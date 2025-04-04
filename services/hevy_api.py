import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from ..utils.crypto import decrypt_api_key


class HevyAPI:
    """Service for interacting with the Hevy API."""

    def __init__(self, encrypted_api_key: str):
        """Initialize the Hevy API client with an encrypted API key."""
        self.api_key = decrypt_api_key(encrypted_api_key)
        if not self.api_key:
            raise ValueError("Invalid or missing Hevy API key")

        self.base_url = "https://api.hevyapp.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

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

        for workout in workouts:
            # Check if workout already exists
            existing = db.get_workout_by_hevy_id(workout["id"])
            if not existing:
                # Get full workout details
                details = self.get_workout_details(workout["id"])

                # Convert to our workout format
                converted_workout = {
                    "id": f"hevy_{workout['id']}",
                    "user_id": user_id,
                    "title": details.get("name", "Hevy Workout"),
                    "description": details.get("notes", ""),
                    "start_time": details["start_time"],
                    "end_time": details["end_time"],
                    "exercises": [
                        {
                            "index": i,
                            "title": ex["name"],
                            "exercise_template_id": f"hevy_{ex['exercise_id']}",
                            "sets": [
                                {
                                    "index": j,
                                    "type": "normal",
                                    "weight_kg": s["weight"],
                                    "reps": s["reps"],
                                    "rpe": s.get("rpe"),
                                }
                                for j, s in enumerate(ex["sets"])
                            ],
                        }
                        for i, ex in enumerate(details["exercises"])
                    ],
                }

                # Save to database
                db.save_document(converted_workout)
                synced_count += 1

        return synced_count
