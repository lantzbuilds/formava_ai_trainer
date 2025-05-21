import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import couchdb
from dotenv import load_dotenv

from config.config import COUCHDB_DB, COUCHDB_PASSWORD, COUCHDB_URL, COUCHDB_USER

from .views import create_user_views, create_workout_views

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COUCHDB_URL = os.getenv("COUCHDB_URL")
COUCHDB_USER = os.getenv("COUCHDB_USER")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD")
COUCHDB_DB = os.getenv("COUCHDB_DB", "ai_trainer")


class Database:
    def __init__(self, auto_connect: bool = True):
        """Initialize the database connection."""
        try:
            if COUCHDB_USER and COUCHDB_PASSWORD:
                # Local dev with username/password
                full_url = COUCHDB_URL or "http://localhost:5984"
                self.server = couchdb.Server(full_url)
                self.server.resource.credentials = (COUCHDB_USER, COUCHDB_PASSWORD)
                logger.info(
                    f"Connecting to CouchDB at {full_url} using user: {COUCHDB_USER}"
                )
            else:
                # Production with embedded credentials in URL
                if not COUCHDB_URL:
                    raise ValueError("COUCHDB_URL is required for production mode.")
                self.server = couchdb.Server(COUCHDB_URL)
                logger.info(f"Connecting to CouchDB at COUCHDB_URL={COUCHDB_URL}")

            # Ensure database exists
            if COUCHDB_DB in self.server:
                self.db = self.server[COUCHDB_DB]
            else:
                logger.info(f"Database {COUCHDB_DB} does not exist. Creating...")
                self.db = self.server.create(COUCHDB_DB)

        except Exception as e:
            logger.error(f"Error connecting to CouchDB: {e}")
            raise

        if auto_connect:
            self.connect()

    def connect(self):
        """Connect to the CouchDB server and get or create the database."""
        # TODO: why it this called multiple times when launching the app?
        try:
            logger.info(f"Connecting to CouchDB at {self.couchdb_url}")

            # Create server with authentication
            self.server = couchdb.Server(self.couchdb_url)

            # Set credentials if provided
            if self.couchdb_user and self.couchdb_password:
                self.server.resource.credentials = (
                    self.couchdb_user,
                    self.couchdb_password,
                )
                logger.info(f"Using authentication with user: {self.couchdb_user}")
            else:
                logger.warning(
                    "No CouchDB credentials provided. Using anonymous access."
                )

            # Check if database exists, create if not
            try:
                if self.db_name not in self.server:
                    logger.info(f"Database {self.db_name} does not exist. Creating...")
                    self.db = self.server.create(self.db_name)
                    logger.info(f"Database {self.db_name} created successfully")
                else:
                    logger.info(f"Database {self.db_name} already exists")
                    self.db = self.server[self.db_name]
            except couchdb.http.Unauthorized:
                logger.error(
                    "Authentication failed. Please check your CouchDB credentials."
                )
                # Try to connect without authentication as fallback
                logger.info("Attempting to connect without authentication...")
                self.server = couchdb.Server(self.couchdb_url)
                if self.db_name not in self.server:
                    self.db = self.server.create(self.db_name)
                else:
                    self.db = self.server[self.db_name]

            # Create design documents if they don't exist
            self._create_design_documents()
        except Exception as e:
            logger.error(f"Error connecting to CouchDB: {str(e)}")
            # Create a mock database for development
            logger.warning("Creating mock database for development")
            self._create_mock_database()

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
        """Create necessary design documents for views."""
        try:
            # Check if users design document exists
            if "_design/users" not in self.db:
                logger.info("Creating users design document")
                self.db.save(
                    {
                        "_id": "_design/users",
                        "views": {
                            "by_username": {
                                "map": "function(doc) { if (doc.type === 'user_profile') { emit(doc.username, doc); } }"
                            },
                            "by_email": {
                                "map": "function(doc) { if (doc.type === 'user_profile') { emit(doc.email, doc); } }"
                            },
                        },
                    }
                )
                logger.info("Users design document created successfully")

            # Check if exercises design document exists
            if "_design/exercises" not in self.db:
                logger.info("Creating exercises design document")
                self.db.save(
                    {
                        "_id": "_design/exercises",
                        "views": {
                            "by_hevy_id": {
                                "map": "function(doc) { if (doc.type === 'exercise') { emit(doc.hevy_id, doc); } }"
                            },
                            "by_muscle_group": {
                                "map": "function(doc) { if (doc.type === 'exercise') { emit(doc.muscle_group, doc); } }"
                            },
                            "all": {
                                "map": "function(doc) { if (doc.type === 'exercise') { emit(doc._id, doc); } }"
                            },
                        },
                    }
                )
                logger.info("Exercises design document created successfully")

            # Check if workouts design document exists
            if "_design/workouts" not in self.db:
                logger.info("Creating workouts design document")
                self.db.save(
                    {
                        "_id": "_design/workouts",
                        "views": {
                            "by_hevy_id": {
                                "map": "function(doc) { if (doc.type === 'workout') { emit(doc.hevy_id, doc); } }"
                            },
                            "by_user": {
                                "map": "function(doc) { if (doc.type === 'workout' && doc.user_id) { emit([doc.user_id, doc.start_time], doc); } }"
                            },
                            "by_date": {
                                "map": "function(doc) { if (doc.type === 'workout') { emit(doc.start_time, doc); } }"
                            },
                            "by_exercise": {
                                "map": "function(doc) { if (doc.type === 'workout') { doc.exercises.forEach(function(ex) { emit([ex.template_id, doc.start_time], doc); }); } }"
                            },
                            "stats": {
                                "map": "function(doc) { if (doc.type === 'workout') { emit(doc.start_time, {duration: doc.duration, exercise_count: doc.exercises.length}); } }",
                                "reduce": "function(keys, values, rereduce) { return {total_duration: values.reduce(function(a, b) { return a + b.duration; }, 0), total_exercises: values.reduce(function(a, b) { return a + b.exercise_count; }, 0), count: values.length}; }",
                            },
                        },
                    }
                )
                logger.info("Workouts design document created successfully")
        except Exception as e:
            logger.error(f"Error creating design documents: {str(e)}")

    def recreate_workouts_design_document(self):
        """Recreate the workouts design document to update views."""
        try:
            # Delete existing workouts design document if it exists
            if "_design/workouts" in self.db:
                logger.info("Deleting existing workouts design document")
                doc = self.db["_design/workouts"]
                self.db.delete(doc)

            # Create new workouts design document
            logger.info("Creating new workouts design document")
            self.db.save(
                {
                    "_id": "_design/workouts",
                    "views": {
                        "by_hevy_id": {
                            "map": "function(doc) { if (doc.type === 'workout') { emit(doc.hevy_id, doc); } }"
                        },
                        "by_user": {
                            "map": "function(doc) { if (doc.type === 'workout' && doc.user_id) { emit([doc.user_id, doc.start_time], doc); } }"
                        },
                        "by_date": {
                            "map": "function(doc) { if (doc.type === 'workout') { emit(doc.start_time, doc); } }"
                        },
                        "by_exercise": {
                            "map": "function(doc) { if (doc.type === 'workout') { doc.exercises.forEach(function(ex) { emit([ex.template_id, doc.start_time], doc); }); } }"
                        },
                        "stats": {
                            "map": "function(doc) { if (doc.type === 'workout') { emit(doc.start_time, {duration: doc.duration, exercise_count: doc.exercises.length}); } }",
                            "reduce": "function(keys, values, rereduce) { return {total_duration: values.reduce(function(a, b) { return a + b.duration; }, 0), total_exercises: values.reduce(function(a, b) { return a + b.exercise_count; }, 0), count: values.length}; }",
                        },
                    },
                }
            )
            logger.info("Workouts design document recreated successfully")
        except Exception as e:
            logger.error(f"Error recreating workouts design document: {str(e)}")

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

    def get_workout_stats(self, start_date: datetime = None, end_date: datetime = None):
        """Get workout statistics, optionally filtered by date range."""
        if start_date and end_date:
            return [
                row.value
                for row in self.db.view(
                    "workouts/stats",
                    startkey=start_date.isoformat(),
                    endkey=end_date.isoformat(),
                )
            ]
        return [row.value for row in self.db.view("workouts/stats")]

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
            exercise_name = exercise_data.get("name", "Unknown")
            has_embedding = "embedding" in exercise_data
            logger.info(
                f"Saving exercise: {exercise_name} (Has embedding: {has_embedding})"
            )

            # Check if exercise already exists by hevy_id
            if "hevy_id" in exercise_data:
                existing = self.get_exercise_by_hevy_id(exercise_data["hevy_id"])
                if existing:
                    # Update existing exercise
                    exercise_data["_id"] = existing["_id"]
                    exercise_data["_rev"] = existing["_rev"]
                    logger.info(
                        f"Updating existing exercise: {exercise_name} (ID: {existing['_id']})"
                    )

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
            logger.info(
                f"Saved exercise with ID: {doc_id} (Has embedding: {'embedding' in exercise_data})"
            )
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

    def get_all_exercises(self) -> List[Dict[str, Any]]:
        """
        Get all exercises from the database.

        Returns:
            List of all exercise documents
        """
        try:
            return [row.doc for row in self.db.view("exercises/all", include_docs=True)]
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
            logger.info(
                f"save_workout called with doc_id: {doc_id}, user_id: {user_id}"
            )
            logger.info(f"Workout data keys: {list(workout_data.keys())}")

            # Set the document type
            workout_data["type"] = "workout"
            logger.info(f"Set workout type to: workout")

            # Set the user_id if provided
            if user_id:
                workout_data["user_id"] = user_id
                logger.info(f"Set workout user_id to: {user_id}")

            # Set the document ID if provided
            if doc_id:
                workout_data["_id"] = doc_id
                logger.info(f"Set workout _id to: {doc_id}")

            # Check if workout already exists by hevy_id
            elif "hevy_id" in workout_data:
                existing = self.get_workout_by_hevy_id(workout_data["hevy_id"])
                if existing:
                    # Update existing workout
                    workout_data["_id"] = existing["_id"]
                    workout_data["_rev"] = existing["_rev"]
                    logger.info(f"Updating existing workout with ID: {existing['_id']}")

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
            except couchdb.http.ResourceNotFound:
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
            except couchdb.http.ResourceNotFound:
                logger.info(
                    f"No existing {'custom' if is_custom else 'base'} exercises found"
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
                logger.info(
                    f"Processing exercise: {exercise.get('name', 'Unknown')} (ID: {exercise_id})"
                )

                if exercise_id in existing_exercise_map:
                    # Check if the existing exercise has an embedding
                    if "embedding" in existing_exercise_map[exercise_id]:
                        # Copy the embedding to the new exercise
                        exercise["embedding"] = existing_exercise_map[exercise_id][
                            "embedding"
                        ]
                        logger.info(
                            f"Reused existing embedding for exercise: {exercise.get('name', 'Unknown')}"
                        )
                        # Save the exercise with the embedding
                        self.save_exercise(exercise)
                        exercises_with_embeddings += 1
                    else:
                        logger.info(
                            f"No embedding found for existing exercise: {exercise.get('name', 'Unknown')}"
                        )
                        exercises_to_add.append(exercise)
                else:
                    # New exercise, add to vector store
                    logger.info(
                        f"New exercise found: {exercise.get('name', 'Unknown')}"
                    )
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
                if base_doc and "exercises" in base_doc:
                    exercises.extend(base_doc["exercises"])
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

    def recreate_exercises_design_document(self):
        """Recreate the exercises design document to update views."""
        try:
            # Delete existing exercises design document if it exists
            if "_design/exercises" in self.db:
                logger.info("Deleting existing exercises design document")
                doc = self.db["_design/exercises"]
                self.db.delete(doc)

            # Create new exercises design document
            logger.info("Creating new exercises design document")
            self.db.save(
                {
                    "_id": "_design/exercises",
                    "views": {
                        "by_hevy_id": {
                            "map": "function(doc) { if (doc.type === 'exercise') { emit(doc.hevy_id, {id: doc._id, title: doc.title, muscle_groups: doc.muscle_groups, equipment: doc.equipment}); } }"
                        },
                        "by_muscle_group": {
                            "map": "function(doc) { if (doc.type === 'exercise' && doc.muscle_groups) { doc.muscle_groups.forEach(function(mg) { emit(mg.name, {id: doc._id, title: doc.title, is_primary: mg.is_primary, equipment: doc.equipment}); }); } }"
                        },
                        "all": {
                            "map": "function(doc) { if (doc.type === 'exercise') { emit(doc._id, {id: doc._id, title: doc.title, muscle_groups: doc.muscle_groups, equipment: doc.equipment}); } }"
                        },
                    },
                }
            )
            logger.info("Exercises design document recreated successfully")
        except Exception as e:
            logger.error(f"Error recreating exercises design document: {str(e)}")
