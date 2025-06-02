import logging
from datetime import datetime, timedelta, timezone

import gradio as gr

from app.config.database import Database
from app.models.user import UserProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def dashboard_view(state):
    """Display the dashboard page."""
    with gr.Column():
        # Welcome message
        welcome_message = gr.Markdown()

        # Stats section
        with gr.Row():
            with gr.Column():
                total_workouts = gr.Markdown("### Total Workouts\nLoading...")
                avg_workouts = gr.Markdown("### Average Workouts per Week\nLoading...")
            with gr.Column():
                last_workout = gr.Markdown("### Last Workout\nLoading...")
                workout_streak = gr.Markdown("### Current Streak\nLoading...")

        # Goals section
        with gr.Row():
            goals_section = gr.Markdown("### Your Fitness Goals\nLoading...")

        # Active injuries section
        with gr.Row():
            injuries_section = gr.Markdown("### Active Injuries\nLoading...")

        # Add a hidden button for initial data loading
        load_data_btn = gr.Button("Load Data", visible=False)

        def update_dashboard(user_state):
            logger.info("Dashboard update called with user state")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(f"User state has value attr: {hasattr(user_state, 'value')}")
            if hasattr(user_state, "value"):
                logger.info(f"User state value: {user_state.value}")

            if not user_state:
                logger.warning("No user state provided to dashboard")
                return (
                    gr.update(value="Please log in to view your dashboard"),
                    gr.update(value="### Total Workouts\nPlease log in to view stats"),
                    gr.update(
                        value="### Average Workouts per Week\nPlease log in to view stats"
                    ),
                    gr.update(value="### Last Workout\nPlease log in to view stats"),
                    gr.update(value="### Current Streak\nPlease log in to view stats"),
                    gr.update(
                        value="### Your Fitness Goals\nPlease log in to view goals"
                    ),
                    gr.update(
                        value="### Active Injuries\nPlease log in to view injuries"
                    ),
                )

            try:
                # Get user profile
                user_id = (
                    user_state.value.get("id")
                    if hasattr(user_state, "value")
                    else user_state.get("id")
                )
                logger.info(f"Extracted user ID: {user_id}")
                if not user_id:
                    logger.error("No user ID found in state")
                    return (
                        gr.update(value="Error: User ID not found in state"),
                        gr.update(value="### Total Workouts\nError loading stats"),
                        gr.update(
                            value="### Average Workouts per Week\nError loading stats"
                        ),
                        gr.update(value="### Last Workout\nError loading stats"),
                        gr.update(value="### Current Streak\nError loading stats"),
                        gr.update(value="### Your Fitness Goals\nError loading goals"),
                        gr.update(value="### Active Injuries\nError loading injuries"),
                    )

                user_doc = db.get_document(user_id)
                logger.info(f"Retrieved user document: {bool(user_doc)}")
                if not user_doc:
                    logger.error(f"User document not found for ID: {user_id}")
                    return (
                        gr.update(value="Error: User profile not found"),
                        gr.update(value="### Total Workouts\nError loading stats"),
                        gr.update(
                            value="### Average Workouts per Week\nError loading stats"
                        ),
                        gr.update(value="### Last Workout\nError loading stats"),
                        gr.update(value="### Current Streak\nError loading stats"),
                        gr.update(value="### Your Fitness Goals\nError loading goals"),
                        gr.update(value="### Active Injuries\nError loading injuries"),
                    )

                user = UserProfile.from_dict(user_doc)

                # Get workout stats
                now = datetime.now(timezone.utc)
                thirty_days_ago = now - timedelta(days=30)
                stats = db.get_workout_stats(thirty_days_ago, now)

                # The stats view now returns a single aggregated result
                if stats and len(stats) > 0:
                    stats_data = stats[0]  # Get the first (and only) result
                    total_workouts_count = stats_data.get("total_workouts", 0)
                    avg_workouts_per_week = (
                        total_workouts_count / 4
                    )  # Approximate for 30 days

                    # Get last workout from the stats
                    last_workout_info = stats_data.get("last_workout", {})
                    last_workout_date = (
                        last_workout_info.get("date") if last_workout_info else None
                    )
                else:
                    total_workouts_count = 0
                    avg_workouts_per_week = 0
                    last_workout_date = None

                # Calculate streak
                streak = 0
                current_date = now.date()
                while True:
                    date_stats = db.get_workout_stats(
                        datetime.combine(current_date, datetime.min.time()),
                        datetime.combine(current_date, datetime.max.time()),
                    )
                    if not date_stats or not any(
                        stat.get("total_workouts", 0) > 0 for stat in date_stats
                    ):
                        break
                    streak += 1
                    current_date -= timedelta(days=1)

                # Format goals
                goals_text = "\n".join(
                    [f"- {goal.value}" for goal in user.fitness_goals]
                )

                # Format active injuries
                active_injuries = [i for i in user.injuries if i.is_active]
                injuries_text = (
                    "\n".join(
                        [
                            f"- {injury.description} ({injury.body_part}) - {injury.severity.value} severity"
                            for injury in active_injuries
                        ]
                    )
                    if active_injuries
                    else "No active injuries"
                )

                return (
                    gr.update(value=f"# Welcome back, {user.username}! 👋"),
                    gr.update(
                        value=f"### Total Workouts\n{total_workouts_count} workouts in the last 30 days"
                    ),
                    gr.update(
                        value=f"### Average Workouts per Week\n{avg_workouts_per_week:.1f} workouts"
                    ),
                    gr.update(
                        value=f"### Last Workout\n{last_workout_date or 'No workouts yet'}"
                    ),
                    gr.update(value=f"### Current Streak\n{streak} days"),
                    gr.update(value=f"### Your Fitness Goals\n{goals_text}"),
                    gr.update(value=f"### Active Injuries\n{injuries_text}"),
                )

            except Exception as e:
                logger.error(f"Error updating dashboard: {str(e)}", exc_info=True)
                return (
                    gr.update(value="Error loading dashboard"),
                    gr.update(value="### Total Workouts\nError loading stats"),
                    gr.update(
                        value="### Average Workouts per Week\nError loading stats"
                    ),
                    gr.update(value="### Last Workout\nError loading stats"),
                    gr.update(value="### Current Streak\nError loading stats"),
                    gr.update(value="### Your Fitness Goals\nError loading goals"),
                    gr.update(value="### Active Injuries\nError loading injuries"),
                )

        # Load initial data when page is shown
        load_data_btn.click(
            fn=update_dashboard,
            inputs=[state["user_state"]],
            outputs=[
                welcome_message,
                total_workouts,
                avg_workouts,
                last_workout,
                workout_streak,
                goals_section,
                injuries_section,
            ],
        )

        # Add logging to help debug state issues
        logger.info("Setting up dashboard event handlers")
        logger.info(f"User state type: {type(state['user_state'])}")
        logger.info(
            f"User state value: {state['user_state'].value if hasattr(state['user_state'], 'value') else state['user_state']}"
        )

        return (
            welcome_message,
            total_workouts,
            avg_workouts,
            last_workout,
            workout_streak,
            goals_section,
            injuries_section,
            load_data_btn,
            update_dashboard,
        )
