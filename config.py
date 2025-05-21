import os

from dotenv import load_dotenv

# Load .env by default, or .env.production if ENV=production
env_file = ".env.production" if os.getenv("ENV") == "production" else ".env"
load_dotenv(dotenv_path=env_file)

if os.getenv("ENV") == "production" and not os.getenv("COUCHDB_URL"):
    raise EnvironmentError("Missing COUCHDB_URL for production environment")

COUCHDB_URL = os.getenv("COUCHDB_URL")
COUCHDB_USER = os.getenv("COUCHDB_USER")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD")
