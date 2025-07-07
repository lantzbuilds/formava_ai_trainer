#!/usr/bin/env python3
"""
Debug script to test environment loading for staging.
"""

import os
import sys

from dotenv import load_dotenv

# Set environment to staging if not already set
if not os.getenv("ENV"):
    os.environ["ENV"] = "staging"
    print("🔧 Environment set to 'staging'")

print(f"Current ENV value: {os.getenv('ENV')}")
print(f"Current working directory: {os.getcwd()}")

# Check which .env files exist
env_files_to_check = [".env.local", ".env.staging", ".env.production", ".env"]
print("\n📁 Checking for environment files:")
for file in env_files_to_check:
    exists = os.path.exists(file)
    print(f"  {file}: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")

# Test the NEW SIMPLIFIED loading logic from config.py
print("\n🔄 Testing NEW SIMPLIFIED environment loading logic:")

# Load environment variables based on ENV setting (matches config.py exactly)
env = os.getenv("ENV", "development")
env_file = (
    ".env.production"
    if env == "production"
    else (
        ".env.staging" if env == "staging" else ".env.local"
    )  # Default to local development
)

print(f"Environment: {env}")
print(f"Single file to load: {env_file}")

if os.path.exists(env_file):
    print(f"✅ Loading environment from {env_file}")
    load_dotenv(dotenv_path=env_file)
else:
    print(f"❌ Environment file {env_file} not found")
    # Fallback to .env if specific file doesn't exist
    if os.path.exists(".env"):
        print("✅ Falling back to .env")
        load_dotenv(dotenv_path=".env")
    else:
        print("❌ No environment file found!")

print("✅ No overrides - single file loading only!")

# Check final values
print("\n🎯 Final environment values:")
print(f"ENV: {os.getenv('ENV')}")
print(f"COUCHDB_URL: {os.getenv('COUCHDB_URL')}")
print(f"COUCHDB_USER: {os.getenv('COUCHDB_USER')}")
print(
    f"COUCHDB_PASSWORD: {'*' * len(os.getenv('COUCHDB_PASSWORD', '')) if os.getenv('COUCHDB_PASSWORD') else 'NOT SET'}"
)
print(f"COUCHDB_DB: {os.getenv('COUCHDB_DB')}")

# Now test importing the config module
print("\n🔄 Testing config module import:")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.config.config import (
        COUCHDB_DB,
        COUCHDB_PASSWORD,
        COUCHDB_URL,
        COUCHDB_USER,
    )

    print(f"✅ Config module imported successfully")
    print(f"COUCHDB_DB from config: {COUCHDB_DB}")
    print(f"COUCHDB_URL from config: {COUCHDB_URL}")
    print(f"COUCHDB_USER from config: {COUCHDB_USER}")
    print(
        f"COUCHDB_PASSWORD from config: {'*' * len(COUCHDB_PASSWORD) if COUCHDB_PASSWORD else 'NOT SET'}"
    )
except Exception as e:
    print(f"❌ Error importing config: {e}")
