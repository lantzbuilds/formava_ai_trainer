import logging

from app.config.database import Database
from app.services.vector_store import ExerciseVectorStore

logger = logging.getLogger(__name__)


def bootstrap_vectorstore():
    """Bootstrap the vector store with exercises and workout history."""
    db = Database()
    vector_store = ExerciseVectorStore()

    # First, add exercises to the vector store
    logger.info("Adding exercises to vector store...")
    exercises = db.get_all_exercises()
    if not exercises:
        logger.warning("No exercises found in database!")
        logger.warning("Vector store will be empty - routine generation will fail.")
        logger.warning(
            "Solution: Run 'python app/scripts/populate_exercises.py' first."
        )
        # Don't fail the app startup, just continue without exercises
        return False

    logger.info(f"Adding {len(exercises)} exercises to vector store...")
    vector_store.add_exercises(exercises)

    # Verify exercises were added
    valid_ids, name_to_id = vector_store.get_all_exercise_ids_and_names()
    logger.info(f"Vector store now has {len(valid_ids)} exercise IDs")

    if len(valid_ids) == 0:
        logger.error("Failed to add exercises to vector store!")
        return False

    # Then, add workout history
    logger.info("Adding workout history to vector store...")
    workouts = db.get_all_workouts()
    if not workouts:
        logger.info(
            "No workouts found in database - this is normal for new deployments."
        )
        logger.info(
            "Exercises added successfully - vector store is ready for routine generation!"
        )
        return True

    vector_store.add_workout_history(workouts)
    logger.info(f"Bootstrapped {len(workouts)} workouts into vectorstore.")
    logger.info(
        f"Vector store fully populated with {len(valid_ids)} exercises and {len(workouts)} workouts!"
    )
    return True


if __name__ == "__main__":
    # When run standalone, use print statements for better visibility
    import sys

    # Override logger to use print for standalone execution
    class PrintLogger:
        def info(self, msg):
            print(f"ℹ️  {msg}")

        def warning(self, msg):
            print(f"⚠️  {msg}")

        def error(self, msg):
            print(f"❌ {msg}")

    logger = PrintLogger()

    success = bootstrap_vectorstore()
    if not success:
        print("\n💡 To fix this issue:")
        print("1. Run: python app/scripts/populate_exercises.py")
        print("2. Then run: python app/scripts/bootstrap_vectorstore.py")
        sys.exit(1)
    else:
        print("\n🎉 Vector store successfully bootstrapped!")
