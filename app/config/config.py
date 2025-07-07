import logging
import os

from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables based on ENV setting
env = os.getenv("ENV", "development")
env_file = (
    ".env.production"
    if env == "production"
    else (
        ".env.staging" if env == "staging" else ".env.local"
    )  # Default to local development
)

logger.info(f"Environment: {env}")
logger.info("Attempting to load environment files...")

if os.path.exists(env_file):
    logger.info(f"Loading environment from {env_file}")
    load_dotenv(dotenv_path=env_file)
else:
    logger.info(f"Environment file {env_file} not found")
    # Fallback to .env if specific file doesn't exist
    if os.path.exists(".env"):
        logger.info("Falling back to .env")
        load_dotenv(dotenv_path=".env")
    else:
        logger.warning("No environment file found!")

if os.getenv("ENV") == "production" and not os.getenv("COUCHDB_URL"):
    raise EnvironmentError("Missing COUCHDB_URL for production environment")

# CouchDB Configuration
COUCHDB_URL = os.getenv("COUCHDB_URL", "http://localhost:5984")
COUCHDB_USER = os.getenv("COUCHDB_USER", "admin")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD", "admin")
COUCHDB_DB = os.getenv("COUCHDB_DB", "ai_trainer")

# Log the values being set
logger.info("Environment variables loaded:")
logger.info(f"ENV: {os.getenv('ENV')}")
logger.info(f"COUCHDB_URL: {COUCHDB_URL}")
logger.info(f"COUCHDB_USER: {COUCHDB_USER}")
logger.info(
    f"COUCHDB_PASSWORD: {'*' * len(COUCHDB_PASSWORD) if COUCHDB_PASSWORD else None}"
)
logger.info(f"COUCHDB_DB: {COUCHDB_DB}")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Hevy API Configuration (for development/demo use only)
HEVY_API_KEY = os.getenv(
    "HEVY_API_KEY"
)  # Used as fallback for users without their own API key
