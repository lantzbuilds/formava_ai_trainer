"""
Script to test if exercises are properly indexed in the vector store.
"""

import logging
from typing import List

from services.vector_store import ExerciseVectorStore

# Configure logging
logger = logging.getLogger(__name__)


def test_vector_store():
    """Test if exercises are properly indexed in the vector store."""
    try:
        # Initialize vector store
        vector_store = ExerciseVectorStore()
        logger.info("Vector store initialized")

        # Define muscle groups to search for
        muscle_groups = ["chest", "back", "legs", "shoulders", "arms"]
        total_exercises = []

        # Search for exercises targeting each muscle group
        for muscle_group in muscle_groups:
            logger.info(f"\nSearching for {muscle_group} exercises:")
            # Use a more specific query that matches our content format
            query = f"Primary muscles: {muscle_group}"
            exercises = vector_store.search_exercises(query, k=5)
            logger.info(f"Found {len(exercises)} exercises for {muscle_group}")
            for exercise in exercises:
                logger.info(
                    f"- {exercise['title']} (Score: {exercise['similarity_score']:.2f})"
                )
                logger.info(
                    f"  Primary muscles: {[mg['name'] for mg in exercise['muscle_groups'] if mg['is_primary']]}"
                )
                logger.info(
                    f"  Secondary muscles: {[mg['name'] for mg in exercise['muscle_groups'] if not mg['is_primary']]}"
                )
                logger.info(
                    f"  Equipment: {[eq['name'] for eq in exercise['equipment']]}"
                )
            total_exercises.extend(exercises)

        logger.info(f"\nTotal exercises found: {len(total_exercises)}")

    except Exception as e:
        logger.error(f"Error testing vector store: {str(e)}")


if __name__ == "__main__":
    test_vector_store()
