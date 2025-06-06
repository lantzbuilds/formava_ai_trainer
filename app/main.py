"""
Main application entry point for the AI Personal Trainer.
"""

# Configure logging
import logging
import os
from datetime import datetime, timedelta, timezone

import gradio as gr
from dotenv import load_dotenv

from app.config.database import Database
from app.config.state import setup_state
from app.models.user import FitnessGoal, Injury, InjurySeverity, Sex, UserProfile
from app.pages.ai_recs import ai_recs_view
from app.pages.dashboard import dashboard_view
from app.pages.login import login_view
from app.pages.profile import profile_view
from app.pages.register import register_view
from app.routes import setup_routes
from app.services.hevy_api import HevyAPI
from app.services.openai_service import OpenAIService
from app.theme import setup_theme
from app.utils.crypto import decrypt_api_key, encrypt_api_key
from app.utils.units import (
    cm_to_inches,
    format_height_cm,
    format_weight_kg,
    inches_to_cm,
    kg_to_lbs,
    lbs_to_kg,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
console_handler.setFormatter(console_formatter)

# File handler
file_handler = logging.FileHandler("app.log", mode="a")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
file_handler.setFormatter(file_formatter)

# Add handlers (avoid duplicates)
if not logger.hasHandlers():
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
else:
    # Prevent adding multiple handlers if this code runs more than once
    handler_types = [type(h) for h in logger.handlers]
    if logging.StreamHandler not in handler_types:
        logger.addHandler(console_handler)
    if logging.FileHandler not in handler_types:
        logger.addHandler(file_handler)

favicon_path = os.path.abspath("app/static/images/favicon.ico")

# Load environment variables
load_dotenv()

port = int(os.getenv("PORT", 7860))

# Initialize database connection - only do this once
if gr.NO_RELOAD:
    db = Database()
    logger.info("Database initialized successfully")

    # Bootstrap vectorstore if in production
    if os.getenv("ENV") == "production":
        logger.info("Bootstrapping vectorstore for production environment")
        from app.scripts.bootstrap_vectorstore import bootstrap_vectorstore

        bootstrap_vectorstore()


def create_app():
    """Create and configure the Gradio application."""
    try:
        # Create Gradio app
        demo = gr.Blocks(
            title="Formava AI Fitness",
            theme="soft",
            css_paths=["app/static/css/style.css"],
        )

        # Setup application state
        state = setup_state(demo)
        logger.info("Application state initialized")

        # Setup routes and navigation
        setup_routes(demo, state)
        logger.info("Routes and navigation configured")

        return demo

    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise


demo = create_app()


def main():
    """Main entry point for the application."""
    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=True,
            debug=True,
            favicon_path=favicon_path,
        )
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
