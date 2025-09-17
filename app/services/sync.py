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

        # Sync base and custom exercises
        for include_custom in [False, True]:
            exercise_list = hevy_api.get_all_exercises(include_custom=include_custom)
            if exercise_list.exercises:
                exercises_data = [
                    exercise.model_dump() for exercise in exercise_list.exercises
                ]
                db.save_exercises(
                    exercises_data, user_id=user_doc["_id"] if include_custom else None
                )
                vector_store.add_exercises(exercises_data)

        # Determine date range for sync
        end_date = datetime.now(timezone.utc)

        # Auto-detect demo/test API key and force full sync for better demo experience
        is_demo_key = api_key.startswith("42c1e") if api_key else False

        if sync_type == "full" or is_demo_key:
            # Full sync: fetch all workouts from a very early date
            # Use full sync for demo keys to ensure seeded data is captured
            start_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
            if is_demo_key:
                logger.info(
                    "Detected demo API key - using full sync to capture seeded workout history"
                )
        else:
            # Recent sync: last 30 days
            start_date = end_date - timedelta(days=30)

        # Sync workouts in the determined date range
        logger.info(
            f"Syncing workouts from {start_date.isoformat()} to {end_date.isoformat()}"
        )
        workouts = hevy_api.get_workouts(start_date, end_date)
        logger.info(f"Retrieved {len(workouts)} workouts from Hevy API")

        if workouts:
            enriched_workouts = []
            new_workouts_count = 0
            skipped_count = 0

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

                # Check if workout already exists to prevent duplicates
                existing_workout = db.get_workout_by_hevy_id(workout["id"])
                if existing_workout:
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

                try:
                    db.save_workout(workout_data)
                    enriched_workouts.append(workout_data)
                    new_workouts_count += 1
                    logger.info(f"Saved new workout: {workout_data['title']}")
                except Exception as e:
                    logger.error(f"Error saving workout {workout.get('title')}: {e}")
                    skipped_count += 1
                    continue

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

        SYNC_STATUS["status"] = "complete"
        logger.info("Sync process completed successfully")
        return "Sync complete."

    except Exception as e:
        logger.error(f"Error during sync process: {e}", exc_info=True)
        SYNC_STATUS["status"] = "error"
        return f"Sync failed: {str(e)}"
