import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import couchdb
from dotenv import load_dotenv

from app.config.config import COUCHDB_DB, COUCHDB_PASSWORD, COUCHDB_URL, COUCHDB_USER

from .views import create_exercise_views, create_user_views, create_workout_views

# Configure logging
logger = logging.getLogger(__name__)

# Log imported values
logger.info("Imported environment variables in database.py:")
logger.info(f"COUCHDB_URL: {COUCHDB_URL}")
logger.info(f"COUCHDB_USER: {COUCHDB_USER}")
logger.info(
    f"COUCHDB_PASSWORD: {'*' * len(COUCHDB_PASSWORD) if COUCHDB_PASSWORD else None}"
)
logger.info(f"COUCHDB_DB: {COUCHDB_DB}")


class Database:
    def __init__(self):
        """Initialize the database connection."""
        try:
            # Check if we're in production mode
            is_production = os.getenv("ENV") == "production"

            if is_production:
                # Production mode requires COUCHDB_URL
                if not COUCHDB_URL:
                    raise ValueError("COUCHDB_URL is required for production mode.")
                self.server = couchdb.Server(COUCHDB_URL)
                self.couchdb_url = COUCHDB_URL
                logger.info(
                    f"Connecting to CouchDB in production mode at {COUCHDB_URL}"
                )
            else:
                # Local development mode
                full_url = COUCHDB_URL or "http://localhost:5984"

                # In development, we always need credentials
                if not COUCHDB_USER or not COUCHDB_PASSWORD:
                    raise ValueError(
                        "COUCHDB_USER and COUCHDB_PASSWORD are required in development mode"
                    )

                # Create server with credentials
                self.server = couchdb.Server(full_url)
                self.server.resource.credentials = (COUCHDB_USER, COUCHDB_PASSWORD)
                logger.info(
                    f"Connecting to CouchDB at {full_url} using user: {COUCHDB_USER}"
                )
                self.couchdb_url = full_url

            # Store credentials and db name for later use
            self.couchdb_user = COUCHDB_USER
            self.couchdb_password = COUCHDB_PASSWORD
            self.couchdb_db = COUCHDB_DB

            # Ensure database exists
            try:
                if COUCHDB_DB in self.server:
                    self.db = self.server[COUCHDB_DB]
                    logger.info(f"Connected to existing database: {COUCHDB_DB}")
                else:
                    logger.info(f"Database {COUCHDB_DB} does not exist. Creating...")
                    self.db = self.server.create(COUCHDB_DB)
                    logger.info(f"Created database: {COUCHDB_DB}")

                    # Create necessary design documents
                    self._create_design_documents()
                    logger.info("Created design documents")

            except Exception as e:
                logger.error(f"Error ensuring database exists: {e}")
                raise

        except Exception as e:
            logger.error(f"Error connecting to CouchDB: {e}")
            raise

    def connect(self):
        """Reconnect to CouchDB using stored URL and credentials."""
        try:
            logger.info(f"Reconnecting to CouchDB at {self.couchdb_url}")
            self.server = couchdb.Server(self.couchdb_url)

            # Only set credentials if using local dev mode
            if COUCHDB_USER and COUCHDB_PASSWORD:
                self.server.resource.credentials = (COUCHDB_USER, COUCHDB_PASSWORD)
                logger.info(f"Using authentication with user: {COUCHDB_USER}")

            # Reconnect to existing database
            if COUCHDB_DB in self.server:
                self.db = self.server[COUCHDB_DB]
                logger.info(f"Reconnected to database: {COUCHDB_DB}")
            else:
                logger.info(f"Database {COUCHDB_DB} does not exist. Creating...")
                self.db = self.server.create(COUCHDB_DB)
                logger.info(f"Database {COUCHDB_DB} created successfully")

        except Exception as e:
            logger.error(f"Error reconnecting to CouchDB: {str(e)}")
            raise

    def _create_mock_database(self):
        """Create a mock database for development when CouchDB is not available."""

        class MockDB:
            def __init__(self):
                self.data = {}
                self.counter = 0

            def save(self, doc):
                if "_id" not in doc:
                    doc["_id"] = f"mock_{self.counter}"
                    self.counter += 1
                self.data[doc["_id"]] = doc
                return doc["_id"], "1-mock"

            def get(self, doc_id):
                return self.data.get(doc_id)

            def find(self, selector):
                # Simple mock implementation
                results = []
                for doc_id, doc in self.data.items():
                    match = True
                    if "selector" in selector:
                        for key, value in selector["selector"].items():
                            if key not in doc or doc[key] != value:
                                match = False
                                break
                    if match:
                        results.append(doc)
                return results

        self.db = MockDB()
        logger.info("Mock database created for development")

    def _create_design_documents(self):
        """Create necessary design documents for views using centralized view functions."""
        try:
            create_user_views(self.db)
            create_workout_views(self.db)
            create_exercise_views(self.db)
            logger.info("All design documents created successfully")
        except Exception as e:
            logger.error(f"Error creating design documents: {str(e)}")

    def recreate_workouts_design_document(self):
        """Recreate the workouts design document to update views using centralized view function."""
        try:
            if "_design/workouts" in self.db:
                logger.info("Deleting existing workouts design document")
                doc = self.db["_design/workouts"]
                self.db.delete(doc)
            logger.info("Creating new workouts design document")
            create_workout_views(self.db)
            logger.info("Workouts design document recreated successfully")
        except Exception as e:
            logger.error(f"Error recreating workouts design document: {str(e)}")

    def recreate_exercises_design_document(self):
        """Recreate the exercises design document to update views using centralized view function."""
        try:
            if "_design/exercises" in self.db:
                logger.info("Deleting existing exercises design document")
                doc = self.db["_design/exercises"]
                self.db.delete(doc)
            logger.info("Creating new exercises design document")
            create_exercise_views(self.db)
            logger.info("Exercises design document recreated successfully")
        except Exception as e:
            logger.error(f"Error recreating exercises design document: {str(e)}")

    def recreate_all_design_documents(self):
        """Recreate all design documents (users, workouts, exercises) using centralized view functions."""
        try:
            # Delete existing design docs if they exist
            for design in ["users", "workouts", "exercises"]:
                doc_id = f"_design/{design}"
                if doc_id in self.db:
                    logger.info(f"Deleting existing {design} design document")
                    doc = self.db[doc_id]
                    self.db.delete(doc)
            # Recreate all design docs
            create_user_views(self.db)
            create_workout_views(self.db)
            create_exercise_views(self.db)
            logger.info("All design documents recreated successfully")
        except Exception as e:
            logger.error(f"Error recreating all design documents: {str(e)}")

    def save_document(
        self, doc: Dict[str, Any], doc_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """Save a document to the database."""
        try:
            # Log the arguments being passed
            logger.info(f"save_document called with doc_id: {doc_id}")
            logger.info(f"Document keys: {list(doc.keys())}")

            # Ensure the document is JSON serializable
            doc = self._ensure_json_serializable(doc)

            # Set the document ID if provided
            if doc_id:
                doc["_id"] = doc_id
                logger.info(f"Set document _id to: {doc_id}")

            # Save the document
            doc_id, doc_rev = self.db.save(doc)
            logger.info(f"Document saved successfully. ID: {doc_id}, Rev: {doc_rev}")
            return doc_id, doc_rev
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _ensure_json_serializable(self, obj: Any) -> Any:
        """Ensure an object is JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "model_dump"):
            return self._ensure_json_serializable(obj.model_dump())
        elif hasattr(obj, "dict"):
            return self._ensure_json_serializable(obj.dict())
        else:
            return obj

    def get_document(self, doc_id):
        """Retrieve a document by ID."""
        try:
            logger.info(f"Retrieving document: {doc_id}")
            doc = self.db[doc_id]
            logger.info(f"Document retrieved successfully: {doc_id}")
            return doc
        except couchdb.http.ResourceNotFound:
            logger.warning(f"Document not found: {doc_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            raise

    def update_document(self, doc):
        """Update an existing document."""
        return self.db.save(doc)

    def delete_document(self, doc_id):
        """Delete a document by ID."""
        try:
            doc = self.db[doc_id]
            self.db.delete(doc)
            return True
        except couchdb.http.ResourceNotFound:
            return False

    def get_all_documents(self):
        """Get all documents from the database."""
        return [doc for doc in self.db.view("_all_docs", include_docs=True)]

    def create_view(
        self, design_doc_name, view_name, map_function, reduce_function=None
    ):
        """Create or update a view in the database."""
        try:
            design_doc = self.db[f"_design/{design_doc_name}"]
        except couchdb.http.ResourceNotFound:
            design_doc = {"_id": f"_design/{design_doc_name}"}

        design_doc["views"] = {
            view_name: {"map": map_function, "reduce": reduce_function}
        }

        return self.db.save(design_doc)

    def get_all_workouts(self) -> List[Dict[str, Any]]:
        """Retrieve all workout documents across all users."""
        try:
            return [
                row.doc for row in self.db.view("workouts/by_date", include_docs=True)
            ]
        except Exception as e:
            logger.error(f"Error fetching all workouts: {str(e)}")
            return []

    def get_workouts_by_date_range(self, start_date, end_date):
        """Get workouts within a date range."""
        try:
            # Convert dates to ISO format if they aren't already
            if isinstance(start_date, datetime):
                start_date = start_date.isoformat()
            if isinstance(end_date, datetime):
                end_date = end_date.isoformat()

            # Query the view
            result = self.db.view(
                "workouts/by_date",
                startkey=start_date,
                endkey=end_date,
                include_docs=True,
            )

            # Extract workout documents
            workouts = [row.doc for row in result]
            return workouts
        except Exception as e:
            print(f"Error getting workouts by date range: {e}")
            return []

    def get_workouts_by_exercise(self, exercise_template_id: str):
        """Get all workouts containing a specific exercise."""
        return [
            row.value
            for row in self.db.view(
                "workouts/by_exercise",
                startkey=[exercise_template_id],
                endkey=[exercise_template_id, {}],
            )
        ]

    def get_workout_stats(
        self, user_id: str, start_date: datetime = None, end_date: datetime = None
    ):
        """Get workout statistics for a user, optionally filtered by date range."""

        # Helper to convert to isoformat if needed
        def to_iso(val):
            if isinstance(val, datetime):
                return val.isoformat()
            return val

        if start_date and end_date:
            result = list(
                self.db.view(
                    "workouts/stats",
                    startkey=[user_id, to_iso(start_date)],
                    endkey=[user_id, to_iso(end_date)],
                    reduce=True,
                    group_level=2,
                )
            )
            # Sum the values in Python
            total_duration = 0
            total_exercises = 0
            total_workouts = 0
            last_workout_date = None

            for row in result:
                val = row.value
                total_duration += val.get("total_duration", 0)
                total_exercises += val.get("total_exercises", 0)
                total_workouts += val.get("total_workouts", 0)
                lw = val.get("last_workout_date")
                if lw and (not last_workout_date or lw > last_workout_date):
                    last_workout_date = lw
            logger.info(
                f"Workout stats (get_workout_stats): {total_duration}, {total_exercises}, {total_workouts}, {last_workout_date}"
            )
            return [
                {
                    "total_duration": total_duration,
                    "total_exercises": total_exercises,
                    "total_workouts": total_workouts,
                    "last_workout_date": last_workout_date,
                }
            ]
        # If no date range, get all stats for the user
        result = list(
            self.db.view(
                "workouts/stats",
                startkey=[user_id],
                endkey=[user_id, {}],
                reduce=True,
                group_level=1,
            )
        )
        return [row.value for row in result]

    def get_workout_progression(self, exercise_template_id: str):
        """Get progression data for a specific exercise."""
        return [
            row.value
            for row in self.db.view(
                "workouts/by_exercise",
                startkey=[exercise_template_id],
                endkey=[exercise_template_id, {}],
                include_docs=True,
            )
        ]

    # User Profile Methods
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get a user by username."""
        try:
            # Use Mango query to find user by username
            query = {"selector": {"type": "user_profile", "username": username}}
            result = self.db.find(query)
            for doc in result:
                # Fix preferred_workout_days if it's a list
                # TODO: Remove this once we've confirmed that the data is normalized
                if "preferred_workout_days" in doc and isinstance(
                    doc["preferred_workout_days"], list
                ):
                    # Take the first value if it's a list
                    doc["preferred_workout_days"] = doc["preferred_workout_days"][0]
                    logging.info(
                        f"Converted preferred_workout_days from list to integer: {doc['preferred_workout_days']}"
                    )
                return doc
            return None
        except Exception as e:
            logging.error(f"Error getting user by username: {str(e)}")
            return None

    def username_exists(self, username: str) -> bool:
        """Check if a username already exists."""
        try:
            # Use Mango query to find user by username
            query = {"selector": {"type": "user_profile", "username": username}}
            result = self.db.find(query)
            # Check if any results were returned
            return any(True for _ in result)
        except Exception as e:
            logging.error(f"Error checking if username exists: {str(e)}")
            return False

    def get_users_by_fitness_goal(self, goal: str):
        """Get all users with a specific fitness goal."""
        return [
            row.value
            for row in self.db.view(
                "users/by_fitness_goals", startkey=[goal], endkey=[goal, {}]
            )
        ]

    def get_users_by_injury(self, body_part: str, severity: Optional[int] = None):
        """Get all users with injuries to a specific body part."""
        if severity is not None:
            return [
                row.value
                for row in self.db.view(
                    "users/by_injuries",
                    startkey=[body_part, severity],
                    endkey=[body_part, severity],
                )
            ]
        return [
            row.value
            for row in self.db.view(
                "users/by_injuries", startkey=[body_part], endkey=[body_part, 10]
            )
        ]

    def update_user_hevy_api_key(self, user_id: str, api_key: str):
        """Update a user's Hevy API key."""
        try:
            user_doc = self.db[user_id]
            user_doc["hevy_api_key"] = api_key
            user_doc["hevy_api_key_updated_at"] = datetime.now(timezone.utc).isoformat()
            return self.db.save(user_doc)
        except couchdb.http.ResourceNotFound:
            return None

    def get_user_workout_history(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """
        Get workout history for a user within a date range.

        Args:
            user_id (str): User ID
            start_date (datetime): Start date for the range
            end_date (datetime): End date for the range

        Returns:
            List[Dict]: List of workout dictionaries
        """
        try:
            # Convert dates to UTC if they have timezone info
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            logger.info(f"Getting workout history for user {user_id}")
            logger.info(f"Date range: {start_date} to {end_date}")

            # Query workouts within date range using the by_user view
            results = self.db.view(
                "workouts/by_user",
                startkey=[user_id, start_date.isoformat()],
                endkey=[user_id, end_date.isoformat()],
                include_docs=True,
            )

            # Convert to list and log count
            workout_list = [row.doc for row in results]
            logger.info(
                f"Found {len(workout_list)} workouts for user {user_id} in date range {start_date} to {end_date}"
            )

            return workout_list
        except Exception as e:
            logger.error(f"Error getting workout history: {str(e)}")
            return []

    def save_exercise(self, exercise_data: Dict[str, Any]) -> str:
        """
        Save an exercise to the database.

        Args:
            exercise_data: Exercise data to save

        Returns:
            Document ID
        """
        try:
            # logger.info(f"Saving exercise type: {type(exercise_data)}")
            exercise_name = exercise_data.get("title", "Unknown")
            has_embedding = "embedding" in exercise_data
            # logger.info(
            #     f"Saving exercise: {exercise_name} (Has embedding: {has_embedding})"
            # )

            # Check if exercise already exists by hevy_id
            if "hevy_id" in exercise_data:
                existing = self.get_exercise_by_hevy_id(exercise_data["hevy_id"])
                if existing:
                    # Update existing exercise
                    exercise_data["_id"] = existing["_id"]
                    exercise_data["_rev"] = existing["_rev"]
                    # logger.info(
                    #     f"Updating existing exercise: {exercise_name} (ID: {existing['_id']})"
                    # )

                    # Check if we're preserving the embedding
                    if has_embedding and "embedding" not in existing:
                        logger.info(
                            f"Adding embedding to existing exercise: {exercise_name}"
                        )
                    elif has_embedding and "embedding" in existing:
                        logger.info(
                            f"Updating embedding for existing exercise: {exercise_name}"
                        )
                    elif not has_embedding and "embedding" in existing:
                        logger.info(
                            f"Preserving existing embedding for exercise: {exercise_name}"
                        )
                        exercise_data["embedding"] = existing["embedding"]

            # Save to database
            doc_id, _ = self.db.save(exercise_data)
            # logger.info(
            #     f"Saved exercise with ID: {doc_id} (Has embedding: {'embedding' in exercise_data})"
            # )
            return doc_id
        except Exception as e:
            logger.error(f"Error saving exercise: {str(e)}")
            raise

    def get_exercise_by_hevy_id(self, hevy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an exercise by its Hevy ID.

        Args:
            hevy_id: The Hevy ID of the exercise

        Returns:
            Exercise document if found, None otherwise
        """
        try:
            results = self.db.view(
                "exercises/by_hevy_id", key=hevy_id, include_docs=True
            )
            for row in results:
                exercise = row.doc
                has_embedding = "embedding" in exercise
                logger.info(
                    f"Retrieved exercise by Hevy ID {hevy_id}: {exercise.get('title', 'Unknown')} (Has embedding: {has_embedding})"
                )
                return exercise
            logger.info(f"No exercise found with Hevy ID: {hevy_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting exercise by Hevy ID: {str(e)}")
            return None

    def get_exercises_by_muscle_group(self, muscle_group: str) -> List[Dict[str, Any]]:
        """
        Get all exercises for a specific muscle group.

        Args:
            muscle_group: The muscle group to filter by

        Returns:
            List of exercise documents
        """
        try:
            return [
                row.doc
                for row in self.db.view(
                    "exercises/by_muscle_group", key=muscle_group, include_docs=True
                )
            ]
        except Exception as e:
            logger.error(f"Error getting exercises by muscle group: {str(e)}")
            return []

    def get_all_exercises(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all exercises from the database, including base and custom exercises.

        Args:
            user_id: Optional user ID to include their custom exercises

        Returns:
            List of all exercise documents
        """
        try:
            exercises = []

            # First try to get individual exercise documents from the view
            individual_exercises = [
                row.doc for row in self.db.view("exercises/all", include_docs=True)
            ]
            exercises.extend(individual_exercises)

            # Get base exercises from base_exercises document
            base_doc = self.get_document("base_exercises")
            if base_doc and base_doc.get("exercises"):
                exercises.extend(base_doc["exercises"])
                logger.info(f"Retrieved {len(base_doc['exercises'])} base exercises")

            # Get custom exercises for the specific user if provided
            if user_id:
                custom_doc = self.get_document(f"custom_exercises_{user_id}")
                if custom_doc and custom_doc.get("exercises"):
                    exercises.extend(custom_doc["exercises"])
                    logger.info(
                        f"Retrieved {len(custom_doc['exercises'])} custom exercises for user {user_id}"
                    )

            # Remove duplicates based on exercise ID
            seen_ids = set()
            unique_exercises = []
            for exercise in exercises:
                exercise_id = exercise.get("id") or exercise.get("hevy_id")
                if exercise_id and exercise_id not in seen_ids:
                    seen_ids.add(exercise_id)
                    unique_exercises.append(exercise)

            logger.info(f"Retrieved {len(unique_exercises)} total unique exercises")
            return unique_exercises
        except Exception as e:
            logger.error(f"Error getting all exercises: {str(e)}")
            return []

    def save_workout(
        self,
        workout_data: Dict[str, Any],
        doc_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Save a workout to the database.

        Args:
            workout_data: Workout data to save
            doc_id: Optional document ID to use
            user_id: Optional user ID to associate with the workout

        Returns:
            Document ID
        """
        try:
            # Log the arguments being passed
            # logger.info(
            #     # f"save_workout called with doc_id: {doc_id}, user_id: {user_id}"
            # )
            # logger.info(f"Workout data keys: {list(workout_data.keys())}")

            # Set the document type
            workout_data["type"] = "workout"
            # logger.info(f"Set workout type to: workout")

            # Set the user_id if provided
            if user_id:
                workout_data["user_id"] = user_id
                # logger.info(f"Set workout user_id to: {user_id}")

            # Set the document ID if provided
            if doc_id:
                workout_data["_id"] = doc_id
                # logger.info(f"Set workout _id to: {doc_id}")

            # Check if workout already exists by hevy_id
            elif "hevy_id" in workout_data:
                existing = self.get_workout_by_hevy_id(workout_data["hevy_id"])
                if existing:
                    # Update existing workout
                    workout_data["_id"] = existing["_id"]
                    workout_data["_rev"] = existing["_rev"]
                    # logger.info(f"Updating existing workout with ID: {existing['_id']}")

            # Ensure exercise_count is set
            if "exercise_count" not in workout_data and "exercises" in workout_data:
                workout_data["exercise_count"] = len(workout_data["exercises"])
                logger.info(f"Set exercise_count to: {workout_data['exercise_count']}")

            # Save to database
            doc_id, _ = self.db.save(workout_data)
            logger.info(f"Saved workout with ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error saving workout: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def get_workout_by_hevy_id(self, hevy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a workout by its Hevy ID.

        Args:
            hevy_id: The Hevy ID of the workout

        Returns:
            Workout document if found, None otherwise
        """
        try:
            results = self.db.view(
                "workouts/by_hevy_id", key=hevy_id, include_docs=True
            )
            for row in results:
                return row.doc
            return None
        except Exception as e:
            logger.error(f"Error getting workout by Hevy ID: {str(e)}")
            return None

    def get_existing_workout_ids(self, hevy_ids: List[str]) -> Set[str]:
        """
        Get a set of Hevy IDs that already exist in the database.
        This is more efficient than checking each workout individually.

        Args:
            hevy_ids: List of Hevy IDs to check

        Returns:
            Set of Hevy IDs that already exist in the database
        """
        existing_ids = set()
        try:
            # Use bulk query to check multiple IDs at once
            # CouchDB views support multiple keys in a single query
            results = self.db.view(
                "workouts/by_hevy_id", keys=hevy_ids, include_docs=False
            )
            for row in results:
                existing_ids.add(row.key)
            logger.info(
                f"Found {len(existing_ids)} existing workouts out of {len(hevy_ids)} checked"
            )
        except Exception as e:
            logger.error(f"Error getting existing workout IDs: {str(e)}")
            # Fallback to individual queries if bulk query fails
            logger.info("Falling back to individual workout checks...")
            for hevy_id in hevy_ids:
                try:
                    if self.get_workout_by_hevy_id(hevy_id):
                        existing_ids.add(hevy_id)
                except Exception as individual_error:
                    logger.error(
                        f"Error checking individual workout {hevy_id}: {individual_error}"
                    )

        return existing_ids

    def are_base_exercises_bootstrapped(self) -> bool:
        """
        Check if base exercises have already been bootstrapped.

        Returns:
            True if base exercises exist, False otherwise
        """
        try:
            base_exercises_doc = self.get_document("base_exercises")
            if base_exercises_doc and base_exercises_doc.get("exercises"):
                exercise_count = len(base_exercises_doc.get("exercises", []))
                logger.info(
                    f"Found {exercise_count} base exercises already bootstrapped"
                )
                return exercise_count > 0
            return False
        except Exception as e:
            logger.error(f"Error checking base exercises bootstrap status: {e}")
            return False

    def get_last_sync_timestamp(self, user_id: str) -> Optional[datetime]:
        """
        Get the last sync timestamp for a user.

        Args:
            user_id: User ID

        Returns:
            Last sync timestamp or None if no previous sync
        """
        try:
            user_doc = self.get_document(user_id)
            if user_doc and user_doc.get("last_sync_timestamp"):
                return datetime.fromisoformat(user_doc["last_sync_timestamp"])
            return None
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None

    def update_last_sync_timestamp(self, user_id: str, timestamp: datetime) -> None:
        """
        Update the last sync timestamp for a user.

        Args:
            user_id: User ID
            timestamp: Sync timestamp
        """
        try:
            user_doc = self.get_document(user_id)
            if user_doc:
                user_doc["last_sync_timestamp"] = timestamp.isoformat()
                self.save_document(user_doc)
                logger.info(
                    f"Updated last sync timestamp for user {user_id}: {timestamp.isoformat()}"
                )
        except Exception as e:
            logger.error(f"Error updating last sync timestamp: {e}")

    def save_workouts_batch(self, workouts: List[Dict[str, Any]]) -> None:
        """
        Save multiple workouts in a single batch operation.
        This is more efficient than saving workouts individually.

        Args:
            workouts: List of workout data dictionaries to save
        """
        if not workouts:
            return

        try:
            # Prepare documents for bulk save
            docs_to_save = []
            for workout_data in workouts:
                doc = {
                    "_id": f"workout_{workout_data['hevy_id']}",
                    "type": "workout",
                    "hevy_id": workout_data["hevy_id"],
                    "user_id": workout_data["user_id"],
                    "title": workout_data["title"],
                    "description": workout_data.get("description", ""),
                    "start_time": workout_data.get("start_time"),
                    "end_time": workout_data.get("end_time"),
                    "duration_minutes": workout_data.get("duration_minutes"),
                    "exercises": workout_data.get("exercises", []),
                    "exercise_count": workout_data.get("exercise_count", 0),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                docs_to_save.append(doc)

            # Use CouchDB bulk save
            self.db.update(docs_to_save)
            logger.info(f"Successfully saved {len(docs_to_save)} workouts in batch")

        except Exception as e:
            logger.error(f"Error batch saving workouts: {str(e)}")
            raise

    def save_exercises(
        self,
        exercises: List[Dict[str, Any]],
        is_custom: bool = False,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Save exercises to the database.

        Args:
            exercises: List of exercise dictionaries
            is_custom: Whether these are custom exercises
            user_id: User ID for custom exercises
        """
        try:
            # Determine document ID and type
            if is_custom and user_id:
                doc_id = f"custom_exercises_{user_id}"
                doc_type = "custom_exercises"
            else:
                doc_id = "base_exercises"
                doc_type = "base_exercises"

            # Create document
            exercise_doc = {
                "_id": doc_id,
                "type": doc_type,
                "exercises": exercises,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Check if document already exists
            try:
                existing = self.db[doc_id]
                exercise_doc["_rev"] = existing["_rev"]
            except (couchdb.http.ResourceNotFound, AttributeError) as e:
                # Handle both missing document and client library compatibility issues
                logger.info(f"Document {doc_id} not found or client error: {e}")
                pass

            # Save to database
            self.db.save(exercise_doc)
            logger.info(
                f"Saved {len(exercises)} {'custom' if is_custom else 'base'} exercises"
            )

            # Get existing exercises to check for embeddings
            existing_exercises = []
            try:
                if is_custom and user_id:
                    existing_doc = self.db.get(f"custom_exercises_{user_id}")
                    if existing_doc and "exercises" in existing_doc:
                        existing_exercises = existing_doc["exercises"]
                        logger.info(
                            f"Found {len(existing_exercises)} existing custom exercises"
                        )
                else:
                    existing_doc = self.db.get("base_exercises")
                    if existing_doc and "exercises" in existing_doc:
                        existing_exercises = existing_doc["exercises"]
                        logger.info(
                            f"Found {len(existing_exercises)} existing base exercises"
                        )
            except (couchdb.http.ResourceNotFound, AttributeError) as e:
                logger.info(
                    f"No existing {'custom' if is_custom else 'base'} exercises found: {e}"
                )
                pass

            # Create a map of existing exercises by ID
            existing_exercise_map = {ex.get("id"): ex for ex in existing_exercises}
            logger.info(
                f"Created map with {len(existing_exercise_map)} existing exercises"
            )

            # Only add exercises to vector store that don't already have embeddings
            exercises_to_add = []
            exercises_with_embeddings = 0
            for exercise in exercises:
                exercise_id = exercise.get("id")
                exercise_title = exercise.get("title", "Unknown")
                # logger.info(
                #     # f"Processing exercise: {exercise_title} (ID: {exercise_id})"
                # )

                if exercise_id in existing_exercise_map:
                    # Check if the existing exercise has an embedding
                    if "embedding" in existing_exercise_map[exercise_id]:
                        # Copy the embedding to the new exercise
                        exercise["embedding"] = existing_exercise_map[exercise_id][
                            "embedding"
                        ]
                        # logger.info(
                        #     # f"Reused existing embedding for exercise: {exercise_title}"
                        # )
                        # Save the exercise with the embedding
                        self.save_exercise(exercise)
                        exercises_with_embeddings += 1
                    else:
                        logger.info(
                            f"No embedding found for existing exercise: {exercise_title}"
                        )
                        exercises_to_add.append(exercise)
                else:
                    # New exercise, add to vector store
                    logger.info(f"New exercise found: {exercise_title}")
                    exercises_to_add.append(exercise)

            logger.info(
                f"Found {exercises_with_embeddings} exercises with existing embeddings"
            )
            logger.info(
                f"Need to generate embeddings for {len(exercises_to_add)} exercises"
            )

            # Only add new exercises to vector store
            if exercises_to_add:
                from services.vector_store import ExerciseVectorStore

                vector_store = ExerciseVectorStore()
                vector_store.add_exercises(exercises_to_add)

                # Update the exercises in the database with the embeddings
                for exercise in exercises_to_add:
                    if "embedding" in exercise:
                        # Save the exercise with the embedding
                        self.save_exercise(exercise)
                        logger.info(
                            f"Saved exercise with new embedding: {exercise.get('name', 'Unknown')}"
                        )

        except Exception as e:
            logger.error(f"Error saving exercises: {str(e)}")
            raise

    def get_exercises(
        self, user_id: Optional[str] = None, include_custom: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all available exercises from the database.

        Args:
            user_id: Optional user ID to get custom exercises for
            include_custom: Whether to include custom exercises in the results

        Returns:
            List of exercise dictionaries
        """
        try:
            exercises = []

            # Get base exercises
            try:
                base_doc = self.db.get("base_exercises")
                if base_doc:
                    logger.info(f"Found base exercises document: {base_doc.get('_id')}")
                    if "exercises" in base_doc:
                        logger.info(
                            f"Found {len(base_doc['exercises'])} base exercises"
                        )
                        exercises.extend(base_doc["exercises"])
                    else:
                        logger.warning(
                            "Base exercises document exists but has no exercises field"
                        )
                else:
                    logger.warning("Base exercises document not found")
            except couchdb.http.ResourceNotFound:
                logger.info("No base exercises found in database")

            # Get custom exercises if requested
            if include_custom and user_id:
                try:
                    custom_doc = self.db.get(f"custom_exercises_{user_id}")
                    if custom_doc and "exercises" in custom_doc:
                        exercises.extend(custom_doc["exercises"])
                except couchdb.http.ResourceNotFound:
                    logger.info(f"No custom exercises found for user {user_id}")

            return exercises
        except Exception as e:
            logger.error(f"Error getting exercises: {str(e)}")
            return []

    def get_custom_exercises(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get custom exercises for a specific user.

        Args:
            user_id: User ID to get custom exercises for

        Returns:
            List of custom exercise dictionaries
        """
        try:
            custom_doc = self.db.get(f"custom_exercises_{user_id}")
            if custom_doc and "exercises" in custom_doc:
                return custom_doc["exercises"]
            return []
        except couchdb.http.ResourceNotFound:
            logger.info(f"No custom exercises found for user {user_id}")
            return []
        except Exception as e:
            logger.error(f"Error getting custom exercises: {str(e)}")
            return []

    # TODO: is this method being used?
    def save_user_workouts(self, user_id: str, workouts: list[dict]) -> list[str]:
        """
        Save multiple workouts for a user.

        Args:
            user_id: The user's ID to associate with each workout.
            workouts: List of workout dicts to save.

        Returns:
            List of document IDs for the saved workouts.
        """
        doc_ids = []
        for workout in workouts:
            doc_id = self.save_workout(workout_data=workout, user_id=user_id)
            doc_ids.append(doc_id)
        return doc_ids
