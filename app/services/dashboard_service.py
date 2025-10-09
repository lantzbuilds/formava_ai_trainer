"""
Dashboard service - handles dashboard data aggregation.
Shared between Gradio and FastAPI interfaces.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import dateutil.parser

from app.config.database import Database
from app.models.user import UserProfile

logger = logging.getLogger(__name__)
db = Database()


class DashboardService:
    """Service for handling dashboard data operations."""

    @staticmethod
    def get_dashboard_data(user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a user.

        Args:
            user_id: User's ID

        Returns:
            Dictionary containing:
            - welcome_message: str
            - total_workouts: int (all-time)
            - recent_workouts: int (last 30 days)
            - avg_workouts_per_week: float
            - last_workout_date: str or None
            - current_streak: int (days)
            - fitness_goals: List[str]
            - active_injuries: List[Dict]

        Raises:
            ValueError: If user not found
        """
        try:
            logger.info(f"Getting dashboard data for user ID: {user_id}")

            # Get user profile
            user_doc = db.get_document(user_id)
            if not user_doc:
                logger.error(f"User document not found for ID: {user_id}")
                raise ValueError(f"User not found: {user_id}")

            user = UserProfile.from_dict(user_doc)

            # Get workout stats for the last 30 days (for recent activity)
            now = datetime.now(timezone.utc)
            thirty_days_ago = now - timedelta(days=30)
            recent_stats = db.get_workout_stats(user_id, thirty_days_ago, now)

            # Get all-time workout stats (for total counts)
            all_time_stats = db.get_workout_stats(user_id)

            logger.info(f"Recent stats (30 days): {recent_stats}")
            logger.info(f"All-time stats: {all_time_stats}")

            # Process recent stats (last 30 days)
            if recent_stats and len(recent_stats) > 0:
                recent_data = recent_stats[0]
                recent_workouts_count = recent_data.get("total_workouts", 0)
                avg_workouts_per_week = recent_workouts_count / 4.3  # ~30 days / 7 days
            else:
                recent_workouts_count = 0
                avg_workouts_per_week = 0.0

            # Process all-time stats (for total counts)
            if all_time_stats and len(all_time_stats) > 0:
                all_time_data = all_time_stats[0]
                total_workouts_count = all_time_data.get("total_workouts", 0)
                last_workout_date = all_time_data.get("last_workout_date")
            else:
                total_workouts_count = 0
                last_workout_date = None

            # Format last workout date
            if last_workout_date:
                try:
                    dt = dateutil.parser.parse(last_workout_date)
                    last_workout_str = dt.strftime("%Y-%m-%d")
                except:
                    last_workout_str = "Unknown date"
            else:
                last_workout_str = None

            # Calculate streak (simplified approach)
            # Note: For accurate streak calculation, we'd need individual workout data
            # This is a placeholder that could be enhanced
            streak = 0
            # TODO: Implement proper streak calculation

            # Format goals
            goals = [goal.value for goal in user.fitness_goals]

            # Format active injuries
            active_injuries = [
                {
                    "description": injury.description,
                    "body_part": injury.body_part,
                    "severity": injury.severity.value,
                    "date_injured": (
                        injury.date_injured.isoformat()
                        if hasattr(injury.date_injured, "isoformat")
                        else str(injury.date_injured)
                    ),
                    "notes": injury.notes,
                }
                for injury in user.injuries
                if injury.is_active
            ]

            return {
                "welcome_message": f"Welcome back, {user.username}!",
                "total_workouts": total_workouts_count,
                "recent_workouts": recent_workouts_count,
                "avg_workouts_per_week": round(avg_workouts_per_week, 1),
                "last_workout_date": last_workout_str,
                "current_streak": streak,
                "fitness_goals": goals,
                "active_injuries": active_injuries,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get dashboard data: {str(e)}")

    @staticmethod
    def get_user_profile(user_id: str) -> Dict[str, Any]:
        """
        Get user profile data (read-only for MVP).

        Args:
            user_id: User's ID

        Returns:
            Dictionary containing user profile data

        Raises:
            ValueError: If user not found
        """
        try:
            logger.info(f"Getting profile for user ID: {user_id}")

            user_doc = db.get_document(user_id)
            if not user_doc:
                logger.error(f"User document not found for ID: {user_id}")
                raise ValueError(f"User not found: {user_id}")

            user = UserProfile.from_dict(user_doc)

            # Return sanitized profile data (no password hash)
            profile_data = {
                "username": user.username,
                "email": user.email,
                "age": user.age,
                "sex": user.sex.value if user.sex else None,
                "height_cm": user.height_cm,
                "weight_kg": user.weight_kg,
                "experience_level": user.experience_level,
                "preferred_units": (
                    user.preferred_units.value if user.preferred_units else "imperial"
                ),
                "fitness_goals": [goal.value for goal in user.fitness_goals],
                "preferred_workout_days": user.preferred_workout_days,
                "preferred_workout_duration": user.preferred_workout_duration,
                "injuries": [
                    {
                        "description": injury.description,
                        "body_part": injury.body_part,
                        "severity": injury.severity.value,
                        "date_injured": (
                            injury.date_injured.isoformat()
                            if hasattr(injury.date_injured, "isoformat")
                            else str(injury.date_injured)
                        ),
                        "is_active": injury.is_active,
                        "notes": injury.notes,
                    }
                    for injury in user.injuries
                ],
                "has_hevy_api_key": bool(user.hevy_api_key),
            }

            return profile_data

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get user profile: {str(e)}")
