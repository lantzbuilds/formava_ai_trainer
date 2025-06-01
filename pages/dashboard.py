import logging
from datetime import datetime, timedelta, timezone

import gradio as gr

from config.database import Database
from models.user import UserProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
db = Database()


def dashboard_view():
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

        def update_dashboard(user_state):
            if not user_state:
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
                user_doc = db.get_document(user_state["id"])
                if not user_doc:
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

                total_workouts_count = sum(stat["count"] for stat in stats)
                avg_workouts_per_week = (
                    total_workouts_count / 4
                )  # Approximate for 30 days

                # Get last workout
                last_workout_date = None
                if stats:
                    last_workout_date = max(
                        stat.get("start_time", "") for stat in stats
                    )

                # Calculate streak
                streak = 0
                current_date = now.date()
                while True:
                    date_stats = db.get_workout_stats(
                        datetime.combine(current_date, datetime.min.time()),
                        datetime.combine(current_date, datetime.max.time()),
                    )
                    if not date_stats or not any(
                        stat["count"] > 0 for stat in date_stats
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

        # Update dashboard when user state changes
        gr.on(
            fn=update_dashboard,
            inputs=[gr.State()],
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
