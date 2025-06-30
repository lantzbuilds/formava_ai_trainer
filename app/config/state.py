"""
State management for the AI Personal Trainer application.
"""

import logging

import gradio as gr

logger = logging.getLogger(__name__)


def setup_state(app):
    """Setup application state management."""
    with app:
        # Global state
        current_page = gr.State("landing")
        user_state = gr.State({})  # Store user session data

        def update_visibility(page):
            """Update visibility of blocks and navigation button states."""
            return (
                gr.update(visible=page == "register"),
                gr.update(visible=page == "login"),
                gr.update(visible=page == "landing"),
                gr.update(visible=page == "dashboard"),
                gr.update(visible=page == "ai_recs"),
                gr.update(visible=page == "profile"),
                page,
                # Update button variants to show active state
                gr.update(variant="primary" if page == "register" else "secondary"),
                gr.update(variant="primary" if page == "login" else "secondary"),
                gr.update(variant="primary" if page == "landing" else "secondary"),
                gr.update(variant="primary" if page == "dashboard" else "secondary"),
                gr.update(variant="primary" if page == "ai_recs" else "secondary"),
                gr.update(variant="primary" if page == "profile" else "secondary"),
            )

        def update_nav_visibility(user):
            """Update navigation visibility based on user state."""
            if user is None:
                # Not logged in - show only register and login
                return (
                    gr.update(visible=True),  # register
                    gr.update(visible=True),  # login
                    gr.update(visible=True),  # landing
                    gr.update(visible=False),  # dashboard
                    gr.update(visible=False),  # ai_recs
                    gr.update(visible=False),  # profile
                    gr.update(visible=False),  # logout
                )
            else:
                # Logged in - show all except register and login
                return (
                    gr.update(visible=False),  # register
                    gr.update(visible=False),  # login
                    gr.update(visible=True),  # landing
                    gr.update(visible=True),  # dashboard
                    gr.update(visible=True),  # ai_recs
                    gr.update(visible=True),  # profile
                    gr.update(visible=True),  # logout
                )

    return {
        "current_page": current_page,
        "user_state": user_state,
        "update_visibility": update_visibility,
        "update_nav_visibility": update_nav_visibility,
    }
