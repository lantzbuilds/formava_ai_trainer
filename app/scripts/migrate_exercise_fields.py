#!/usr/bin/env python3
import logging
from typing import Dict, List

from config.database import Database

# Configure logging
logger = logging.getLogger(__name__)


def migrate_exercises(db: Database) -> None:
    """Migrate exercises from 'name' to 'title' field."""
    try:
        # Get all exercises
        exercises = db.get_exercises(include_custom=True)
        logger.info(f"Found {len(exercises)} exercises to migrate")

        # Process each exercise
        migrated_count = 0
        for exercise in exercises:
            # Skip if already has title
            if "title" in exercise:
                continue

            # Get name and ensure it exists
            name = exercise.get("name")
            if not name:
                logger.warning(f"Skipping exercise with no name: {exercise}")
                continue

            # Add title field
            exercise["title"] = name
            migrated_count += 1

            # Save the updated exercise
            db.save_exercise(exercise)
            logger.info(f"Migrated exercise: {name} -> {exercise['title']}")

        logger.info(f"Successfully migrated {migrated_count} exercises")
    except Exception as e:
        logger.error(f"Error migrating exercises: {str(e)}")
        raise


def main():
    try:
        logger.info("Starting exercise field migration")
        db = Database()
        migrate_exercises(db)
        logger.info("Exercise field migration completed successfully")
    except Exception as e:
        logger.error(f"Error in migration script: {str(e)}")
        raise


if __name__ == "__main__":
    main()
