#!/bin/bash
# Script to seed recent workout history for demo and test users
set -e

echo "🏋️ Recent Workout History Seeder"
echo "================================="

# Set Python path and change to project root
export PYTHONPATH=/formava_ai_trainer
cd /formava_ai_trainer

# Default to seeding both users
USER_TYPE=${1:-both}
DAYS=${2:-30}

echo "🎯 Seeding $DAYS days of recent workouts for: $USER_TYPE"
echo ""

# Run the seeding script
python app/scripts/seed_demo_recent_workouts.py --user "$USER_TYPE" --days "$DAYS"

echo ""
echo "✅ Recent workout seeding complete!"
