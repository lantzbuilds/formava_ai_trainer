import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import requests
from dotenv import load_dotenv

from app.config.database import Database
from app.models.exercise import Exercise, ExerciseList
from app.utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)


class HevyAPI:
    """Service for interacting with the Hevy API."""

    def __init__(self, api_key: str, is_encrypted: bool = True):
        """Initialize the Hevy API client with an API key.

        Args:
            api_key: The API key (either encrypted or decrypted)
            is_encrypted: Whether the API key is encrypted (default: True)
        """
        if is_encrypted:
            logger.info("Decrypting API key")
            self.api_key = decrypt_api_key(api_key)
            logger.info(f"Decrypted key format: {self.api_key[:5]}...")
            logger.info(f"Decrypted key length: {len(self.api_key)}")
        else:
            self.api_key = api_key
            logger.info(f"Using unencrypted key format: {self.api_key[:5]}...")
            logger.info(f"Unencrypted key length: {len(self.api_key)}")

        if not self.api_key:
            raise ValueError("Invalid or missing Hevy API key")

        self.base_url = "https://api.hevyapp.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        logger.info("Initialized Hevy API client with headers")
        logger.info(
            f"Request headers: {json.dumps({k: v[:5] + '...' if k == 'api-key' else v for k, v in self.headers.items()})}"
        )

    def get_workouts(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get workouts from Hevy API within a date range.

        Args:
            start_date: Start date for the range (optional)
            end_date: End date for the range (optional)

        Returns:
            List of workout dictionaries
        """
        # Initialize variables for pagination
        all_workouts = []
        current_page = 1
        page_size = 10  # Maximum allowed by API
        total_pages = None

        # Convert dates to ISO format if provided
        start_str = start_date.isoformat() if start_date else None
        end_str = end_date.isoformat() if end_date else None

        # Make API requests until we get all pages
        while total_pages is None or current_page <= total_pages:
            # Make API request
            url = f"{self.base_url}/workouts"
            params = {"page": current_page, "pageSize": page_size}

            try:
                logger.info(f"Making request to {url} with params: {params}")
                logger.info(
                    f"Using headers: {json.dumps({k: v[:5] + '...' if k == 'api-key' else v for k, v in self.headers.items()})}"
                )

                response = requests.get(url, headers=self.headers, params=params)
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")

                if response.status_code == 401:
                    logger.error("Received 401 Unauthorized response")
                    logger.error(f"Response body: {response.text}")
                    logger.error(f"Request URL: {response.request.url}")
                    logger.error(f"Request headers: {dict(response.request.headers)}")
                    raise requests.exceptions.HTTPError(
                        "401 Unauthorized: Invalid API key"
                    )

                response.raise_for_status()

                # Parse response
                response_data = response.json()
                logger.info(f"Response data keys: {list(response_data.keys())}")
                logger.info(
                    f"Total workouts in response: {len(response_data.get('workouts', []))}"
                )

                # Get total pages from response if not set
                if total_pages is None:
                    total_pages = response_data.get("page_count", 1)
                    logger.info(f"Total pages: {total_pages}")

                # Get workouts from current page
                page_workouts = response_data.get("workouts", [])

                # Filter workouts by date range if dates are provided
                if start_str and end_str:
                    filtered_workouts = [
                        workout
                        for workout in page_workouts
                        if start_str <= workout.get("start_time", "") <= end_str
                    ]
                    logger.info(
                        f"Filtered {len(filtered_workouts)} workouts by date range"
                    )
                else:
                    filtered_workouts = page_workouts

                all_workouts.extend(filtered_workouts)
                logger.info(f"Total workouts collected so far: {len(all_workouts)}")

                # Move to next page
                current_page += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching workouts: {str(e)}")
                if hasattr(e, "response") and e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response headers: {dict(e.response.headers)}")
                    logger.error(f"Response body: {e.response.text}")
                raise

        return all_workouts

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

            # Extract workout ID from the response
            response_data = response.json()
            if (
                "workout" in response_data
                and isinstance(response_data["workout"], list)
                and len(response_data["workout"]) > 0
            ):
                return response_data["workout"][0].get("id")
            else:
                logger.error("Failed to extract workout ID from response")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating workout: {str(e)}")
            if hasattr(e, "response"):
                logger.error(f"API Response Status: {e.response.status_code}")
                logger.error(f"API Response Content: {e.response.text}")
            raise  # Re-raise the exception to be handled by the caller

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
        """Create a new routine in Hevy.

        Args:
            routine_data: The routine data to create

        Returns:
            Routine ID if successful, None otherwise
        """
        try:
            # Ensure the routine data is in the correct format
            if "routine" not in routine_data:
                routine_data = {
                    "routine": {
                        "title": routine_data.get("name", "Unnamed Routine"),
                        "folder_id": routine_data.get("folder_id"),
                        "notes": routine_data.get("description", ""),
                        "exercises": routine_data.get("exercises", []),
                    }
                }

            logger.info(f"Creating routine: {routine_data['routine']['title']}")
            logger.debug(f"Request data: {json.dumps(routine_data, indent=2)}")

            # Validate all exercise template IDs before proceeding
            for exercise in routine_data["routine"]["exercises"]:
                exercise_id = exercise.get("exercise_template_id")
                if not exercise_id:
                    logger.error(
                        f"Missing exercise template ID in exercise: {exercise}"
                    )
                    return None

                # Verify the exercise template exists in Hevy
                exercise_details = self.get_exercise_details(exercise_id)
                if not exercise_details:
                    logger.error(f"Invalid exercise template ID: {exercise_id}")
                    return None
                logger.debug(f"Validated exercise template ID: {exercise_id}")

            # Format exercises for Hevy API
            formatted_exercises = []
            for exercise in routine_data["routine"]["exercises"]:
                formatted_exercise = {
                    "exercise_template_id": exercise["exercise_template_id"],
                    "superset_id": None,
                    "rest_seconds": exercise.get("rest_seconds", 90),
                    "notes": exercise.get("notes", ""),
                    "sets": exercise.get("sets", []),
                }
                formatted_exercises.append(formatted_exercise)

            # Update the routine data with formatted exercises
            routine_data["routine"]["exercises"] = formatted_exercises

            url = f"{self.base_url}/routines"
            logger.info(f"Sending POST request to: {url}")
            logger.debug(f"Headers: {json.dumps(self.headers, indent=2)}")
            logger.debug(f"Final request data: {json.dumps(routine_data, indent=2)}")

            response = requests.post(url, headers=self.headers, json=routine_data)
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response text: {response.text}")

            if response.status_code != 201:
                logger.error(
                    f"Error creating routine: {response.status_code} {response.text}"
                )
                return None

            routine_response = response.json()
            logger.debug(f"Routine response: {routine_response}")

            # The response has the routine data nested under a 'routine' key
            if "routine" in routine_response and isinstance(
                routine_response["routine"], list
            ):
                routine_data = routine_response["routine"][0]
                routine_id = routine_data.get("id")
                if routine_id:
                    logger.info(f"Created routine with ID: {routine_id}")
                    return routine_id
                else:
                    logger.error(f"Missing routine ID in response: {routine_response}")
                    return None
            else:
                logger.error(f"Unexpected response format: {routine_response}")
                return None

        except Exception as e:
            logger.error(f"Error creating routine: {str(e)}")
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
                    "title": template.get("title", ""),
                    "description": "",
                    "instructions": "",
                    "muscle_groups": muscle_groups,
                    "equipment": equipment,
                    "categories": [],
                    "difficulty": "",
                    "is_custom": template.get("is_custom", False),
                    "created_at": "",
                    "updated_at": "",
                    "exercise_template_id": template.get("id", ""),
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

    def create_routine_folder(self, title: str) -> Optional[str]:
        """Create a new routine folder in Hevy.

        Args:
            title: Title of the routine folder

        Returns:
            Folder ID if successful, None otherwise
        """
        try:
            folder_data = {"routine_folder": {"title": title}}
            logger.info(f"Creating routine folder with title: {title}")
            logger.debug(f"Request data: {json.dumps(folder_data, indent=2)}")

            url = f"{self.base_url}/routine_folders"
            logger.info(f"Sending POST request to: {url}")
            logger.debug(f"Headers: {json.dumps(self.headers, indent=2)}")

            response = requests.post(
                url,
                headers=self.headers,
                json=folder_data,
            )

            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response text: {response.text}")

            if response.status_code != 201:
                logger.error(
                    f"Error creating routine folder: {response.status_code} {response.text}"
                )
                return None

            folder_response = response.json()
            logger.debug(f"Folder response: {folder_response}")

            # The response is nested under routine_folder
            routine_folder = folder_response.get("routine_folder")
            if not routine_folder:
                logger.error(f"Missing routine_folder in response: {folder_response}")
                return None

            # Check for the expected response fields
            if not all(key in routine_folder for key in ["id", "title", "created_at"]):
                logger.error(
                    f"Missing required fields in routine_folder: {routine_folder}"
                )
                return None

            folder_id = str(
                routine_folder["id"]
            )  # Convert to string to match other IDs
            logger.info(f"Created routine folder with ID: {folder_id}")
            return folder_id

        except Exception as e:
            logger.error(f"Error creating routine folder: {str(e)}")
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

    def save_routine_folder(
        self, routine_folder: Dict[str, Any], user_id: str, db: Database
    ) -> Optional[Dict[str, Any]]:
        """Save an entire routine folder to Hevy and persist to CouchDB.

        Args:
            routine_folder: The routine folder data containing routines to save
            user_id: The user ID to associate with the routines
            db: Database instance for CouchDB persistence

        Returns:
            Dictionary containing the saved routine folder data with Hevy IDs, or None if failed
        """
        try:
            logger.info(f"Starting to save routine folder: {routine_folder['name']}")

            # First create the routine folder in Hevy
            folder_id = self.create_routine_folder(routine_folder["name"])
            if not folder_id:
                logger.error("Failed to create routine folder in Hevy")
                return None

            logger.info(f"Created routine folder in Hevy with ID: {folder_id}")

            # Save each routine in the folder
            saved_routines = []
            for routine in routine_folder["routines"]:
                # Create the routine data in the correct format
                routine_data = {
                    "routine": {
                        "title": routine["hevy_api"]["routine"]["title"],
                        "folder_id": folder_id,
                        "notes": routine["hevy_api"]["routine"].get("notes", ""),
                        "exercises": routine["hevy_api"]["routine"].get(
                            "exercises", []
                        ),
                    }
                }

                logger.info(
                    f"Creating routine: {routine['hevy_api']['routine']['title']}"
                )
                logger.debug(f"Routine data: {json.dumps(routine_data, indent=2)}")

                # Create the routine in Hevy
                routine_id = self.create_routine(routine_data)
                if routine_id:
                    logger.info(f"Created routine in Hevy with ID: {routine_id}")
                    # Update the routine data with the Hevy ID
                    routine["hevy_api"]["routine"]["id"] = routine_id
                    saved_routines.append(routine)
                else:
                    logger.error(
                        f"Failed to create routine in Hevy: {routine['hevy_api']['routine']['title']}"
                    )

            if not saved_routines:
                logger.error("Failed to create any routines in Hevy")
                return None

            # Create the document to save to CouchDB
            saved_folder = {
                "_id": f"routine_folder_{folder_id}",  # Unique ID for the document
                "type": "routine_folder",
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "folder_id": folder_id,
                "name": routine_folder["name"],
                "description": routine_folder.get("description", ""),
                "split_type": routine_folder.get("split_type", ""),
                "days_per_week": routine_folder.get("days_per_week", 0),
                "period": routine_folder.get("period", ""),
                "date_range": routine_folder.get("date_range", ""),
                "routines": saved_routines,
                "request_data": routine_folder,  # Save the original request data
                "hevy_response": {  # Save the Hevy response data
                    "folder_id": folder_id,
                    "routines": [
                        {
                            "id": routine["hevy_api"]["routine"]["id"],
                            "title": routine["hevy_api"]["routine"]["title"],
                        }
                        for routine in saved_routines
                    ],
                },
            }

            # Save to CouchDB
            try:
                db.save_document(saved_folder)  # Remove user_id parameter
                logger.info(
                    f"Saved routine folder to CouchDB with ID: {saved_folder['_id']}"
                )
            except Exception as e:
                logger.error(f"Error saving routine folder to CouchDB: {str(e)}")
                # Continue even if CouchDB save fails, as the routines are already in Hevy

            return saved_folder

        except Exception as e:
            logger.error(f"Error saving routine folder to Hevy: {str(e)}")
            return None
