import logging
from datetime import datetime, timedelta, timezone

from app.config.database import Database
from app.models.user import UserProfile
from app.services.hevy_api import HevyAPI
from app.services.vector_store import ExerciseVectorStore
from app.state.sync_status import SYNC_STATUS
from app.utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)


db = Database()
vector_store = ExerciseVectorStore()


def calculate_duration_minutes(start_time, end_time):
    if not start_time or not end_time:
        return None
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        return int((end_dt - start_dt).total_seconds() / 60)
    except Exception as e:
        logger.error(f"Error calculating duration: {e}")
        return None


def sync_hevy_data(user_state, sync_type="recent"):
    try:
        SYNC_STATUS["status"] = "syncing"
        logger.info(
            f"Starting sync process for user: {user_state.get('id', 'unknown')}"
        )

        if "id" not in user_state:
            logger.error("No user ID in state")
            SYNC_STATUS["status"] = "error"
            return "No user logged in."

        user_doc = db.get_document(user_state["id"])
        if not user_doc:
            logger.error(f"User profile not found for ID: {user_state['id']}")
            SYNC_STATUS["status"] = "error"
            return "User profile not found."

        if not user_doc.get("hevy_api_key"):
            logger.error("Hevy API key not configured for user")
            SYNC_STATUS["status"] = "error"
            return "Hevy API key not configured."

        # Decrypt API key
        logger.info("Decrypting API key...")
        api_key = decrypt_api_key(user_doc["hevy_api_key"])
        hevy_api = HevyAPI(api_key, is_encrypted=False)
        logger.info("Hevy API client initialized successfully")

        # Sync exercises - skip base exercises if already bootstrapped
        base_exercises_bootstrapped = db.are_base_exercises_bootstrapped()

        if not base_exercises_bootstrapped:
            logger.info("Base exercises not bootstrapped, fetching from Hevy API...")
            exercise_list = hevy_api.get_all_exercises(include_custom=False)
            if exercise_list.exercises:
                exercises_data = [
                    exercise.model_dump() for exercise in exercise_list.exercises
                ]
                db.save_exercises(exercises_data, user_id=None)
                vector_store.add_exercises(exercises_data)
        else:
            logger.info("Base exercises already bootstrapped, skipping...")

        # Skip custom exercises during regular sync - they'll be loaded on-demand for AI recommendations
        logger.info(
            "Skipping custom exercises during sync - will be loaded on-demand for AI recommendations"
        )

        # Determine sync strategy
        end_date = datetime.now(timezone.utc)
        is_demo_key = api_key.startswith("42c1e") if api_key else False

        # Get last sync timestamp for incremental sync
        last_sync = db.get_last_sync_timestamp(user_doc["_id"])

        if sync_type == "full" or is_demo_key or last_sync is None:
            # Full sync: fetch all workouts from a very early date
            if is_demo_key:
                logger.info(
                    "Detected demo API key - using full sync to capture seeded workout history"
                )
            elif last_sync is None:
                logger.info("No previous sync found - performing full sync")
            else:
                logger.info("Full sync requested")

            start_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
            logger.info(
                f"Full sync: fetching workouts from {start_date.isoformat()} to {end_date.isoformat()}"
            )
            workouts = hevy_api.get_workouts(start_date, end_date)
            logger.info(f"Retrieved {len(workouts)} workouts from Hevy API")
        else:
            # Incremental sync: use workout events since last sync
            logger.info(
                f"Incremental sync: checking for workout events since {last_sync.isoformat()}"
            )

            # First, check for workout events (updates/deletes)
            events = hevy_api.get_workout_events(last_sync)
            logger.info(f"Found {len(events)} workout events since last sync")

            # Process events to get updated workout IDs
            updated_workout_ids = set()
            for event in events:
                if event.get("type") in ["workout_updated", "workout_created"]:
                    updated_workout_ids.add(event.get("workout_id"))
                elif event.get("type") == "workout_deleted":
                    # Handle workout deletion
                    workout_id = event.get("workout_id")
                    if workout_id:
                        logger.info(
                            f"Workout {workout_id} was deleted, removing from database"
                        )
                        # TODO: Implement workout deletion from database

            # Fetch updated workouts
            workouts = []
            if updated_workout_ids:
                logger.info(f"Fetching {len(updated_workout_ids)} updated workouts")
                for workout_id in updated_workout_ids:
                    workout_details = hevy_api.get_workout_details(workout_id)
                    if workout_details:
                        workouts.append(workout_details)

            logger.info(f"Retrieved {len(workouts)} updated workouts from Hevy API")

        if workouts:
            enriched_workouts = []
            new_workouts_count = 0
            skipped_count = 0

            # Batch check for existing workouts to reduce database queries
            logger.info("Checking for existing workouts in batch...")
            workout_ids = [workout["id"] for workout in workouts]
            existing_workout_ids = db.get_existing_workout_ids(workout_ids)
            logger.info(
                f"Found {len(existing_workout_ids)} existing workouts out of {len(workout_ids)} total"
            )

            for workout in workouts:
                # Skip if workout is missing required fields
                if not workout.get("title") or not workout.get("exercises"):
                    logger.warning(
                        f"Skipping workout due to missing required fields: {workout}"
                    )
                    skipped_count += 1
                    continue

                if not user_doc["_id"]:
                    logger.warning(
                        f"Skipping workout due to missing user_id: {workout}"
                    )
                    skipped_count += 1
                    continue

                # Check if workout already exists using batch lookup
                if workout["id"] in existing_workout_ids:
                    logger.info(
                        f"Workout {workout.get('title')} already exists, skipping"
                    )
                    skipped_count += 1
                    continue

                workout_data = {
                    "hevy_id": workout["id"],
                    "user_id": user_doc["_id"],
                    "title": workout.get("title", "Untitled Workout"),
                    "description": workout.get("description", ""),
                    "start_time": workout.get("start_time"),
                    "end_time": workout.get("end_time"),
                    "duration_minutes": calculate_duration_minutes(
                        workout.get("start_time"), workout.get("end_time")
                    ),
                    "exercises": workout.get("exercises", []),
                    "exercise_count": len(workout.get("exercises", [])),
                }

                enriched_workouts.append(workout_data)
                new_workouts_count += 1

            # Batch save all new workouts to reduce database operations
            if enriched_workouts:
                logger.info(f"Batch saving {len(enriched_workouts)} new workouts...")
                try:
                    db.save_workouts_batch(enriched_workouts)
                    logger.info(
                        f"Successfully saved {len(enriched_workouts)} workouts in batch"
                    )
                except Exception as e:
                    logger.error(f"Error batch saving workouts: {e}")
                    # Fallback to individual saves
                    logger.info("Falling back to individual workout saves...")
                    successful_saves = 0
                    for workout_data in enriched_workouts:
                        try:
                            db.save_workout(workout_data)
                            successful_saves += 1
                        except Exception as individual_error:
                            logger.error(
                                f"Error saving individual workout {workout_data.get('title')}: {individual_error}"
                            )
                            skipped_count += 1
                    new_workouts_count = successful_saves

            logger.info(
                f"Sync summary: {new_workouts_count} new workouts, {skipped_count} skipped"
            )

            # Only vectorize if we have new workouts
            if enriched_workouts:
                logger.info(
                    f"Adding {len(enriched_workouts)} new workouts to vector store..."
                )
                try:
                    vector_store.add_workout_history(enriched_workouts)
                    logger.info("Vector store update completed successfully")
                except Exception as e:
                    logger.error(f"Error updating vector store: {e}")
                    # Don't fail the sync if vector store update fails
            else:
                logger.info("No new workouts to add to vector store")
        else:
            logger.info("No workouts found in the specified date range")

        # Update last sync timestamp
        db.update_last_sync_timestamp(user_doc["_id"], end_date)

        SYNC_STATUS["status"] = "complete"
        logger.info("Sync process completed successfully")
        return "Sync complete."

    except Exception as e:
        logger.error(f"Error during sync process: {e}", exc_info=True)
        SYNC_STATUS["status"] = "error"
        return f"Sync failed: {str(e)}"
