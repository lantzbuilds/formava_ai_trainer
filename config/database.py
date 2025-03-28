import os
from datetime import datetime

import couchdb
from dotenv import load_dotenv

from .views import create_workout_views

load_dotenv()


class Database:
    def __init__(self):
        self.server = couchdb.Server(
            f'http://{os.getenv("COUCHDB_USER", "admin")}:{os.getenv("COUCHDB_PASSWORD", "password")}@localhost:5984/'
        )
        self.db = None
        self._init_database()
        self._init_views()

    def _init_database(self):
        """Initialize the database and create it if it doesn't exist."""
        db_name = os.getenv("COUCHDB_DATABASE", "ai_personal_trainer")
        try:
            self.db = self.server[db_name]
        except couchdb.http.ResourceNotFound:
            self.db = self.server.create(db_name)

    def _init_views(self):
        """Initialize CouchDB views."""
        create_workout_views(self.db)

    def save_document(self, doc):
        """Save a document to the database."""
        return self.db.save(doc)

    def get_document(self, doc_id):
        """Retrieve a document by ID."""
        try:
            return self.db[doc_id]
        except couchdb.http.ResourceNotFound:
            return None

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
