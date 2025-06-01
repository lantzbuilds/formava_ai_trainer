"""
Route configuration for the AI Personal Trainer application.
"""

import logging

import gradio as gr

from app.config.database import Database
from app.models.user import UserProfile
from app.pages.ai_recs import ai_recs_view
from app.pages.dashboard import dashboard_view
from app.pages.login import login_view
from app.pages.profile import profile_view
from app.pages.register import register_view

logger = logging.getLogger(__name__)
db = Database()


def setup_routes(app, state):
    """Setup application routes and navigation."""
    with app:
        # Navigation Bar
        with gr.Row(elem_classes="nav-bar"):
            with gr.Column(scale=1, min_width=120):
                register_btn = gr.Button(
                    "Register", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                login_btn = gr.Button(
                    "Login", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                dashboard_btn = gr.Button(
                    "Dashboard", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                ai_recs_btn = gr.Button(
                    "AI Recs", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                profile_btn = gr.Button(
                    "Profile", variant="primary", elem_classes="nav-button"
                )
            with gr.Column(scale=1, min_width=120):
                logout_btn = gr.Button(
                    "Logout", variant="secondary", elem_classes="nav-button"
                )

        # Main Content Area
        with gr.Column(elem_classes="page-container"):
            with gr.Group(visible=False) as register_block:
                register_components = register_view()
                register_button = register_components[0]
                register_error = register_components[1]
            with gr.Group(visible=False) as login_block:
                login_components = login_view()
                login_button = login_components[0]
                login_error = login_components[1]
                username = login_components[2]
                password = login_components[3]
            with gr.Group(visible=False) as dashboard_block:
                dashboard_components = dashboard_view()
                welcome_message = dashboard_components[0]
                total_workouts = dashboard_components[1]
                avg_workouts = dashboard_components[2]
                last_workout = dashboard_components[3]
                workout_streak = dashboard_components[4]
                goals_section = dashboard_components[5]
                injuries_section = dashboard_components[6]
            with gr.Group(visible=False) as ai_recs_block:
                ai_recs_view()
            with gr.Group(visible=False) as profile_block:
                profile_components = profile_view(state)
                profile_username = profile_components[0]
                profile_email = profile_components[1]
                profile_age = profile_components[2]
                profile_sex = profile_components[3]
                profile_height_feet = profile_components[4]
                profile_height_inches = profile_components[5]
                profile_weight = profile_components[6]
                profile_experience = profile_components[7]
                profile_goals = profile_components[8]
                profile_workout_days = profile_components[9]
                profile_workout_duration = profile_components[10]
                profile_hevy_status = profile_components[11]
                profile_injuries = profile_components[12]
                profile_error = profile_components[13]

        def handle_login(username, password):
            """Handle login attempt."""
            try:
                logger.info(f"Attempting login for username: {username}")
                # Get user from database
                user_doc = db.get_user_by_username(username)
                if not user_doc:
                    logger.warning(f"User not found: {username}")
                    return (
                        None,  # user_state
                        *state["update_nav_visibility"](None),  # nav buttons
                        "login",  # current_page
                        *state["update_visibility"]("login")[6:],  # button variants
                    )

                # Create UserProfile instance from document
                user_profile = UserProfile.from_dict(user_doc)

                # Verify password using the UserProfile instance
                if not user_profile.verify_password(password):
                    logger.warning(f"Invalid password for user: {username}")
                    return (
                        None,  # user_state
                        *state["update_nav_visibility"](None),  # nav buttons
                        "login",  # current_page
                        *state["update_visibility"]("login")[6:],  # button variants
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

                # Update navigation and redirect to dashboard
                nav_updates = state["update_nav_visibility"](user)
                logger.info(f"Updating navigation with user state: {user}")
                return (
                    user,  # user_state
                    *nav_updates,  # nav buttons
                    "dashboard",  # current_page
                    *state["update_visibility"]("dashboard")[6:],  # button variants
                )

            except Exception as e:
                logger.error(f"Login failed: {str(e)}", exc_info=True)
                return (
                    None,  # user_state
                    *state["update_nav_visibility"](None),  # nav buttons
                    "login",  # current_page
                    *state["update_visibility"]("login")[6:],  # button variants
                )

        def handle_register(user, error_msg):
            """Handle successful registration."""
            if user is None:
                return (
                    None,
                    *state["update_nav_visibility"](None),
                    "register",
                    *state["update_visibility"]("register")[6:],
                )
            return (
                user,  # Update user state
                *state["update_nav_visibility"](user),  # Update nav visibility
                "dashboard",  # Redirect to dashboard
                *state["update_visibility"]("dashboard")[6:],  # Update button variants
            )

        def handle_logout():
            """Handle user logout."""
            return (
                None,  # Clear user state
                *state["update_nav_visibility"](None),  # Update nav visibility
                "login",  # Redirect to login
                *state["update_visibility"]("login")[6:],  # Update button variants
            )

        # Connect navigation buttons
        register_btn.click(
            fn=lambda: state["update_visibility"]("register"),
            inputs=[],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )
        login_btn.click(
            fn=lambda: state["update_visibility"]("login"),
            inputs=[],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )
        dashboard_btn.click(
            fn=lambda: state["update_visibility"]("dashboard"),
            inputs=[],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )
        ai_recs_btn.click(
            fn=lambda: state["update_visibility"]("ai_recs"),
            inputs=[],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )
        profile_btn.click(
            fn=lambda: state["update_visibility"]("profile"),
            inputs=[],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )
        logout_btn.click(
            fn=handle_logout,
            inputs=[],
            outputs=[
                state["user_state"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
                logout_btn,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        ).then(
            fn=state["update_visibility"],
            inputs=[state["current_page"]],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )

        # Connect login and register handlers
        login_button.click(
            fn=handle_login,
            inputs=[username, password],
            outputs=[
                state["user_state"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
                logout_btn,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        ).then(
            fn=lambda x: logger.info(f"Main app user state updated: {x}"),
            inputs=[state["user_state"]],
            outputs=[],
        ).then(
            fn=state["update_visibility"],
            inputs=[state["current_page"]],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )

        register_button.click(
            fn=handle_register,
            inputs=[register_button, register_error],
            outputs=[
                state["user_state"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
                logout_btn,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        ).then(
            fn=state["update_visibility"],
            inputs=[state["current_page"]],
            outputs=[
                register_block,
                login_block,
                dashboard_block,
                ai_recs_block,
                profile_block,
                state["current_page"],
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
            ],
        )

        # Update dashboard when user state changes
        state["user_state"].change(
            fn=lambda x: dashboard_components[7](x),
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

        # Update profile when user state changes
        state["user_state"].change(
            fn=profile_components[14],  # load_profile function
            inputs=[state["user_state"]],
            outputs=[
                profile_username,
                profile_email,
                profile_age,
                profile_sex,
                profile_height_feet,
                profile_height_inches,
                profile_weight,
                profile_experience,
                profile_goals,
                profile_workout_days,
                profile_workout_duration,
                profile_hevy_status,
                profile_injuries,
                profile_error,
            ],
        )

        # Initial nav visibility update
        app.load(
            fn=lambda: state["update_nav_visibility"](None),
            inputs=[],
            outputs=[
                register_btn,
                login_btn,
                dashboard_btn,
                ai_recs_btn,
                profile_btn,
                logout_btn,
            ],
        )
