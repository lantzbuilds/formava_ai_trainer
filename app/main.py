"""
Main application entry point for the AI Personal Trainer.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import gradio as gr
from dotenv import load_dotenv

from app.config.database import Database
from app.models.user import FitnessGoal, Injury, InjurySeverity, Sex, UserProfile
from app.pages.ai_recs import ai_recs_view
from app.pages.dashboard import dashboard_view
from app.pages.login import login_view
from app.pages.profile import profile_view
from app.pages.register import register_view
from app.routes import setup_routes
from app.services.hevy_api import HevyAPI
from app.services.openai_service import OpenAIService
from app.state import setup_state
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

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
            theme=setup_theme(),
            css="app/static/css/style.css",
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


def main():
    """Main entry point for the application."""
    try:
        demo = create_app()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=True,
            debug=True,
            favicon_path="app/static/images/favicon.ico",
        )
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
