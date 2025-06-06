"""
Service for building and formatting routine folders.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.config.database import Database
from app.models.exercise import Exercise, ExerciseList

logger = logging.getLogger(__name__)


class RoutineFolderBuilder:
    """Service for building and formatting routine folders."""

    @staticmethod
    def determine_workout_split(
        days_per_week: int, experience_level: str, preferred_split: str = "auto"
    ) -> tuple[str, List[Dict[str, str]]]:
        """Determine the workout split based on user preference and handle additional days.

        Args:
            days_per_week: Number of workout days per week
            experience_level: User's experience level (beginner, intermediate, advanced)
            preferred_split: Preferred split type ("auto", "full_body", "upper_lower", "push_pull")

        Returns:
            Tuple of (split_type, list of day configurations)
        """
        # For beginners, default to full body regardless of days
        if preferred_split == "auto" and experience_level == "beginner":
            preferred_split = "full_body"
        # For others, default to upper/lower for 3-4 days, push/pull for 5+ days
        elif preferred_split == "auto":
            preferred_split = "upper_lower" if days_per_week <= 4 else "push_pull"

        if preferred_split == "full_body":
            base_routines = [
                {"day": "Monday", "focus": "Full Body"},
                {"day": "Wednesday", "focus": "Full Body"},
                {"day": "Friday", "focus": "Full Body"},
            ]
            # Add extra days as additional full body workouts
            extra_days = days_per_week - 3
            if extra_days > 0:
                base_routines.append({"day": "Tuesday", "focus": "Full Body"})
            if extra_days > 1:
                base_routines.append({"day": "Thursday", "focus": "Full Body"})
            if extra_days > 2:
                base_routines.append({"day": "Saturday", "focus": "Full Body"})
            return "full_body", base_routines

        elif preferred_split == "upper_lower":
            base_routines = [
                {"day": "Monday", "focus": "Upper Body"},
                {"day": "Wednesday", "focus": "Lower Body"},
                {"day": "Friday", "focus": "Upper Body"},
            ]
            # Add extra days as additional upper/lower workouts
            extra_days = days_per_week - 3
            if extra_days > 0:
                base_routines.append({"day": "Tuesday", "focus": "Lower Body"})
            if extra_days > 1:
                base_routines.append({"day": "Thursday", "focus": "Upper Body"})
            if extra_days > 2:
                base_routines.append({"day": "Saturday", "focus": "Lower Body"})
            return "upper_lower", base_routines

        elif preferred_split == "push_pull":
            base_routines = [
                {"day": "Monday", "focus": "Push (Chest, Shoulders, Triceps)"},
                {"day": "Tuesday", "focus": "Pull (Back, Biceps)"},
                {"day": "Wednesday", "focus": "Legs and Abdominals"},
                {"day": "Thursday", "focus": "Push (Chest, Shoulders, Triceps)"},
                {"day": "Friday", "focus": "Pull (Back, Biceps)"},
            ]
            # Add extra days as additional leg and abs workouts
            extra_days = days_per_week - 5
            if extra_days > 0:
                base_routines.append(
                    {"day": "Saturday", "focus": "Legs and Abdominals"}
                )
            return "push_pull", base_routines

        raise ValueError(f"Invalid split type: {preferred_split}")

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
            "name": name,  # Use the provided name directly
            "description": description,
            "split_type": split_type,
            "days_per_week": len(routines),
            "period": period,
            "date_range": date_range,
            "routines": routines,  # Include the actual routines
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
