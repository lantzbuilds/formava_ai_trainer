from app.config.database import Database
from app.services.vector_store import ExerciseVectorStore


def bootstrap_vectorstore():
    db = Database()
    vector_store = ExerciseVectorStore()

    workouts = db.get_all_workouts()
    if not workouts:
        print("⚠️ No workouts found in database.")
        return

    documents = [
        {
            "id": workout["_id"],
            "text": f"{workout.get('type', '')} - {workout.get('start_time', '')} - {workout.get('notes', '')}",
        }
        for workout in workouts
    ]

    vector_store.add_workout_history(documents)
    print(f"✅ Bootstrapped {len(documents)} workouts into vectorstore.")


if __name__ == "__main__":
    bootstrap_vectorstore()
