import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import gradio as gr

from app.config.database import Database
from app.models.user import UserProfile
from app.services.hevy_api import HevyAPI
from app.services.openai_service import OpenAIService
from app.services.routine_folder_builder import RoutineFolderBuilder
from app.services.vector_store import ExerciseVectorStore
from app.utils.formatters import format_routine_markdown

# Configure logging
logger = logging.getLogger(__name__)

# Initialize services
db = Database()
openai_service = OpenAIService()
vector_store = ExerciseVectorStore()

split_type_labels = {
    "auto": "Auto",
    "full_body": "Full Body",
    "upper_lower": "Upper/Lower",
    "push_pull": "Push/Pull",
}


def get_default_title(split_type, period):
    split_label = split_type_labels.get(split_type, split_type.title())
    date_range = RoutineFolderBuilder.get_date_range(period)
    return f"{split_label} - {date_range}"


def ai_recs_view(state):
    """Display the AI recommendations page."""
    with gr.Column():
        # Title
        gr.Markdown("# AI Recommendations")

        # User Profile Summary Section
        with gr.Group():
            gr.Markdown("## Your Profile Summary")
            profile_summary = gr.Markdown()

        # Workout History Summary Section
        with gr.Group():
            gr.Markdown("## Recent Workout History")
            workout_summary = gr.Markdown()

        # Available Exercises Summary Section
        with gr.Group():
            gr.Markdown("## Available Exercises")
            exercises_summary = gr.Markdown()

        # Routine Generation Preferences Section
        with gr.Group():
            gr.Markdown("## Routine Generation Preferences")

            with gr.Row():
                # TODO: Create a map for the split type choices strings to display names
                split_type = gr.Dropdown(
                    choices=["auto", "full_body", "upper_lower", "push_pull"],
                    label="Workout Split Type",
                    info="Choose how to split your workouts. 'auto' will determine based on your experience level and days per week.",
                    value="auto",
                )

                period = gr.Dropdown(
                    choices=["week", "month"],
                    label="Time Period",
                    info="Generate routines for the upcoming week or month",
                    value="week",
                )

                include_cardio = gr.Checkbox(
                    label="Include Cardio",
                    value=True,
                    info="Include cardio exercises in the generated routines",
                )

            # Set the default value for the title textbox
            initial_title = get_default_title("auto", "week")
            title = gr.Textbox(
                label="Routine Folder Title",
                value=initial_title,
                info="Edit the title for your workout routine folder",
            )

            generate_btn = gr.Button("Generate Recommendations")

        # Generated Routine Display Section
        with gr.Group():
            gr.Markdown("## Generated Routine")
            routine_display = gr.Markdown(" ")

        # Save to Hevy Section
        with gr.Group():
            save_btn = gr.Button("Save to Hevy")
            save_status = gr.Markdown()

        # Add a hidden button for initial data loading
        load_data_btn = gr.Button("Load Data", visible=False)

        loading_messages = [
            "🧠 Analyzing workout history...",
            "💡 Generating new exercise plan...",
            "🔥 Optimizing for strength and recovery...",
            "⏳ Almost done...",
        ]
        # Add state for loading
        loading_idx = gr.State(0)
        loading_active = gr.State(False)
        loading_timer = gr.Timer(value=2.0, active=False)

        def start_loading(*args):
            # Start loading: set index to 0, active to True, show first message
            return gr.update(value=loading_messages[0]), 0, True, gr.update(active=True)

        def cycle_loading(idx, active):
            if not active:
                return gr.update(), idx  # Don't update if not active
            next_idx = (idx + 1) % len(loading_messages)
            return gr.update(value=loading_messages[next_idx]), next_idx

        def generate_routine_llm(user_state, split, period, cardio, title):
            # This is called after loading starts, and will stop loading when done
            if "id" not in user_state:
                return (
                    gr.update(value="Please log in to generate recommendations."),
                    False,
                    gr.update(active=False),
                )
            try:
                user_id = user_state["id"]
                if not user_id:
                    return (
                        gr.update(value="User ID not found in state"),
                        False,
                        gr.update(active=False),
                    )
                user_doc = db.get_document(user_id)
                if not user_doc:
                    return (
                        gr.update(value="User profile not found"),
                        False,
                        gr.update(active=False),
                    )
                user = UserProfile(**user_doc)
                context = {
                    "user_id": user_id,
                    "user_profile": {
                        "experience_level": user.experience_level,
                        "fitness_goals": [g.value for g in user.fitness_goals],
                        "preferred_workout_duration": user.preferred_workout_duration,
                        "preferred_units": getattr(
                            user.preferred_units, "value", "imperial"
                        ),
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
                        "split_type": split,
                        "include_cardio": cardio,
                    },
                }
                routine_folder = openai_service.generate_routine_folder(
                    name=title,
                    description="Personalized workout plan based on your profile and goals",
                    context=context,
                    period=period,
                )
                if routine_folder:
                    state["generated_routine"] = routine_folder
                    display_text = f"## {routine_folder['name']}\n"
                    display_text += f"*{routine_folder['description']}*\n\n"
                    display_text += f"**Split Type:** {routine_folder['split_type'].replace('_', ' ').title()}\n"
                    display_text += (
                        f"**Days per Week:** {routine_folder['days_per_week']}\n"
                    )
                    display_text += f"**Period:** {routine_folder['period'].title()}\n"
                    display_text += (
                        f"**Date Range:** {routine_folder['date_range']}\n\n"
                    )
                    for routine in routine_folder["routines"]:
                        display_text += "---\n"
                        display_text += format_routine_markdown(
                            routine, getattr(user.preferred_units, "value", "imperial")
                        )
                    return gr.update(value=display_text), False, gr.update(active=False)
                else:
                    return (
                        gr.update(
                            value="Failed to generate routine folder. Please try again."
                        ),
                        False,
                        gr.update(active=False),
                    )
            except Exception as e:
                logger.error(f"Error generating recommendations: {str(e)}")
                return (
                    gr.update(value=f"Error generating recommendations: {str(e)}"),
                    False,
                    gr.update(active=False),
                )

        def update_ai_recs(user_state):
            """Load and display user data."""
            logger.info(f"Updating AI Recs")
            if "id" not in user_state:
                return (
                    "Please log in to view recommendations.",
                    "Please log in to view workout history.",
                    "Please log in to view available exercises.",
                    "Auto Workout Plan - Next Week",
                    "",
                )

            # Get user document from database
            user_id = user_state["id"]
            logger.info(f"User ID: {user_id}")
            if not user_id:
                return (
                    "User ID not found in state",
                    "User ID not found in state",
                    "User ID not found in state",
                    "Auto Workout Plan - Next Week",
                    "",
                )

            user_doc = db.get_document(user_id)
            logger.info(f"User doc: {user_doc}")
            if not user_doc:
                return (
                    "User profile not found",
                    "User profile not found",
                    "User profile not found",
                    "Auto Workout Plan - Next Week",
                    "",
                )

            # Create UserProfile instance
            user = UserProfile(**user_doc)

            # Build profile summary
            profile_text = f"""
            **Experience Level:** {user.experience_level}
            **Fitness Goals:** {', '.join([g.value for g in user.fitness_goals])}
            **Workout Schedule:** {user.preferred_workout_days} days per week
            **Preferred Duration:** {user.preferred_workout_duration} minutes
            """

            if user.injuries:
                profile_text += "\n**Active Injuries:**"
                for injury in user.injuries:
                    if injury.is_active:
                        profile_text += f"\n- {injury.description} ({injury.body_part})"
            else:
                profile_text += "\n**No active injuries**"

            # Get user's recent workouts
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            workouts = db.get_user_workout_history(user_id, start_date, end_date)

            # Build workout summary
            if workouts:
                workout_count = len(workouts)
                total_exercises = sum(len(w.get("exercises", [])) for w in workouts)
                avg_exercises = (
                    total_exercises / workout_count if workout_count > 0 else 0
                )

                workout_text = f"""
                **Workouts in last 30 days:** {workout_count}
                **Average exercises per workout:** {avg_exercises:.1f}
                """
            else:
                workout_text = "**No workouts recorded in the last 30 days**"

            # Get available exercises count
            exercises = db.get_exercises(user_id=user_id, include_custom=True)
            exercises_text = f"**Total exercises available:** {len(exercises)}"

            # Set default routine title
            date_range = RoutineFolderBuilder.get_date_range("week")
            default_title = f"Auto Workout Plan - {date_range}"

            return (
                profile_text,
                workout_text,
                exercises_text,
                default_title,
                "",
            )

        def save_to_hevy(user_state):
            """Save generated routine to Hevy."""
            if "id" not in user_state:
                return "Please log in to save to Hevy."

            try:
                # Get user document
                user_id = user_state["id"]
                if not user_id:
                    return "User ID not found in state"

                user_doc = db.get_document(user_id)
                if not user_doc:
                    return "User profile not found"

                user = UserProfile(**user_doc)

                if not user.hevy_api_key:
                    return "Hevy API key is not configured. Please configure it in your profile."

                hevy_api = HevyAPI(api_key=user.hevy_api_key, is_encrypted=True)
                saved_folder = hevy_api.save_routine_folder(
                    routine_folder=state["generated_routine"],
                    user_id=user_id,
                    db=db,
                )

                if saved_folder:
                    return "Routine folder saved to Hevy successfully!"
                else:
                    return "Failed to save routine folder to Hevy. Please try again."

            except Exception as e:
                logger.error(f"Error saving to Hevy: {str(e)}")
                return f"Error saving to Hevy: {str(e)}"

        def update_title(split_type, period):
            return get_default_title(split_type, period)

        # Set up event handlers
        generate_btn.click(
            fn=start_loading,
            inputs=[],
            outputs=[routine_display, loading_idx, loading_active, loading_timer],
        ).then(
            fn=generate_routine_llm,
            inputs=[state["user_state"], split_type, period, include_cardio, title],
            outputs=[routine_display, loading_active, loading_timer],
        )
        # 2. Timer cycles loading messages
        loading_timer.tick(
            fn=cycle_loading,
            inputs=[loading_idx, loading_active],
            outputs=[routine_display, loading_idx],
        )

        save_btn.click(
            fn=save_to_hevy, inputs=[state["user_state"]], outputs=save_status
        )

        # Load initial data when page is shown
        load_data_btn.click(
            fn=update_ai_recs,
            inputs=[state["user_state"]],
            outputs=[
                profile_summary,
                workout_summary,
                exercises_summary,
                title,
                save_status,
            ],
        )

        split_type.change(
            update_title,
            inputs=[split_type, period],
            outputs=title,
        )
        period.change(
            update_title,
            inputs=[split_type, period],
            outputs=title,
        )

        return [
            profile_summary,
            workout_summary,
            exercises_summary,
            routine_display,
            save_status,
            load_data_btn,
            update_ai_recs,
        ]
