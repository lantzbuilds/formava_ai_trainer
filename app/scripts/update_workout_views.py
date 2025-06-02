#!/usr/bin/env python3
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent)
sys.path.append(app_dir)

from config.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("Starting workout views update")
        db = Database()
        db.recreate_workouts_design_document()
        logger.info("Workout views update completed successfully")
    except Exception as e:
        logger.error(f"Error updating workout views: {str(e)}")
        raise


if __name__ == "__main__":
    main()
