"""
Route configuration for the AI Personal Trainer application.
"""

import functools
import logging
import threading

import gradio as gr

from app.config.database import Database
from app.models.user import UserProfile
from app.pages.ai_recs import ai_recs_view
from app.pages.dashboard import dashboard_view
from app.pages.landing import landing_page_view
from app.pages.login import login_view
from app.pages.profile import profile_view
from app.pages.register import register_view
from app.services.sync import sync_hevy_data
from app.state.sync_status import SYNC_STATUS

logger = logging.getLogger(__name__)
db = Database()


def handle_session_errors(func):
    """Decorator to handle session errors gracefully."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if "session" in error_msg or "404" in error_msg:
                logger.warning(f"Session error in {func.__name__}: {e}")
                # Return safe defaults for session errors
                return None
            else:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise

    return wrapper


def setup_routes(app, state):
    """Setup application routes and navigation."""
    with app:
        # Navigation Bar
        with gr.Row(elem_classes="nav-bar"):
            with gr.Column(scale=1, min_width=120):
                register_nav_button = gr.Button(
                    "Register", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                login_nav_button = gr.Button(
                    "Login", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                landing_nav_button = gr.Button(
                    "Home", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                dashboard_nav_button = gr.Button(
                    "Dashboard", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                ai_recs_nav_button = gr.Button(
                    "AI Recs", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                profile_nav_button = gr.Button(
                    "Profile", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                logout_nav_button = gr.Button(
                    "Logout", variant="secondary", elem_classes="nav-button"
                )

        # Main Content Area
        with gr.Column(elem_classes="page-container"):
            with gr.Group(visible=False) as register_block:
                register_components = register_view(
                    state,
                    register_nav_button,
                    login_nav_button,
                    landing_nav_button,
                    dashboard_nav_button,
                    ai_recs_nav_button,
                    profile_nav_button,
                    logout_nav_button,
                )
                (_, register_error, _) = register_components
            with gr.Group(visible=False) as login_block:
                login_components = login_view()
                (login_button, login_error, login_username, login_password) = (
                    login_components
                )
            with gr.Group(visible=True) as landing_block:
                landing_components = landing_page_view(state)
                (
                    title,
                    intro,
                    logo,
                    demo_btn,
                    use_demo_account,
                ) = landing_components
            with gr.Group(visible=False) as dashboard_block:
                dashboard_components = dashboard_view(state)
                (
                    welcome_message,
                    total_workouts,
                    avg_workouts,
                    last_workout,
                    workout_streak,
                    goals_section,
                    injuries_section,
                    dashboard_load_btn,
                    update_dashboard,
                    sync_recent_btn,
                    sync_full_btn,
                    sync_status,
                    is_syncing,
                    sync_status_timer,
                    refresh_needed,
                ) = dashboard_components
            with gr.Group(visible=False) as ai_recs_block:
                ai_recs_components = ai_recs_view(state)
                (
                    profile_summary,
                    workout_summary,
                    exercises_summary,
                    routine_display,
                    save_status,
                    ai_recs_load_btn,
                    update_ai_recs,
                ) = ai_recs_components
            with gr.Group(visible=False) as profile_block:
                profile_components = profile_view(state)
                (
                    profile_username,
                    email,
                    age,
                    sex,
                    height_feet,
                    height_inches,
                    weight_lbs,
                    experience,
                    preferred_units,
                    goals,
                    workout_days,
                    workout_duration,
                    hevy_status,
                    injuries_list,
                    profile_load_btn,
                    update_profile,
                ) = profile_components

        def handle_login(username, password, user_state):
            """Handle login attempt."""
            try:
                logger.info(f"Attempting login for username: {username}")

                # Validate input
                if not username or not password:
                    error_msg = "Please enter both username and password."
                    logger.warning("Login attempt with missing credentials")
                    return (
                        {},  # user_state
                        gr.update(value=error_msg, visible=True),  # error_message
                        gr.update(value=""),  # clear username
                        gr.update(value=""),  # clear password
                        *state["update_nav_visibility"](None),  # nav buttons
                        "login",  # current_page
                        *state["update_visibility"]("login")[7:],  # button variants
                    )

                # Get user from database
                user_doc = db.get_user_by_username(username)
                if not user_doc:
                    error_msg = "Invalid username or password. Please check your credentials and try again."
                    logger.warning(f"User not found: {username}")
                    return (
                        {},  # user_state
                        gr.update(value=error_msg, visible=True),  # error_message
                        gr.update(value=""),  # clear username
                        gr.update(value=""),  # clear password
                        *state["update_nav_visibility"](None),  # nav buttons
                        "login",  # current_page
                        *state["update_visibility"]("login")[7:],  # button variants
                    )

                # Create UserProfile instance from document
                user_profile = UserProfile.from_dict(user_doc)

                # Verify password using the UserProfile instance
                if not user_profile.verify_password(password):
                    error_msg = "Invalid username or password. Please check your credentials and try again."
                    logger.warning(f"Invalid password for user: {username}")
                    return (
                        {},  # user_state
                        gr.update(value=error_msg, visible=True),  # error_message
                        gr.update(value=""),  # clear username
                        gr.update(value=""),  # clear password
                        *state["update_nav_visibility"](None),  # nav buttons
                        "login",  # current_page
                        *state["update_visibility"]("login")[7:],  # button variants
                    )

                # Return user object for state management
                user = {
                    "id": user_doc["_id"],
                    "username": user_doc["username"],
                    "email": user_doc["email"],
                }
                logger.info(
                    f"Login successful for user: {username}, returning user state: {user}"
                )
                # TODO: Add a guard to check if user is a valid dict with an id before starting sync
                # Sync Hevy data
                threading.Thread(
                    target=sync_hevy_data, args=(user,), daemon=True
                ).start()

                # Update navigation and redirect to dashboard
                nav_updates = state["update_nav_visibility"](user)
                logger.info(f"Updating navigation with user state: {user}")
                return (
                    user,  # user_state
                    gr.update(value="", visible=False),  # error_message (clear)
                    *nav_updates,  # nav buttons
                    "dashboard",  # current_page
                    *state["update_visibility"]("dashboard")[7:],  # button variants
                )

            except Exception as e:
                error_msg = (
                    "An unexpected error occurred during login. Please try again."
                )
                logger.error(f"Login failed: {str(e)}", exc_info=True)
                return (
                    {},  # user_state
                    gr.update(value=error_msg, visible=True),  # error_message
                    gr.update(value=""),  # clear username
                    gr.update(value=""),  # clear password
                    *state["update_nav_visibility"](None),  # nav buttons
                    "login",  # current_page
                    *state["update_visibility"]("login")[7:],  # button variants
                )

        def handle_demo_login(user_state):
            """Handle demo account login."""
            try:
                logger.info("Attempting demo account login")
                # Get demo user from database
                demo_user_id = "075ce2423576c5d4a0d8f883aa4ebf7e"
                user_doc = db.get_document(demo_user_id)

                # Check if it's a valid user document
                if not user_doc or user_doc.get("type") != "user_profile":
                    logger.warning(f"Demo user not found with ID: {demo_user_id}")
                    # Try to find demo user by username as fallback
                    user_doc = db.get_user_by_username("demo_user")

                if not user_doc:
                    logger.error("Demo user not found in database!")
                    return (
                        {},  # user_state
                        *state["update_nav_visibility"](None),  # nav buttons
                        "login",  # current_page - redirect to login with error
                        *state["update_visibility"]("login")[7:],  # button variants
                    )

                # Return user object for state management
                user = {
                    "id": user_doc["_id"],
                    "username": user_doc["username"],
                    "email": user_doc["email"],
                }
                logger.info(f"Demo login successful, returning user state: {user}")

                # Sync Hevy data for demo user (full sync to get all historical workouts)
                threading.Thread(
                    target=sync_hevy_data, args=(user, "full"), daemon=True
                ).start()

                # Update navigation and redirect to dashboard
                nav_updates = state["update_nav_visibility"](user)
                return (
                    user,  # user_state
                    *nav_updates,  # nav buttons
                    "dashboard",  # current_page
                    *state["update_visibility"]("dashboard")[7:],  # button variants
                )

            except Exception as e:
                logger.error(f"Demo login failed: {str(e)}", exc_info=True)
                return (
                    {},  # user_state
                    *state["update_nav_visibility"](None),  # nav buttons
                    "login",  # current_page
                    *state["update_visibility"]("login")[7:],  # button variants
                )

        def handle_logout(user_state):
            """Handle user logout."""
            return (
                {},  # Clear user state
                *state["update_nav_visibility"](None),  # Update nav visibility
                "login",  # Redirect to login
                *state["update_visibility"]("login")[7:],  # Update button variants
            )

        def update_visibility_and_load(page=None, user_state=None):
            logger.info(f"Updating visibility and loading data for page: {page}")
            if page is None:
                logger.info("No page specified, defaulting to login")
                return user_state, *state["update_visibility"](
                    "login"
                )  # Default to login page

            logger.info("Updating visibility")
            updates = state["update_visibility"](page)

            # current_user_state = user_state
            logger.info(f"Prev user state dict id: {id(user_state)}")

            import datetime

            new_user_state = dict(user_state) if user_state else {}
            new_user_state["_profile_updated"] = datetime.datetime.now().isoformat()

            logger.info(f"New user state dict id: {id(new_user_state)}")

            return new_user_state, *updates

        # Set initial visibility when app loads
        gr.on(
            fn=lambda: state["update_nav_visibility"](None),
            inputs=[],
            outputs=[
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
                logout_nav_button,
            ],
        )

        # Connect navigation buttons
        register_nav_button.click(
            fn=lambda user_state: update_visibility_and_load("register", user_state),
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )
        login_nav_button.click(
            fn=lambda user_state: update_visibility_and_load("login", user_state),
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )
        landing_nav_button.click(
            fn=lambda user_state: update_visibility_and_load("landing", user_state),
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )
        dashboard_nav_button.click(
            fn=lambda user_state: update_visibility_and_load("dashboard", user_state),
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )
        ai_recs_nav_button.click(
            fn=lambda user_state: update_visibility_and_load("ai_recs", user_state),
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )
        profile_nav_button.click(
            fn=lambda user_state: update_visibility_and_load("profile", user_state),
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )
        logout_nav_button.click(
            fn=handle_logout,
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
                logout_nav_button,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        ).then(
            fn=lambda user_state, page: update_visibility_and_load(page, user_state),
            inputs=[state["user_state"], state["current_page"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )

        # Connect login and register handlers
        login_button.click(
            fn=handle_login,
            inputs=[login_username, login_password, state["user_state"]],
            outputs=[
                state["user_state"],
                login_error,  # error_message
                login_username,  # username field
                login_password,  # password field
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
                logout_nav_button,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        ).then(
            fn=lambda user_state, page: update_visibility_and_load(page, user_state),
            inputs=[state["user_state"], state["current_page"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )

        # Connect demo account button
        demo_btn.click(
            fn=handle_demo_login,
            inputs=[state["user_state"]],
            outputs=[
                state["user_state"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
                logout_nav_button,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        ).then(
            fn=lambda user_state, page: update_visibility_and_load(page, user_state),
            inputs=[state["user_state"], state["current_page"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )

        # Update profile when user state changes
        state["user_state"].change(
            fn=update_profile,
            inputs=[state["user_state"]],
            outputs=[
                profile_username,
                email,
                age,
                sex,
                height_feet,
                height_inches,
                weight_lbs,
                experience,
                preferred_units,
                goals,
                workout_days,
                workout_duration,
                hevy_status,
                injuries_list,
            ],
        )

        # Update dashboard when user state changes
        state["user_state"].change(
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

        # Update AI RECs when user state changes
        state["user_state"].change(
            fn=update_ai_recs,
            inputs=[state["user_state"]],
            outputs=[
                profile_summary,
                workout_summary,
                exercises_summary,
                routine_display,
                save_status,
            ],
        )

        # Listen for changes to the current page and update visibility
        state["current_page"].change(
            fn=lambda page, user_state: update_visibility_and_load(page, user_state),
            inputs=[state["current_page"], state["user_state"]],
            outputs=[
                state["user_state"],
                register_block,
                login_block,
                landing_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_nav_button,
                login_nav_button,
                landing_nav_button,
                dashboard_nav_button,
                ai_recs_nav_button,
                profile_nav_button,
            ],
        )
