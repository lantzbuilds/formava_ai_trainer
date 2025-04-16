"""
Service for building and formatting routine folders.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RoutineFolderBuilder:
    """Service for building and formatting routine folders."""

    @staticmethod
    def determine_workout_split(
        days_per_week: int, experience_level: str
    ) -> tuple[str, List[Dict[str, str]]]:
        """Determine the appropriate workout split based on days per week and experience level.

        Args:
            days_per_week: Number of workout days per week
            experience_level: User's experience level (beginner, intermediate, advanced)

        Returns:
            Tuple of (split_type, list of day configurations)
        """
        if days_per_week == 3:
            if experience_level == "beginner":
                split_type = "full_body"
                routines = [
                    {"day": "Monday", "focus": "Full Body"},
                    {"day": "Wednesday", "focus": "Full Body"},
                    {"day": "Friday", "focus": "Full Body"},
                ]
            else:
                split_type = "upper_lower"
                routines = [
                    {"day": "Monday", "focus": "Upper Body"},
                    {"day": "Wednesday", "focus": "Lower Body"},
                    {"day": "Friday", "focus": "Upper Body"},
                ]
        elif days_per_week == 4:
            split_type = "upper_lower"
            routines = [
                {"day": "Monday", "focus": "Upper Body"},
                {"day": "Tuesday", "focus": "Lower Body"},
                {"day": "Thursday", "focus": "Upper Body"},
                {"day": "Friday", "focus": "Lower Body"},
            ]
        elif days_per_week >= 5:
            split_type = "ppl"
            routines = [
                {"day": "Monday", "focus": "Push (Chest, Shoulders, Triceps)"},
                {"day": "Tuesday", "focus": "Pull (Back, Biceps)"},
                {"day": "Wednesday", "focus": "Legs"},
                {"day": "Thursday", "focus": "Push (Chest, Shoulders, Triceps)"},
                {"day": "Friday", "focus": "Pull (Back, Biceps)"},
            ]
            if days_per_week == 6:
                routines.append({"day": "Saturday", "focus": "Legs"})
        else:
            raise ValueError(f"Invalid number of workout days: {days_per_week}")

        return split_type, routines

    @staticmethod
    def build_routine_folder(
        name: str,
        description: str,
        split_type: str,
        routines: List[Dict[str, str]],
        period: str,
        date_range: str,
    ) -> Dict[str, Any]:
        """Build a routine folder structure.

        Args:
            name: Name of the routine folder
            description: Description of the routine folder
            split_type: Type of workout split
            routines: List of routine configurations
            period: Time period for the routines
            date_range: Date range string

        Returns:
            Dictionary containing the routine folder structure
        """
        return {
            "name": f"{name} - {date_range}",
            "description": description,
            "split_type": split_type,
            "days_per_week": len(routines),
            "period": period,
            "date_range": date_range,
            "routines": [],  # Will be populated with generated routines
        }

    @staticmethod
    def format_for_hevy(routine_folder: Dict[str, Any]) -> Dict[str, Any]:
        """Format a routine folder for Hevy API.

        Args:
            routine_folder: The routine folder to format

        Returns:
            Dictionary formatted for Hevy API
        """
        # Add any Hevy-specific formatting here
        return routine_folder

    @staticmethod
    def get_date_range(period: str) -> str:
        """Get a date range string for the given period.

        Args:
            period: Time period ("week" or "month")

        Returns:
            Date range string
        """
        now = datetime.now(timezone.utc)
        if period == "week":
            end_date = now + timedelta(days=7)
            return f"{now.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif period == "month":
            end_date = now + timedelta(days=30)
            return f"{now.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        else:
            raise ValueError(f"Invalid period: {period}")
