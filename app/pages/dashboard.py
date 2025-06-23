import logging
from datetime import datetime, timedelta, timezone

import dateutil.parser
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
        refresh_needed = gr.State(False)

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
                return gr.update(value="Syncing workouts..."), False
            elif status == "complete":
                SYNC_STATUS["status"] = "idle"
                return gr.update(value="Sync complete!"), True
            elif status == "error":
                SYNC_STATUS["status"] = "idle"
                return gr.update(value="Sync failed!"), True
            else:
                return gr.update(value=""), False

        def handle_refresh_change(refresh_flag, user_state):
            if refresh_flag:
                dashboard_updates = update_dashboard(user_state)
                # Reset refresh_needed to False after update
                return (False, *dashboard_updates)
            else:
                # No update needed
                return (False,) + (gr.update(),) * 7

        # TODO: This method is too long and needs to be refactored
        def update_dashboard(user_state):
            logger.info("Dashboard update called with user state")
            logger.info(f"User state type: {type(user_state)}")
            logger.info(f"User state value: {user_state}")
            logger.info(f"User state has value attr: {hasattr(user_state, 'value')}")

            if "id" not in user_state:
                logger.warning("No user id in user_state")
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
                user_id = user_state["id"]
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

                # Get workout stats for the last 30 days
                now = datetime.now(timezone.utc)
                thirty_days_ago = now - timedelta(days=30)
                stats = db.get_workout_stats(user_id, thirty_days_ago, now)
                logger.info(f"Workout stats: {stats}")

                # The stats view now returns a single aggregated result per user
                if stats and len(stats) > 0:
                    stats_data = stats[0]  # Get the first (and only) result
                    total_workouts_count = stats_data.get("total_workouts", 0)
                    avg_workouts_per_week = (
                        total_workouts_count / 4
                    )  # Approximate for 30 days
                else:
                    total_workouts_count = 0
                    avg_workouts_per_week = 0.0

                # Fetch all workouts in the last 30 days for streak and last workout
                # We'll use the Mango query approach for this
                # (Assume you have a method to fetch all workout docs for the user and date range)
                # We'll use the same get_workout_stats, but you may want a dedicated method for raw docs
                # For now, let's assume get_workout_stats returns a list of dicts, each with last_workout_date
                # If not, you may need to adjust this to fetch raw docs
                # We'll use the stats list as a proxy for all workouts
                all_workouts = []
                # Try to get all workout docs for the user in the date range
                try:
                    # If you have a method like db.get_workouts(user_id, start, end), use it
                    # TODO: Implement this db.get_workouts method
                    # Otherwise, fallback to stats (may need to adjust)
                    all_workouts = [
                        w
                        for w in db.get_workouts_by_date_range(thirty_days_ago, now)
                        if w.get("user_id") == user.id
                    ]
                except Exception:
                    # Fallback: try to use stats if get_workouts is not available
                    all_workouts = []

                # If get_workouts is not available, you may need to implement it
                # For now, let's check if all_workouts is empty, and if so, try to use stats
                if not all_workouts:
                    # Try to reconstruct from stats (may not have all dates)
                    all_workouts = []
                    for w in stats:
                        dt = w.get("last_workout_date")
                        if dt:
                            all_workouts.append({"start_time": dt})

                # Find the last workout date
                last_workout_date = None
                if all_workouts:
                    # Get the max start_time
                    last_workout_date = max(
                        w["start_time"] for w in all_workouts if w.get("start_time")
                    )

                if last_workout_date:
                    dt = dateutil.parser.parse(last_workout_date)
                    last_workout_str = dt.strftime("%Y-%m-%d")
                else:
                    last_workout_str = "No workouts yet"

                logger.info(f"Total workouts count: {total_workouts_count}")
                logger.info(f"Avg workouts per week: {avg_workouts_per_week}")
                logger.info(f"Last workout date: {last_workout_str}")

                # Calculate streak using the set of workout dates
                dates_with_workouts = set()
                for w in all_workouts:
                    dt = w.get("start_time")
                    if dt:
                        date_only = dt[:10]  # 'YYYY-MM-DD'
                        dates_with_workouts.add(date_only)

                logger.info(f"Dates with workouts: {dates_with_workouts}")

                # Calculate streak
                # TODO: Refactor to robustly handle user timezone
                # TODO: Refactor to show streaks longer than 30 days
                streak = 0
                current_date = now.date() - timedelta(days=1)
                logger.info(f"Current date: {current_date}")
                while True:
                    if current_date.isoformat() in dates_with_workouts:
                        streak += 1
                        current_date -= timedelta(days=1)
                    else:
                        break

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
                    gr.update(value=f"### Last Workout\n{last_workout_str}"),
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
            outputs=[sync_status, refresh_needed],
        )

        # When refresh_needed changes to True, update dashboard and reset refresh_needed
        refresh_needed.change(
            fn=handle_refresh_change,
            inputs=[refresh_needed, state["user_state"]],
            outputs=[
                refresh_needed,
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
            refresh_needed,
        )
