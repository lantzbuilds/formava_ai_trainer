#!/usr/bin/env python3
import logging

from config.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("Starting exercise views update")
        db = Database()
        db.recreate_exercises_design_document()
        logger.info("Exercise views update completed successfully")
    except Exception as e:
        logger.error(f"Error updating exercise views: {str(e)}")
        raise


if __name__ == "__main__":
    main()
