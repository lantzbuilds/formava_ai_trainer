"""
AI recommendations page for the AI Personal Trainer application.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

import streamlit as st

from config.database import Database
from models.user import UserProfile
from services.hevy_api import HevyAPI
from services.openai_service import OpenAIService
from services.vector_store import ExerciseVectorStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db = Database()
openai_service = OpenAIService()
vector_store = ExerciseVectorStore()


def ai_recommendations_page():
    """Display the AI recommendations page."""
    st.title("AI Recommendations")

    # Get user document from database
    user_doc = db.get_document(st.session_state.user_id)
    if not user_doc:
        st.error("User profile not found")
        return

    # Create UserProfile instance
    user = UserProfile(**user_doc)

    # Get user's recent workouts
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    workouts = db.get_user_workout_history(
        st.session_state.user_id, start_date, end_date
    )

    # Get available exercises
    exercises = db.get_exercises(user_id=st.session_state.user_id, include_custom=True)

    # Display user's profile summary
    st.subheader("Your Profile Summary")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Experience Level:** {user.experience_level}")
        st.write(
            f"**Fitness Goals:** {', '.join([g.value for g in user.fitness_goals])}"
        )
        st.write(f"**Workout Schedule:** {user.preferred_workout_days} days per week")
        st.write(f"**Preferred Duration:** {user.preferred_workout_duration} minutes")
    with col2:
        if user.injuries:
            st.write("**Active Injuries:**")
            for injury in user.injuries:
                if injury.is_active:
                    st.write(f"- {injury.description} ({injury.body_part})")
        else:
            st.write("**No active injuries**")

    # Display workout history summary
    st.subheader("Recent Workout History")
    if workouts:
        workout_count = len(workouts)
        total_exercises = 0
        for workout in workouts:
            try:
                # Try to get exercise_count first
                if "exercise_count" in workout:
                    total_exercises += workout["exercise_count"]
                else:
                    # Fall back to counting exercises
                    total_exercises += len(workout.get("exercises", []))
            except Exception as e:
                logger.warning(f"Error counting exercises for workout: {str(e)}")
                # If both methods fail, skip this workout
                continue

        avg_exercises = total_exercises / workout_count if workout_count > 0 else 0
        st.write(f"**Workouts in last 30 days:** {workout_count}")
        st.write(f"**Average exercises per workout:** {avg_exercises:.1f}")
    else:
        st.write("**No workouts recorded in the last 30 days**")

    # Display available exercises summary
    st.subheader("Available Exercises")
    if exercises:
        st.write(f"**Total exercises available:** {len(exercises)}")

        # Group exercises by muscle group
        muscle_groups = {}
        for exercise in exercises:
            for muscle in exercise.get("muscle_groups", []):
                muscle_name = muscle.get("name", "Unknown")
                if muscle_name not in muscle_groups:
                    muscle_groups[muscle_name] = []
                muscle_groups[muscle_name].append(exercise.get("name", "Unknown"))

        # Display muscle groups and exercise counts
        st.write("**Exercises by muscle group:**")
        for muscle, exercise_list in muscle_groups.items():
            st.write(f"- {muscle}: {len(exercise_list)} exercises")
    else:
        st.write(
            "**No exercises available. Please sync with Hevy to get exercise data.**"
        )

    # Generate AI recommendations
    st.subheader("AI Recommendations")

    # Cardio recommendation options
    cardio_option = st.radio(
        "Cardio Recommendations",
        ["Include in workout routines", "Recommend separately"],
        help="Choose whether cardio should be included in workout routines or recommended separately",
    )

    # Routine name and description
    routine_name = st.text_input("Routine Name", "AI Generated Workout Plan")
    routine_description = st.text_area(
        "Routine Description",
        "A personalized workout plan based on your fitness goals and preferences.",
    )

    if st.button("Generate Recommendations"):
        with st.spinner("Generating personalized recommendations..."):
            try:
                # Get target muscle groups from fitness goals
                target_muscle_groups = set()
                for goal in user.fitness_goals:
                    if goal.value == "strength":
                        target_muscle_groups.update(
                            ["chest", "back", "legs", "shoulders", "arms"]
                        )
                    elif goal.value == "endurance":
                        target_muscle_groups.update(["legs", "core"])
                    elif goal.value == "flexibility":
                        target_muscle_groups.update(["core", "back", "legs"])
                    elif goal.value == "weight_loss":
                        target_muscle_groups.update(
                            ["chest", "back", "legs", "shoulders", "arms", "core"]
                        )

                # Get relevant exercises using vector store
                relevant_exercises = []
                for muscle_group in target_muscle_groups:
                    exercises = vector_store.get_exercises_by_muscle_group(
                        muscle_group=muscle_group,
                        difficulty=user.experience_level,
                        k=10,
                    )
                    relevant_exercises.extend(exercises)

                # Remove duplicates and limit to most relevant
                seen_ids = set()
                unique_exercises = []
                for exercise in relevant_exercises:
                    if exercise["id"] not in seen_ids:
                        seen_ids.add(exercise["id"])
                        unique_exercises.append(exercise)

                # Limit to 50 most relevant exercises
                relevant_exercises = sorted(
                    unique_exercises,
                    key=lambda x: x.get("similarity_score", 0),
                    reverse=True,
                )[:50]

                # Prepare context for AI
                context = {
                    "user_profile": {
                        "experience_level": user.experience_level,
                        "fitness_goals": [goal.value for goal in user.fitness_goals],
                        "preferred_workout_duration": user.preferred_workout_duration,
                        "injuries": (
                            [injury.model_dump() for injury in user.injuries]
                            if user.injuries
                            else []
                        ),
                    },
                    "recent_workouts": workouts,
                    "available_exercises": relevant_exercises,
                    "cardio_option": cardio_option,
                }

                # Get recommendations from OpenAI
                recommendations = openai_service.generate_routine(
                    name="AI-Generated Workout",
                    description="Personalized workout routine based on your profile and goals",
                    context=context,
                )

                # Display recommendations
                st.write("### Personalized Workout Plan")

                if recommendations and "human_readable" in recommendations:
                    # Display human-readable format
                    st.write(recommendations["human_readable"])
                else:
                    st.error(
                        "Failed to generate recommendations in the expected format."
                    )

                # Save recommendations to database
                db.save_document(
                    {
                        "type": "ai_recommendations",
                        "user_id": st.session_state.user_id,
                        "recommendations": recommendations,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

                # Add buttons for saving to Hevy or regenerating
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save to Hevy"):
                        with st.spinner("Saving routine to Hevy..."):
                            try:
                                # Initialize Hevy API
                                hevy_api = HevyAPI(user.hevy_api_key)

                                if recommendations and "hevy_api" in recommendations:
                                    # Save routine to Hevy
                                    result = hevy_api.create_routine(
                                        recommendations["hevy_api"]
                                    )

                                    if result:
                                        st.success(
                                            "Routine saved successfully to Hevy!"
                                        )
                                    else:
                                        st.error("Failed to save routine to Hevy.")
                                else:
                                    st.error("No Hevy API compatible routine found.")
                            except Exception as e:
                                logger.error(f"Error saving routine to Hevy: {str(e)}")
                                st.error(f"Error saving routine to Hevy: {str(e)}")

                with col2:
                    if st.button("Regenerate Recommendations"):
                        st.rerun()

                st.success("Recommendations generated successfully!")
            except Exception as e:
                logger.error(f"Error generating recommendations: {str(e)}")
                st.error(f"Failed to generate recommendations: {str(e)}")
    else:
        st.info(
            "Click the button above to generate personalized workout recommendations based on your profile and workout history."
        )
