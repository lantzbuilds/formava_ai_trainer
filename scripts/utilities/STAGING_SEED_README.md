# Staging Database Seeding Script

This script seeds the staging database with realistic workout history for testing the AI workout recommendation system.

## What it does

The script will:
1. Create a test user account with realistic fitness profile
2. Generate 30 days of workout history with progressive overload
3. Create realistic exercise data with proper weight progression
4. Include various workout types (upper/lower body split)
5. Add exercises with realistic sets, reps, and weights

## Test User Details

- **Username**: `test_user_staging`
- **Password**: `test_password_123`
- **Email**: `test@staging.formava.com`
- **Profile**: 28-year-old male, intermediate level, strength/muscle gain goals

## Usage

### Option 1: Using the simple runner (recommended)
```bash
python seed_staging_data.py
```

### Option 2: Direct execution
```bash
python app/scripts/seed_workout_history.py
```

## Environment Requirements

The script automatically connects to your staging CouchDB instance using the environment variables:
- `COUCHDB_URL` - Your Render CouchDB internal URL
- `COUCHDB_USER` - CouchDB username
- `COUCHDB_PASSWORD` - CouchDB password
- `COUCHDB_DB` - Database name (usually `ai_trainer`)

## Generated Data

The script creates approximately 20-25 workouts over 30 days with:
- **Upper Body Workouts**: Bench Press, Barbell Row, Overhead Press, Lat Pulldown, Bicep Curl, Tricep Dips
- **Lower Body Workouts**: Squat, Deadlift, Leg Press, Leg Curl, Leg Extension, Plank
- **Progressive Overload**: Weights increase by 1.25-2.5kg per week
- **Realistic Variation**: RPE ratings, rep ranges, occasional cardio
- **Rest Days**: Simulates realistic workout schedule with rest days

## Exercise Templates

The script includes 18 common exercises with proper:
- Muscle group targeting
- Equipment requirements
- Weight progressions
- Rep ranges

## Logging

The script provides detailed logging to track:
- Database connection status
- User creation/lookup
- Exercise template creation
- Workout generation progress
- Any errors encountered

## Troubleshooting

If you encounter issues:

1. **Database Connection**: Ensure your CouchDB service is running and environment variables are set
2. **Permissions**: Make sure the script has write access to the database
3. **Dependencies**: Ensure all required Python packages are installed
4. **Existing Data**: The script will skip creating a user if one already exists

## Clean Up

To remove the test data:
1. Delete the user document with ID starting with `test_user_staging`
2. Delete workout documents with `user_id` matching the test user
3. Delete exercise templates if needed (they have IDs ending in `_001`)

## Notes

- The script is designed to be run multiple times safely
- It will reuse existing test user if found
- Exercise templates are only created once
- Workout history is additive (won't duplicate existing workouts)
- All dates and times are in UTC timezone 