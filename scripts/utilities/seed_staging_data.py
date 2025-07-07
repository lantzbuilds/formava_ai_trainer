#!/usr/bin/env python3
"""
Simple runner script to seed staging database with workout history.
Run this from the project root directory.
"""

import os
import sys

# Set environment to staging if not already set
if not os.getenv("ENV"):
    os.environ["ENV"] = "staging"
    print("🔧 Environment set to 'staging'")

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the seeding script
from app.scripts.seed_workout_history import main

if __name__ == "__main__":
    print("🏋️  Seeding staging database with workout history...")
    print("=" * 50)
    print(f"Environment: {os.getenv('ENV', 'unknown')}")
    print("=" * 50)
    main()
    print("=" * 50)
    print("✅ Seeding complete!")
