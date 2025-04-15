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

    # Workout split selection
    split_type = st.radio(
        "Workout Split",
        ["Full Body", "Upper/Lower", "Push/Pull/Legs"],
        help="Choose your preferred workout split. Full Body is recommended for beginners.",
        index=0 if user.experience_level == "beginner" else 1,
    )

    # Time period selection
    period = st.radio(
        "Time Period",
        ["week", "month"],
        help="Choose whether to generate a week's worth of routines or a month's worth",
        format_func=lambda x: "Next Week" if x == "week" else "Next Month",
    )

    # Get date range for the folder name
    date_range = openai_service._get_date_range(period)
    default_folder_name = f"{split_type} Split - {date_range}"

    # Cardio recommendation options
    cardio_option = st.radio(
        "Cardio Recommendations",
        ["Include in workout routines", "Recommend separately"],
        help="Choose whether cardio should be included in workout routines or recommended separately",
    )

    # Routine folder name and description
    routine_name = st.text_input(
        "Routine Folder Name",
        default_folder_name,
        help="The name of the folder that will contain all your workout routines",
    )
    routine_description = st.text_area(
        "Routine Description",
        f"A personalized {split_type.lower()} workout plan based on your fitness goals and preferences.",
    )

    if st.button("Generate Recommendations"):
        with st.spinner("Generating personalized recommendations..."):
            try:
                # Get target muscle groups from fitness goals
                # TODO: reevaluate this mapping of muscle groups to fitness goals
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
                recommendations = openai_service.generate_routine_folder(
                    name=routine_name,
                    description=routine_description,
                    context=context,
                    period=period,
                )

                if not recommendations:
                    st.error("Failed to generate recommendations. Please try again.")
                    return

                # Save recommendations to database
                doc = {
                    "type": "recommendations",
                    "user_id": user.id,
                    "recommendations": recommendations,
                    "created_at": datetime.now().isoformat(),
                }
                db.save_document(doc)

                # Store recommendations in session state
                st.session_state.recommendations = recommendations

                # Display the generated routine folder
                st.subheader("Generated Workout Routine Folder")
                st.markdown(f"### {recommendations['name']}")
                st.markdown(f"**Description:** {recommendations['description']}")
                st.markdown(f"**Split Type:** {recommendations['split_type']}")
                st.markdown(f"**Date Range:** {recommendations['date_range']}")

                # Display each routine in the folder
                for routine in recommendations["routines"]:
                    with st.expander(f"{routine['hevy_api']['routine']['title']}"):
                        st.markdown(routine["routine_description"])
                        st.markdown(routine["hevy_api"]["routine"]["notes"])

                        # Display each exercise in the routine
                        for exercise in routine["hevy_api"]["routine"]["exercises"]:
                            st.subheader(f"Exercise: {exercise['title']}")
                            st.write(
                                f"**Description:** {exercise['exercise_description']}"
                            )
                            st.write(f"**Notes:** {exercise['notes']}")
                            st.write(
                                f"**Rest Period:** {exercise['rest_seconds']} seconds between sets"
                            )

                            # Display sets
                            st.write("**Sets:**")
                            for i, set_info in enumerate(exercise["sets"], 1):
                                set_details = []
                                if set_info.get("weight_kg") is not None:
                                    set_details.append(f"{set_info['weight_kg']} kg")
                                if set_info.get("reps") is not None:
                                    set_details.append(f"{set_info['reps']} reps")
                                if set_info.get("distance_meters") is not None:
                                    set_details.append(
                                        f"{set_info['distance_meters']} meters"
                                    )
                                if set_info.get("duration_seconds") is not None:
                                    set_details.append(
                                        f"{set_info['duration_seconds']} seconds"
                                    )

                                st.write(f"Set {i}: {', '.join(set_details)}")

                # Add buttons for saving to Hevy or regenerating
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save to Hevy"):
                        try:
                            # Save the routine folder to Hevy
                            hevy_api = HevyAPI()
                            for routine in recommendations["routines"]:
                                routine_data = routine["hevy_api"]["routine"]
                                response = hevy_api.create_routine(routine_data)

                                if not response or "id" not in response:
                                    st.error(
                                        f"Failed to save routine {routine_data['title']} to Hevy"
                                    )
                                    continue

                            st.success("All routines saved to Hevy successfully!")
                            # Clear the session state to allow generating a new routine
                            st.session_state.recommendations = None
                        except Exception as e:
                            st.error(f"Error saving routines to Hevy: {str(e)}")

                with col2:
                    if st.button("Regenerate Recommendations"):
                        # Clear the session state to allow generating a new routine
                        st.session_state.recommendations = None
                        st.rerun()

                st.success("Recommendations generated successfully!")
            except Exception as e:
                logger.error(f"Error generating recommendations: {str(e)}")
                st.error(f"Failed to generate recommendations: {str(e)}")
    else:
        st.info(
            "Click the button above to generate personalized workout recommendations based on your profile and workout history."
        )
