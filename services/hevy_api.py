import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests


class HevyAPI:
    """Service for interacting with the Hevy API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hevyapp.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
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
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

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
            existing_workout = db.get_document(workout["id"])

            if not existing_workout:
                # Add user_id to workout
                workout["user_id"] = user_id

                # Save to database
                db.save_document(workout)
                synced_count += 1

        return synced_count
