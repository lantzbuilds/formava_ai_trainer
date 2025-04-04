"""
AI recommendations page for the AI Personal Trainer application.
"""

import logging
from datetime import datetime, timedelta, timezone

import streamlit as st

from config.database import Database
from models.user import UserProfile
from services.openai_service import OpenAIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db = Database()
openai_service = OpenAIService()


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
    exercises = db.get_exercises()

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
        total_exercises = sum(w["exercise_count"] for w in workouts)
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

    if st.button("Generate Recommendations"):
        with st.spinner("Generating personalized recommendations..."):
            try:
                # Prepare context for AI
                context = {
                    "user_profile": user.model_dump(),
                    "recent_workouts": workouts,
                    "available_exercises": exercises,
                    "cardio_option": cardio_option,
                }

                # Get recommendations from OpenAI
                recommendations = openai_service.get_workout_recommendations(context)

                # Display recommendations
                st.write("### Personalized Workout Plan")

                # Check if recommendations contain separate cardio section
                if (
                    isinstance(recommendations, dict)
                    and "cardio_recommendations" in recommendations
                ):
                    # Display workout routine
                    if "workout_routine" in recommendations:
                        st.write("#### Workout Routine")
                        st.write(recommendations["workout_routine"])

                    # Display cardio recommendations separately
                    st.write("#### Cardio Recommendations")
                    st.write(recommendations["cardio_recommendations"])
                else:
                    # Display combined recommendations
                    st.write(recommendations)

                # Save recommendations to database
                db.save_ai_recommendations(
                    st.session_state.user_id,
                    recommendations,
                    datetime.now(timezone.utc),
                )

                st.success("Recommendations generated successfully!")
            except Exception as e:
                logger.error(f"Error generating recommendations: {str(e)}")
                st.error(f"Failed to generate recommendations: {str(e)}")
    else:
        st.info(
            "Click the button above to generate personalized workout recommendations based on your profile and workout history."
        )
