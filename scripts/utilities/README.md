# Utility Scripts

This folder contains development and maintenance utility scripts for the Formava AI Trainer project.

## Scripts

### Data Seeding & Verification

- **`verify_seeding.py`** - Verifies that the workout seeding script successfully created data in the database
- **`fetch_hevy_exercise_ids.py`** - Fetches real exercise template IDs from the Hevy API to use in seeding scripts
- **`update_seeding_with_real_ids.py`** - Updates the seeding script with realistic Hevy exercise template IDs

### Development Utilities

- **`get_real_exercise_ids.py`** - Attempts to fetch exercise IDs from the local database (requires local CouchDB)

## Usage

Most scripts should be run from the project root with the appropriate environment:

```bash
# For staging environment
ENV=staging python scripts/utilities/script_name.py

# For local development
python scripts/utilities/script_name.py
```

## Output Files

These scripts may generate temporary output files (`.json`, `.csv`, `.txt`) that are ignored by git. These files are useful for debugging but should not be committed to version control.

## Environment Requirements

- Scripts that interact with Hevy API require `HEVY_API_KEY` in your environment file
- Scripts that interact with the database require proper database configuration
- Some scripts require specific environment variables to be set (staging vs development)

## Note

These are development utilities and should not be used in production environments. They are designed for:
- Setting up test data
- Debugging issues
- Validating configurations
- Development workflow automation 