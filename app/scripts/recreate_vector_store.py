"""
Script to recreate the vector store with the correct metadata structure.
"""

import logging
import os
import shutil
from typing import List

from config.database import Database
from services.vector_store import ExerciseVectorStore

# Configure logging
logger = logging.getLogger(__name__)


def recreate_vector_store():
    """Recreate the vector store with the correct metadata structure."""
    try:
        # Initialize database and vector store
        db = Database()
        vector_store = ExerciseVectorStore()

        # Get all exercises from the database
        exercises = db.get_exercises(include_custom=True)
        logger.info(f"Found {len(exercises)} exercises in the database")

        # Delete the existing vector store directory
        if os.path.exists(vector_store.persist_directory):
            logger.info(
                f"Deleting existing vector store at {vector_store.persist_directory}"
            )
            shutil.rmtree(vector_store.persist_directory)

        # Create a new vector store
        logger.info("Creating new vector store")
        vector_store = ExerciseVectorStore()

        # Add exercises to the new vector store
        logger.info("Adding exercises to the new vector store")
        vector_store.add_exercises(exercises)

        logger.info("Vector store recreation completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error recreating vector store: {str(e)}")
        return False


if __name__ == "__main__":
    recreate_vector_store()
