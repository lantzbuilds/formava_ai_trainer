# Workout API Structure and hevy_id Explanation

## ID Strategy: Primary vs Secondary IDs

### **Primary ID (`id`)**
- **Database-generated**: CouchDB automatically generates unique `_id` 
- **API Response**: Returned as `id` field in API responses
- **Best Practice**: Let the database handle primary key generation ✅

### **Secondary ID (`hevy_id`)**
The `hevy_id` field serves as an **external reference identifier** for sync purposes:

1. **Real Hevy Workouts**: Contains the actual workout ID from Hevy API (e.g., `"hevy_12345abc"`)
2. **Generated/Seed Workouts**: Uses fake ID for duplicate prevention (e.g., `"seed_a1b2c3d4e5f6"`)

## UUID Usage in Seeding Script

The seeding script generates fake `hevy_id` values for **duplicate prevention only**:

```python
"hevy_id": f"seed_{uuid.uuid4().hex[:12]}"  # For duplicate prevention only
```

**Important**: This is NOT the primary ID. The database generates the primary `_id` automatically.

- **Prefix "seed_"**: Identifies this as a generated workout (not from real Hevy API)
- **UUID hex**: Ensures uniqueness across multiple script runs
- **12 characters**: Keeps it reasonably short while maintaining uniqueness

## Sample Workout JSON for POST /v1/workouts

Here's the **request structure** that matches the Hevy API format:

```json
{
  "workout": {
    "title": "Upper Body Day 💪",
    "description": "High intensity upper workout",
    "start_time": "2024-12-15T09:00:00Z",
    "end_time": "2024-12-15T10:15:00Z",
    "is_private": false,
    "exercises": [
      {
        "exercise_template_id": "bench_press_001",
        "superset_id": null,
        "notes": "Felt strong today",
        "sets": [
          {
            "type": "normal",
            "weight_kg": 62.5,
            "reps": 8,
            "duration_seconds": null,
            "distance_meters": null,
            "custom_metric": null,
            "rpe": 7
          },
          {
            "type": "normal",
            "weight_kg": 62.5,
            "reps": 7,
            "duration_seconds": null,
            "distance_meters": null,
            "custom_metric": null,
            "rpe": 8
          }
        ]
      },
      {
        "exercise_template_id": "lat_pulldown_001",
        "superset_id": null,
        "notes": null,
        "sets": [
          {
            "type": "normal",
            "weight_kg": 47.5,
            "reps": 10,
            "duration_seconds": null,
            "distance_meters": null,
            "custom_metric": null,
            "rpe": null
          }
        ]
      }
    ]
  }
}
```

## Sample API Response

Here's what the API returns after successfully creating a workout:

```json
{
  "id": "b459cba5-cd6d-463c-abd6-54f8eafcadcb",
  "title": "Morning Workout 💪",
  "description": "Pushed myself to the limit today!",
  "start_time": "2021-09-14T12:00:00Z",
  "end_time": "2021-09-14T12:00:00Z",
  "updated_at": "2021-09-14T12:00:00Z",
  "created_at": "2021-09-14T12:00:00Z",
  "exercises": [
    {
      "index": 0,
      "title": "Bench Press (Barbell)",
      "notes": "Paid closer attention to form today. Felt great!",
      "exercise_template_id": "05293BCA",
      "supersets_id": 0,
      "sets": [
        {
          "index": 0,
          "type": "normal",
          "weight_kg": 100,
          "reps": 10,
          "distance_meters": null,
          "duration_seconds": null,
          "rpe": 9.5,
          "custom_metric": 50
        }
      ]
    }
  ]
}
```

## Key Field Explanations

### Request vs Response Structure
- **Request**: Send nested `{"workout": {...}}` structure
- **Response**: Returns flattened structure with database-generated `id`

### Core Workout Fields
- **`id`**: Database-generated primary identifier (response only)
- **`title`**: Human-readable workout name (can include emojis)
- **`description`**: Brief description of the workout
- **`start_time`/`end_time`**: ISO 8601 timestamps in UTC (ending with "Z")
- **`is_private`**: Whether the workout is private or public (request only)

### Exercise Structure
- **`exercise_template_id`**: Links to exercise definition in database
- **`superset_id`**: Groups exercises into supersets (null = no superset)
- **`notes`**: Optional notes about the exercise performance
- **`index`**: Exercise order in workout (response only)
- **`title`**: Exercise name (response only)

### Set Types and Data
- **Weight Training**: Uses `weight_kg` and `reps`
- **Duration-based**: Uses `duration_seconds` (plank, cardio)
- **Distance-based**: Uses `distance_meters` (running, cycling)
- **`custom_metric`**: For specialized tracking (null if not used)
- **RPE**: Rate of Perceived Exertion (1-10 scale, optional)
- **`index`**: Set order within exercise (response only)

## Database Storage

The workout gets stored in CouchDB with additional metadata fields:
- **`_id`**: CouchDB document ID (auto-generated)
- **`_rev`**: CouchDB revision (for updates)
- **`type`**: Always "workout" for workout documents
- **`hevy_id`**: Unique identifier (real Hevy ID or generated fake ID like "seed_a1b2c3d4e5f6")
- **`user_id`**: Links workout to specific user
- **`duration_minutes`**: Calculated workout duration
- **`exercise_count`**: Number of exercises in the workout
- **`created_at`/`updated_at`**: Timestamps for record tracking

The seeding script generates workouts in the Hevy API format, then flattens the structure for database storage by combining the `workout` object with the `_metadata` object.

## Duplicate Prevention

The `hevy_id` field is used to prevent duplicate workouts:
1. Before saving, the system checks if a workout with that `hevy_id` already exists
2. If found, it updates the existing workout instead of creating a new one
3. This works for both real Hevy syncing and our seeding script

## Why This Design?

This approach allows the system to:
- ✅ Handle real Hevy API data seamlessly
- ✅ Generate realistic test data for development
- ✅ Prevent duplicate workouts across sync operations
- ✅ Maintain data integrity between local database and Hevy API
- ✅ Support offline workout creation that can later sync to Hevy 