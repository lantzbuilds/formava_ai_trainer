import logging
from datetime import datetime, timedelta, timezone

import gradio as gr

from app.config.database import Database
from app.models.user import UserProfile
from app.services.sync import sync_hevy_data
from app.state.sync_status import SYNC_STATUS

# Configure logging
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

        # Add sync controls to dashboard
        with gr.Row():
            sync_recent_btn = gr.Button("Sync Recent Workouts (Last 30 Days)")
            sync_full_btn = gr.Button("Sync Full History")
        sync_status = gr.Markdown("")
        is_syncing = gr.State(False)
        sync_status_timer = gr.Timer(value=2.0, active=True)

        # Add a hidden button for initial data loading
        load_data_btn = gr.Button("Load Data", visible=False)

        def start_sync(user_state, sync_type):
            import threading

            from app.services.sync import sync_hevy_data

            if SYNC_STATUS["status"] == "syncing":
                return "Sync already in progress..."

            def run_sync():
                try:
                    sync_hevy_data(user_state, sync_type)
                    SYNC_STATUS["status"] = "complete"
                except Exception as e:
                    SYNC_STATUS["status"] = "error"

            SYNC_STATUS["status"] = "syncing"
            threading.Thread(target=run_sync, daemon=True).start()
            return "Syncing workouts..."

        def poll_sync_status():
            status = SYNC_STATUS["status"]
            if status == "syncing":
                return gr.update(value="Syncing workouts...")
            elif status == "complete":
                SYNC_STATUS["status"] = "idle"
                return gr.update(value="Sync complete!")
            elif status == "error":
                SYNC_STATUS["status"] = "idle"
                return gr.update(value="Sync failed!")
            else:
                return gr.update(value="")

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
                stats = db.get_workout_stats(user_id, thirty_days_ago, now)

                # The stats view now returns a single aggregated result per user
                if stats and len(stats) > 0:
                    stats_data = stats[0]  # Get the first (and only) result
                    total_workouts_count = stats_data.get("total_workouts", 0)
                    avg_workouts_per_week = (
                        total_workouts_count / 4
                    )  # Approximate for 30 days

                    last_workout_date = stats_data.get("last_workout_date")
                else:
                    total_workouts_count = 0
                    avg_workouts_per_week = 0.0
                    last_workout_date = None

                # Calculate streak
                streak = 0
                current_date = now.date()
                while True:
                    day_start = datetime.combine(
                        current_date, datetime.min.time(), tzinfo=timezone.utc
                    )
                    day_end = datetime.combine(
                        current_date, datetime.max.time(), tzinfo=timezone.utc
                    )
                    date_stats = db.get_workout_stats(
                        user_id,
                        day_start,
                        day_end,
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

                if is_syncing_val == "syncing":
                    sync_status.update(value="Syncing workouts...")

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

        # Add sync button event handlers
        sync_recent_btn.click(
            fn=lambda user_state: start_sync(user_state, "recent"),
            inputs=[state["user_state"]],
            outputs=[sync_status],
        )
        sync_full_btn.click(
            fn=lambda user_state: start_sync(user_state, "full"),
            inputs=[state["user_state"]],
            outputs=[sync_status],
        )
        # Poll sync status every 2 seconds using Timer
        sync_status_timer.tick(
            fn=poll_sync_status,
            inputs=[],
            outputs=[sync_status],
        )

        # Add logging to help debug state issues
        logger.info("Setting up dashboard event handlers")
        logger.info(f"User state type: {type(state['user_state'])}")
        logger.info(f"User state value: {state['user_state']}")

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
            sync_recent_btn,
            sync_full_btn,
            sync_status,
            is_syncing,
            sync_status_timer,
        )
