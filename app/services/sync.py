from datetime import datetime, timedelta, timezone

from app.config.database import Database
from app.models.user import UserProfile
from app.services.hevy_api import HevyAPI
from app.services.vector_store import ExerciseVectorStore
from app.utils.crypto import decrypt_api_key

db = Database()
vector_store = ExerciseVectorStore()


def sync_hevy_data(user_state):
    if not user_state or not user_state.get("id"):
        return "No user logged in."

    user_doc = db.get_document(user_state["id"])
    if not user_doc:
        return "User profile not found."

    user = UserProfile(**user_doc)
    if not user.hevy_api_key:
        return "Hevy API key not configured."

    # Decrypt API key
    api_key = decrypt_api_key(user.hevy_api_key)
    hevy_api = HevyAPI(api_key, is_encrypted=False)

    # Sync base and custom exercises
    for include_custom in [False, True]:
        exercise_list = hevy_api.get_all_exercises(include_custom=include_custom)
        if exercise_list.exercises:
            exercises_data = [
                exercise.model_dump() for exercise in exercise_list.exercises
            ]
            db.save_exercises(
                exercises_data, user_id=user.id if include_custom else None
            )
            vector_store.add_exercises(exercises_data)

    # Sync recent workouts
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    workouts = hevy_api.get_workouts(start_date, end_date)
    if workouts:
        for workout in workouts:
            workout_data = {
                "hevy_id": workout["id"],
                "user_id": user.id,
                "title": workout.get("title", "Untitled Workout"),
                "description": workout.get("description", ""),
                "start_time": workout.get("start_time"),
                "end_time": workout.get("end_time"),
                "exercises": workout.get("exercises", []),
                "exercise_count": len(workout.get("exercises", [])),
            }
            db.save_workout(workout_data)
        vector_store.add_workout_history(workouts)
    return "Sync complete."
