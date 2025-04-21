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
from services.routine_folder_builder import RoutineFolderBuilder
from services.vector_store import ExerciseVectorStore
from utils.formatters import format_routine_markdown

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
                if muscle.get("is_primary", False):
                    muscle_name = muscle.get("name", "Unknown")
                    if muscle_name not in muscle_groups:
                        muscle_groups[muscle_name] = 0
                    muscle_groups[muscle_name] += 1

        # TODO: likely remove this section
        st.write("**Exercises by primary muscle group:**")
        for muscle, count in muscle_groups.items():
            st.write(f"- {muscle}: {count}")

    # Get user preferences for routine generation
    st.subheader("Routine Generation Preferences")
    col1, col2, col3 = st.columns(3)
    with col1:
        split_type = st.selectbox(
            "Workout Split Type",
            ["auto", "full_body", "upper_lower", "push_pull"],
            help="Choose how to split your workouts. 'auto' will determine based on your experience level and days per week.",
        )
    with col2:
        period = st.selectbox(
            "Time Period",
            ["week", "month"],
            help="Generate routines for the upcoming week or month",
        )
    with col3:
        include_cardio = st.checkbox(
            "Include Cardio",
            value=True,
            help="Include cardio exercises in the generated routines",
        )

    # Get date range for the folder name
    date_range = RoutineFolderBuilder.get_date_range(period)
    suggested_title = (
        f"{split_type.replace('_', ' ').title()} Workout Plan - {date_range}"
    )

    # Add editable title field
    routine_title = st.text_input(
        "Routine Folder Title",
        value=suggested_title,
        help="Edit the title for your workout routine folder",
    )

    # Generate recommendations
    if st.button("Generate Recommendations"):
        # TODO: if possible, change spinner messages on intervals, or add a progress bar
        with st.spinner("Generating workout recommendations..."):
            try:
                # Create context for routine generation
                context = {
                    "user_id": st.session_state.user_id,
                    "user_profile": {
                        "experience_level": user.experience_level,
                        "fitness_goals": [g.value for g in user.fitness_goals],
                        "preferred_workout_duration": user.preferred_workout_duration,
                        "injuries": [
                            {
                                "description": i.description,
                                "body_part": i.body_part,
                                "is_active": i.is_active,
                            }
                            for i in user.injuries
                        ],
                        "workout_schedule": {
                            "days_per_week": user.preferred_workout_days,
                        },
                    },
                    "generation_preferences": {
                        "split_type": split_type,
                        "include_cardio": include_cardio,
                    },
                }

                # Generate the routine folder
                routine_folder = openai_service.generate_routine_folder(
                    name=routine_title,
                    description="Personalized workout plan based on your profile and goals",
                    context=context,
                    period=period,
                )

                if routine_folder:
                    # Store the generated routine in session state
                    st.session_state.generated_routine = routine_folder

                    # Display the generated routine folder
                    st.success("Routine folder generated successfully!")

                    # Display folder information
                    st.markdown(f"## {routine_folder['name']}")
                    st.markdown(f"*{routine_folder['description']}*")
                    st.markdown(
                        f"**Split Type:** {routine_folder['split_type'].replace('_', ' ').title()}"
                    )
                    st.markdown(f"**Days per Week:** {routine_folder['days_per_week']}")
                    st.markdown(f"**Period:** {routine_folder['period'].title()}")
                    st.markdown(f"**Date Range:** {routine_folder['date_range']}")

                    # Display each routine
                    for routine in routine_folder["routines"]:
                        st.markdown("---")  # Add a separator between routines
                        st.markdown(format_routine_markdown(routine))
                else:
                    st.error("Failed to generate routine folder. Please try again.")
            except Exception as e:
                logger.error(f"Error generating recommendations: {str(e)}")
                st.error(f"Error generating recommendations: {str(e)}")
    else:
        st.info(
            "Click the button above to generate personalized workout recommendations based on your profile and workout history."
        )
    # TODO: redirect to Routines page after saving to Hevy? or display saved routine here?
    # Save to Hevy button (outside the generation block)
    if "generated_routine" in st.session_state:
        if st.button("Save to Hevy"):
            try:
                hevy_api = HevyAPI(user.hevy_api_key)
                saved_folder = hevy_api.save_routine_folder(
                    routine_folder=st.session_state.generated_routine,
                    user_id=st.session_state.user_id,
                    db=db,
                )

                if saved_folder:
                    st.success("Routine folder saved to Hevy successfully!")
                else:
                    st.error("Failed to save routine folder to Hevy. Please try again.")
            except Exception as e:
                logger.error(f"Error saving to Hevy: {str(e)}")
                st.error(f"Error saving to Hevy: {str(e)}")
