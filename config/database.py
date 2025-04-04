import logging
import os
from datetime import datetime
from typing import List, Optional

import couchdb
from dotenv import load_dotenv

from .views import create_user_views, create_workout_views

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class Database:
    def __init__(self):
        # Get CouchDB configuration from environment variables
        couchdb_url = os.getenv("COUCHDB_URL", "http://localhost:5984")
        username = os.getenv("COUCHDB_USERNAME", "admin")
        password = os.getenv("COUCHDB_PASSWORD", "password")

        logger.info(f"Connecting to CouchDB at {couchdb_url}")

        # Create server with authentication
        self.server = couchdb.Server(couchdb_url)
        self.server.resource.credentials = (username, password)

        # Initialize database
        self.db_name = os.getenv("COUCHDB_DATABASE", "ai_personal_trainer")
        try:
            self.db = self.server[self.db_name]
            logger.info(f"Connected to existing database: {self.db_name}")
        except couchdb.http.ResourceNotFound:
            self.db = self.server.create(self.db_name)
            logger.info(f"Created new database: {self.db_name}")

        # Initialize views
        self._init_views()

    def _init_views(self):
        """Initialize CouchDB views."""
        try:
            # Try to create workout views
            create_workout_views(self.db)
            # Try to create user views
            create_user_views(self.db)
        except couchdb.http.ResourceConflict:
            # If views already exist, that's fine - we can continue
            print("Views already exist in the database")
        except Exception as e:
            print(f"Error creating views: {e}")
            # Don't raise the exception - we can still use the database
            # even if view creation fails

    def save_document(self, doc):
        """Save a document to the database."""
        try:
            logger.info(f"Saving document with ID: {doc.get('_id', 'new')}")
            logger.debug(f"Document content: {doc}")
            result = self.db.save(doc)
            logger.info(
                f"Document saved successfully. ID: {result[0]}, Rev: {result[1]}"
            )
            return result
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            raise

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

    def get_workouts_by_date_range(self, start_date: datetime, end_date: datetime):
        """Get workouts within a date range."""
        start_key = start_date.isoformat()
        end_key = end_date.isoformat()
        return [
            row.value
            for row in self.db.view(
                "workouts/by_date", startkey=start_key, endkey=end_key
            )
        ]

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
    def get_user_by_username(self, username: str):
        """Get user profile by username."""
        try:
            return [
                row.value for row in self.db.view("users/by_username", key=username)
            ][0]
        except IndexError:
            return None

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
            user_doc["hevy_api_key_updated_at"] = datetime.utcnow().isoformat()
            return self.db.save(user_doc)
        except couchdb.http.ResourceNotFound:
            return None

    def get_user_workout_history(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """Get a user's workout history."""
        if start_date and end_date:
            return self.get_workouts_by_date_range(start_date, end_date)
        return (
            self.get_all_documents()
        )  # You might want to add a user_id field to workouts for better filtering
