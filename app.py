"""
Main application file for the AI Personal Trainer.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import gradio as gr
import pandas as pd
from dotenv import load_dotenv

from bootstrap_vectorstore import bootstrap_vectorstore
from config.database import Database
from models.user import FitnessGoal, Injury, InjurySeverity, Sex, UserProfile
from pages.ai_recs import ai_recs_view
from pages.dashboard import dashboard_view
from pages.login import login_view
from pages.profile import profile_view
from pages.register import register_view
from services.hevy_api import HevyAPI
from services.openai_service import OpenAIService
from utils.crypto import decrypt_api_key, encrypt_api_key
from utils.units import (
    cm_to_inches,
    format_height_cm,
    format_weight_kg,
    inches_to_cm,
    kg_to_lbs,
    lbs_to_kg,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize database connection
db = Database()

# Bootstrap vectorstore if in production
if os.getenv("ENV") == "production":
    logger.info("Bootstrapping vectorstore for production environment")
    bootstrap_vectorstore()


def app():
    # Custom CSS for better styling and responsiveness
    custom_css = """
    /* Base styles */
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    /* Navigation styles */
    .nav-bar {
        background-color: #f0f0f0;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .nav-button {
        flex: 1;
        min-width: 120px;
        margin: 0.25rem;
        white-space: nowrap;
        text-align: center;
    }
    
    /* Page container styles */
    .page-container {
        padding: 1rem;
        border-radius: 8px;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Form styles */
    .form-group {
        margin-bottom: 1rem;
        width: 100%;
    }
    
    .form-input {
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Responsive grid */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1rem;
        width: 100%;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .container {
            padding: 0.5rem;
        }
        
        .nav-bar {
            padding: 0.5rem;
        }
        
        .nav-button {
            min-width: 100px;
            font-size: 0.9rem;
            padding: 0.5rem;
        }
        
        .page-container {
            padding: 0.75rem;
        }
        
        .grid-container {
            grid-template-columns: 1fr;
        }
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .nav-bar {
            background-color: #2d2d2d;
        }
        
        .page-container {
            background-color: #1e1e1e;
            color: #ffffff;
        }
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as app:
        current_page = gr.State("login")
        user_state = gr.State(None)  # Store user session data

        def update_visibility(page):
            return (
                gr.update(visible=page == "register"),
                gr.update(visible=page == "login"),
                gr.update(visible=page == "dashboard"),
                gr.update(visible=page == "ai_recs"),
                gr.update(visible=page == "profile"),
                page,
            )

        def update_nav_visibility(user):
            """Update navigation visibility based on user state."""
            if user is None:
                # Not logged in - show only register and login
                return (
                    gr.update(visible=True),  # register
                    gr.update(visible=True),  # login
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
                    gr.update(visible=True),  # dashboard
                    gr.update(visible=True),  # ai_recs
                    gr.update(visible=True),  # profile
                    gr.update(visible=True),  # logout
                )

        def handle_login(user, error_msg):
            """Handle successful login."""
            if user is None:
                return None, *update_nav_visibility(None), "login"
            return (
                user,  # Update user state
                *update_nav_visibility(user),  # Update nav visibility
                "dashboard",  # Redirect to dashboard
            )

        def handle_register(user, error_msg):
            """Handle successful registration."""
            if user is None:
                return None, *update_nav_visibility(None), "register"
            return (
                user,  # Update user state
                *update_nav_visibility(user),  # Update nav visibility
                "dashboard",  # Redirect to dashboard
            )

        def handle_logout():
            """Handle user logout."""
            return (
                None,  # Clear user state
                *update_nav_visibility(None),  # Update nav visibility
                "login",  # Redirect to login
            )

        # Main container for better responsiveness
        with gr.Column(elem_classes="container"):
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
                    register_button, register_error = register_view()
                with gr.Group(visible=False) as login_block:
                    login_button, login_error = login_view()
                with gr.Group(visible=False) as dashboard_block:
                    dashboard_view()
                with gr.Group(visible=False) as ai_recs_block:
                    ai_recs_view()
                with gr.Group(visible=False) as profile_block:
                    profile_view()

            # Connect navigation buttons
            register_btn.click(
                fn=lambda: update_visibility("register"),
                inputs=[],
                outputs=[
                    register_block,
                    login_block,
                    dashboard_block,
                    ai_recs_block,
                    profile_block,
                    current_page,
                ],
            )
            login_btn.click(
                fn=lambda: update_visibility("login"),
                inputs=[],
                outputs=[
                    register_block,
                    login_block,
                    dashboard_block,
                    ai_recs_block,
                    profile_block,
                    current_page,
                ],
            )
            dashboard_btn.click(
                fn=lambda: update_visibility("dashboard"),
                inputs=[],
                outputs=[
                    register_block,
                    login_block,
                    dashboard_block,
                    ai_recs_block,
                    profile_block,
                    current_page,
                ],
            )
            ai_recs_btn.click(
                fn=lambda: update_visibility("ai_recs"),
                inputs=[],
                outputs=[
                    register_block,
                    login_block,
                    dashboard_block,
                    ai_recs_block,
                    profile_block,
                    current_page,
                ],
            )
            profile_btn.click(
                fn=lambda: update_visibility("profile"),
                inputs=[],
                outputs=[
                    register_block,
                    login_block,
                    dashboard_block,
                    ai_recs_block,
                    profile_block,
                    current_page,
                ],
            )
            logout_btn.click(
                fn=handle_logout,
                inputs=[],
                outputs=[
                    user_state,
                    register_btn,
                    login_btn,
                    dashboard_btn,
                    ai_recs_btn,
                    profile_btn,
                    logout_btn,
                    current_page,
                ],
            )

            # Connect login and register handlers
            login_button.click(
                fn=handle_login,
                inputs=[login_button, login_error],
                outputs=[
                    user_state,
                    register_btn,
                    login_btn,
                    dashboard_btn,
                    ai_recs_btn,
                    profile_btn,
                    logout_btn,
                    current_page,
                ],
            )
            register_button.click(
                fn=handle_register,
                inputs=[register_button, register_error],
                outputs=[
                    user_state,
                    register_btn,
                    login_btn,
                    dashboard_btn,
                    ai_recs_btn,
                    profile_btn,
                    logout_btn,
                    current_page,
                ],
            )

            # Initial nav visibility update
            app.load(
                fn=lambda: update_nav_visibility(None),
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

    app.launch(
        server_name="0.0.0.0",
        server_port=8080,
        share=True,
        show_error=True,
        show_api=False,
    )


if __name__ == "__main__":
    app()
