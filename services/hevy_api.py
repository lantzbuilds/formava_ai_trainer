import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import requests

from models.exercise import Exercise, ExerciseList
from utils.crypto import decrypt_api_key


class HevyAPI:
    """Service for interacting with the Hevy API."""

    def __init__(self, encrypted_api_key: str):
        """Initialize the Hevy API client with an encrypted API key."""
        self.api_key = decrypt_api_key(encrypted_api_key)
        if not self.api_key:
            raise ValueError("Invalid or missing Hevy API key")

        self.base_url = "https://api.hevyapp.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

    def get_workouts(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get workouts from Hevy API.

        Args:
            start_date: Start date for workout range (default: 30 days ago)
            end_date: End date for workout range (default: today)

        Returns:
            List of workout dictionaries
        """
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Format dates for API
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # Make API request
        url = f"{self.base_url}/workouts"
        params = {"start_date": start_str, "end_date": end_str}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("workouts", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workouts: {e}")
            return []

    def get_workout_count(self) -> int:
        """
        Get the total count of workouts.

        Returns:
            Total number of workouts
        """
        url = f"{self.base_url}/workouts/count"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("count", 0)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workout count: {e}")
            return 0

    def get_workout_events(
        self, since_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get workout events since a given date.

        Args:
            since_date: Date to get events since (default: 30 days ago)

        Returns:
            List of workout event dictionaries
        """
        if not since_date:
            since_date = datetime.now(timezone.utc) - timedelta(days=30)

        # Format date for API
        since_str = since_date.isoformat()

        # Make API request
        url = f"{self.base_url}/workouts/events"
        params = {"since": since_str}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("events", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workout events: {e}")
            return []

    def get_workout_details(self, workout_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific workout.

        Args:
            workout_id: ID of the workout to retrieve

        Returns:
            Workout details dictionary or None if not found
        """
        url = f"{self.base_url}/workouts/{workout_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workout details: {e}")
            return None

    def update_workout(self, workout_id: str, workout_data: Dict[str, Any]) -> bool:
        """
        Update an existing workout.

        Args:
            workout_id: ID of the workout to update
            workout_data: Updated workout data

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/workouts/{workout_id}"

        try:
            response = requests.put(url, headers=self.headers, json=workout_data)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error updating workout: {e}")
            return False

    def create_workout(self, workout_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new workout.

        Args:
            workout_data: Workout data to create

        Returns:
            ID of the created workout or None if failed
        """
        url = f"{self.base_url}/workouts"

        try:
            response = requests.post(url, headers=self.headers, json=workout_data)
            response.raise_for_status()
            return response.json().get("id")
        except requests.exceptions.RequestException as e:
            print(f"Error creating workout: {e}")
            return None

    def get_routines(self) -> List[Dict[str, Any]]:
        """
        Get all routines.

        Returns:
            List of routine dictionaries
        """
        url = f"{self.base_url}/routines"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("routines", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching routines: {e}")
            return []

    def create_routine(self, routine_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new routine.

        Args:
            routine_data: Routine data to create

        Returns:
            ID of the created routine or None if failed
        """
        url = f"{self.base_url}/routines"

        try:
            # Check if the routine has the new format with weeks
            if "weeks" in routine_data and routine_data["weeks"]:
                # Convert the new format to Hevy API format
                hevy_routine = self._convert_routine_to_hevy_format(routine_data)
            else:
                # Check if the routine is already in the correct format
                if "routine" in routine_data:
                    hevy_routine = routine_data
                else:
                    # Convert to the correct format
                    hevy_routine = {
                        "routine": {
                            "title": routine_data.get("name", "Unnamed Routine"),
                            "folder_id": None,
                            "notes": routine_data.get("description", ""),
                            "exercises": routine_data.get("exercises", []),
                        }
                    }

            # Log the request for debugging
            print(
                f"Sending routine creation request: {json.dumps(hevy_routine, indent=2)}"
            )

            response = requests.post(url, headers=self.headers, json=hevy_routine)
            response.raise_for_status()
            return response.json().get("id")
        except requests.exceptions.RequestException as e:
            print(f"Error creating routine: {e}")
            return None

    def _convert_routine_to_hevy_format(
        self, routine_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert the new routine format with weeks to Hevy API format.

        Args:
            routine_data: Routine data in the new format

        Returns:
            Routine data in Hevy API format
        """
        # Extract basic routine information
        name = routine_data.get("name", "Unnamed Routine")
        description = routine_data.get("description", "")
        difficulty = routine_data.get("difficulty", "intermediate")
        estimated_duration = routine_data.get("estimated_duration", 60)
        target_muscle_groups = routine_data.get("target_muscle_groups", [])
        equipment_needed = routine_data.get("equipment_needed", [])

        # Create a flat list of exercises from all weeks and days
        exercises = []

        # Process each week
        for week in routine_data.get("weeks", []):
            week_number = week.get("week_number", 0)
            rpe = week.get("rpe", 0)

            # Process each day in the week
            for day in week.get("days", []):
                day_number = day.get("day_number", 0)
                focus = day.get("focus", "")

                # Process each exercise in the day
                for exercise in day.get("exercises", []):
                    exercise_id = exercise.get("exercise_id", "")
                    exercise_name = exercise.get("name", "")
                    sets = exercise.get("sets", 0)
                    reps = exercise.get("reps", "")
                    rpe = exercise.get("rpe", 0)
                    notes = exercise.get("notes", "")
                    modifications = exercise.get("modifications", [])

                    # Create exercise data in Hevy API format
                    exercise_data = {
                        "exercise_template_id": exercise_id,
                        "superset_id": None,
                        "rest_seconds": 90,  # Default rest time
                        "notes": notes,
                        "sets": [],
                    }

                    # Add sets based on reps format
                    if isinstance(reps, str) and "x" in reps:
                        # Format like "10x3" (reps x sets)
                        reps_str, sets_str = reps.split("x")
                        reps_count = int(reps_str)
                        sets_count = int(sets_str)
                    else:
                        # Default values
                        reps_count = 10
                        sets_count = sets

                    # Create sets
                    for _ in range(sets_count):
                        set_data = {
                            "type": "normal",
                            "weight_kg": None,  # No weight specified
                            "reps": reps_count,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "custom_metric": None,
                        }
                        exercise_data["sets"].append(set_data)

                    exercises.append(exercise_data)

                # Process cardio if present
                if "cardio" in day and day["cardio"]:
                    cardio = day["cardio"]
                    cardio_type = cardio.get("type", "")
                    cardio_duration = cardio.get("duration", "")
                    cardio_intensity = cardio.get("intensity", "")

                    # Parse duration to seconds
                    duration_seconds = 0
                    if cardio_duration:
                        if "min" in cardio_duration.lower():
                            try:
                                minutes = int(cardio_duration.split()[0])
                                duration_seconds = minutes * 60
                            except (ValueError, IndexError):
                                duration_seconds = 600  # Default 10 minutes
                        else:
                            duration_seconds = 600  # Default 10 minutes

                    # Create cardio data in Hevy API format
                    cardio_data = {
                        "exercise_template_id": "cardio",  # Use a placeholder ID
                        "superset_id": None,
                        "rest_seconds": 0,
                        "notes": f"{cardio_type} at {cardio_intensity} intensity",
                        "sets": [
                            {
                                "type": "normal",
                                "weight_kg": None,
                                "reps": None,
                                "distance_meters": None,
                                "duration_seconds": duration_seconds,
                                "custom_metric": None,
                            }
                        ],
                    }

                    exercises.append(cardio_data)

        # Create Hevy API format
        hevy_routine = {
            "routine": {
                "title": name,
                "folder_id": None,
                "notes": description,
                "exercises": exercises,
            }
        }

        return hevy_routine

    def update_routine(self, routine_id: str, routine_data: Dict[str, Any]) -> bool:
        """
        Update an existing routine.

        Args:
            routine_id: ID of the routine to update
            routine_data: Updated routine data

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/routines/{routine_id}"

        try:
            response = requests.put(url, headers=self.headers, json=routine_data)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error updating routine: {e}")
            return False

    def get_exercises(
        self, page: int = 1, page_size: int = 100, include_custom: bool = False
    ) -> ExerciseList:
        """
        Get exercises from Hevy API.

        Args:
            page: Page number to retrieve
            page_size: Number of exercises per page
            include_custom: Whether to include custom exercises

        Returns:
            ExerciseList object containing exercises from the requested page
        """
        url = f"{self.base_url}/exercise_templates"
        params = {"page": page, "pageSize": page_size}

        if include_custom:
            params["includeCustom"] = "true"

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract exercise templates
            exercise_templates = data.get("exercise_templates", [])

            # Convert to our Exercise model format
            exercises_data = []
            for template in exercise_templates:
                # Create muscle groups
                muscle_groups = []
                if "primary_muscle_group" in template:
                    muscle_groups.append(
                        {
                            "id": template["primary_muscle_group"],
                            "name": template["primary_muscle_group"],
                            "is_primary": True,
                        }
                    )

                for muscle in template.get("secondary_muscle_groups", []):
                    muscle_groups.append(
                        {"id": muscle, "name": muscle, "is_primary": False}
                    )

                # Create equipment
                equipment = []
                if "equipment" in template and template["equipment"] != "none":
                    equipment.append(
                        {"id": template["equipment"], "name": template["equipment"]}
                    )

                # Create exercise data
                exercise_data = {
                    "id": template.get("id", ""),
                    "name": template.get("title", ""),
                    "description": "",
                    "instructions": "",
                    "muscle_groups": muscle_groups,
                    "equipment": equipment,
                    "categories": [],
                    "difficulty": "",
                    "is_custom": template.get("is_custom", False),
                    "created_at": "",
                    "updated_at": "",
                }

                exercises_data.append(exercise_data)

            updated_at = datetime.now(timezone.utc).isoformat()
            return ExerciseList.from_hevy_api(exercises_data, updated_at)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching exercises: {e}")
            return ExerciseList()

    def get_exercise_details(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific exercise.

        Args:
            exercise_id: ID of the exercise to retrieve

        Returns:
            Exercise details dictionary or None if not found
        """
        url = f"{self.base_url}/exercise_templates/{exercise_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching exercise details: {e}")
            return None

    def get_routine_folders(self) -> List[Dict[str, Any]]:
        """
        Get all routine folders.

        Returns:
            List of routine folder dictionaries
        """
        url = f"{self.base_url}/routine_folders"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("folders", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching routine folders: {e}")
            return []

    def create_routine_folder(self, folder_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new routine folder.

        Args:
            folder_data: Folder data to create

        Returns:
            ID of the created folder or None if failed
        """
        url = f"{self.base_url}/routine_folders"

        try:
            response = requests.post(url, headers=self.headers, json=folder_data)
            response.raise_for_status()
            return response.json().get("id")
        except requests.exceptions.RequestException as e:
            print(f"Error creating routine folder: {e}")
            return None

    def get_routine_folder(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific routine folder.

        Args:
            folder_id: ID of the folder to retrieve

        Returns:
            Folder details dictionary or None if not found
        """
        url = f"{self.base_url}/routine_folders/{folder_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching routine folder: {e}")
            return None

    def get_all_exercises(
        self, max_pages: int = 10, include_custom: bool = False
    ) -> ExerciseList:
        """
        Get all available exercises from Hevy API by fetching all pages.

        Args:
            max_pages: Maximum number of pages to fetch
            include_custom: Whether to include custom exercises

        Returns:
            ExerciseList object containing all exercises
        """
        all_exercises = []
        page = 1

        while page <= max_pages:
            try:
                exercise_list = self.get_exercises(
                    page=page, page_size=100, include_custom=include_custom
                )
                if not exercise_list.exercises:
                    # No more exercises found, break the loop
                    break

                all_exercises.extend(exercise_list.exercises)
                page += 1
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Page not found, we've reached the end of available pages
                    print(f"Page {page} not found, stopping pagination")
                    break
                else:
                    # Re-raise other HTTP errors
                    raise
            except Exception as e:
                # Log other exceptions and continue with what we have so far
                print(f"Error fetching page {page}: {e}")
                break

        return ExerciseList(
            exercises=all_exercises, updated_at=datetime.now(timezone.utc).isoformat()
        )

    def sync_workouts(self, db, user_id: str) -> int:
        """
        Sync workouts from Hevy to the local database.

        Args:
            db: Database instance
            user_id: User ID to associate workouts with

        Returns:
            Number of workouts synced
        """
        workouts = self.get_workouts()
        synced_count = 0

        # First, sync all available base exercises (only once)
        base_exercise_list = self.get_all_exercises(include_custom=False)
        if base_exercise_list.exercises:
            # Convert to dictionary format for database storage
            exercises_data = [
                exercise.model_dump() for exercise in base_exercise_list.exercises
            ]
            db.save_exercises(exercises_data)  # No user_id for base exercises
            print(f"Synced {len(base_exercise_list.exercises)} base exercises")

        # Then, sync user's custom exercises
        custom_exercise_list = self.get_all_exercises(include_custom=True)
        if custom_exercise_list.exercises:
            # Filter to only include custom exercises
            custom_exercises = [
                exercise
                for exercise in custom_exercise_list.exercises
                if exercise.is_custom
            ]
            if custom_exercises:
                # Convert to dictionary format for database storage
                exercises_data = [
                    exercise.model_dump() for exercise in custom_exercises
                ]
                db.save_exercises(exercises_data, user_id=user_id)
                print(
                    f"Synced {len(custom_exercises)} custom exercises for user {user_id}"
                )

        for workout in workouts:
            # Check if workout already exists
            existing = db.get_workout_by_hevy_id(workout["id"])
            if not existing:
                # Get full workout details
                details = self.get_workout_details(workout["id"])

                if details:
                    # Convert to our workout format
                    workout_data = {
                        "hevy_id": details["id"],
                        "user_id": user_id,
                        "title": details.get("title", "Untitled Workout"),
                        "description": details.get("description", ""),
                        "start_time": details.get("start_time"),
                        "end_time": details.get("end_time"),
                        "updated_at": details.get("updated_at"),
                        "created_at": details.get("created_at"),
                        "exercises": details.get("exercises", []),
                        "exercise_count": len(details.get("exercises", [])),
                        "last_synced": datetime.now(timezone.utc).isoformat(),
                    }

                    # Save to database
                    print(f"Saving workout: {workout_data['title']}")
                    try:
                        db.save_workout(workout_data, user_id=user_id)
                        synced_count += 1
                    except Exception as e:
                        print(f"Error saving workout: {str(e)}")
                        print(f"Exception type: {type(e).__name__}")
                        import traceback

                        print(f"Traceback: {traceback.format_exc()}")
            else:
                print(
                    f"Workout {workout.get('title', 'Untitled')} already exists, skipping"
                )

        return synced_count
