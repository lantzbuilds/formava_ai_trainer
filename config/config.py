import os

from dotenv import load_dotenv

# Load .env by default, or .env.production if ENV=production
env_file = ".env.production" if os.getenv("ENV") == "production" else ".env"
load_dotenv(dotenv_path=env_file)

if os.getenv("ENV") == "production" and not os.getenv("COUCHDB_URL"):
    raise EnvironmentError("Missing COUCHDB_URL for production environment")

# CouchDB Configuration
COUCHDB_URL = os.getenv("COUCHDB_URL", "http://localhost:5984")
COUCHDB_USER = os.getenv("COUCHDB_USER", "admin")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD", "admin")
COUCHDB_DB = os.getenv("COUCHDB_DB", "ai_trainer")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Hevy API Configuration (for development/demo use only)
HEVY_API_KEY = os.getenv(
    "HEVY_API_KEY"
)  # Used as fallback for users without their own API key
