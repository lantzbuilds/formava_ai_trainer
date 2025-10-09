"""
AI service - handles AI recommendation and routine generation.
Shared between Gradio and FastAPI interfaces.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.config.database import Database
from app.models.user import UserProfile
from app.services.hevy_api import HevyAPI
from app.services.openai_service import OpenAIService
from app.services.routine_folder_builder import RoutineFolderBuilder
from app.utils.formatters import format_routine_markdown

logger = logging.getLogger(__name__)
db = Database()
openai_service = OpenAIService()


class AIService:
    """Service for handling AI-powered workout recommendations."""

    @staticmethod
    def get_ai_recs_summary(user_id: str) -> Dict[str, Any]:
        """
        Get summary data for the AI recommendations page.

        Args:
            user_id: User's ID

        Returns:
            Dictionary containing:
            - profile_summary: Dict with user profile info
            - workout_summary: Dict with recent workout stats
            - exercises_summary: Dict with available exercises count

        Raises:
            ValueError: If user not found
        """
        try:
            logger.info(f"Getting AI recs summary for user ID: {user_id}")

            # Get user profile
            user_doc = db.get_document(user_id)
            if not user_doc:
                logger.error(f"User document not found for ID: {user_id}")
                raise ValueError(f"User not found: {user_id}")

            user = UserProfile.from_dict(user_doc)

            # Build profile summary
            profile_summary = {
                "experience_level": user.experience_level,
                "fitness_goals": [g.value for g in user.fitness_goals],
                "workout_days": user.preferred_workout_days,
                "workout_duration": user.preferred_workout_duration,
                "active_injuries": [
                    {
                        "description": injury.description,
                        "body_part": injury.body_part,
                    }
                    for injury in user.injuries
                    if injury.is_active
                ],
            }

            # Get user's recent workouts
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            workouts = db.get_user_workout_history(user_id, start_date, end_date)

            # Build workout summary
            workout_count = len(workouts) if workouts else 0
            if workouts and workout_count > 0:
                total_exercises = sum(len(w.get("exercises", [])) for w in workouts)
                avg_exercises = total_exercises / workout_count
                workout_summary = {
                    "workouts_last_30_days": workout_count,
                    "avg_exercises_per_workout": round(avg_exercises, 1),
                }
            else:
                workout_summary = {
                    "workouts_last_30_days": 0,
                    "avg_exercises_per_workout": 0,
                }

            # Get available exercises count
            exercises = db.get_exercises(user_id=user_id, include_custom=True)
            exercises_summary = {
                "total_exercises_available": len(exercises) if exercises else 0,
            }

            return {
                "profile_summary": profile_summary,
                "workout_summary": workout_summary,
                "exercises_summary": exercises_summary,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting AI recs summary: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get AI recommendations summary: {str(e)}")

    @staticmethod
    def generate_routine(
        user_id: str,
        split_type: str = "auto",
        period: str = "week",
        include_cardio: bool = True,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate an AI-powered workout routine for the user.

        Args:
            user_id: User's ID
            split_type: Workout split type (auto, full_body, upper_lower, push_pull)
            period: Time period (week, month)
            include_cardio: Whether to include cardio exercises
            title: Custom title for the routine folder (optional)

        Returns:
            Dictionary containing the generated routine folder

        Raises:
            ValueError: If generation fails
        """
        try:
            logger.info(f"Generating routine for user ID: {user_id}")

            # Get user profile
            user_doc = db.get_document(user_id)
            if not user_doc:
                logger.error(f"User document not found for ID: {user_id}")
                raise ValueError(f"User not found: {user_id}")

            user = UserProfile.from_dict(user_doc)

            # Build context for AI generation
            context = {
                "user_id": user_id,
                "user_profile": {
                    "experience_level": user.experience_level,
                    "fitness_goals": [g.value for g in user.fitness_goals],
                    "preferred_workout_duration": user.preferred_workout_duration,
                    "preferred_units": getattr(
                        user.preferred_units, "value", "imperial"
                    ),
                    "injuries": [
                        {
                            "description": i.description,
                            "body_part": i.body_part,
                            "is_active": i.is_active,
                        }
                        for i in user.injuries
                    ],
                    "workout_schedule": {
                        "days_per_week": user.preferred_workout_days,
                    },
                },
                "generation_preferences": {
                    "split_type": split_type,
                    "include_cardio": include_cardio,
                },
            }

            # Generate default title if not provided
            if not title:
                date_range = RoutineFolderBuilder.get_date_range(period)
                split_label = split_type.replace("_", " ").title()
                title = f"{split_label} - {date_range}"

            # Generate routine using OpenAI service
            routine_folder = openai_service.generate_routine_folder(
                name=title,
                description="Personalized workout plan based on your profile and goals",
                context=context,
                period=period,
            )

            if not routine_folder:
                raise ValueError("Failed to generate routine. Please try again.")

            logger.info(f"Routine generated successfully for user {user_id}")
            return routine_folder

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error generating routine: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate routine: {str(e)}")

    @staticmethod
    def save_routine_to_hevy(user_id: str, routine_folder: Dict[str, Any]) -> bool:
        """
        Save a generated routine to Hevy.

        Args:
            user_id: User's ID
            routine_folder: The routine folder to save

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If save fails
        """
        try:
            logger.info(f"Saving routine to Hevy for user ID: {user_id}")

            # Get user profile
            user_doc = db.get_document(user_id)
            if not user_doc:
                logger.error(f"User document not found for ID: {user_id}")
                raise ValueError(f"User not found: {user_id}")

            user = UserProfile.from_dict(user_doc)

            if not user.hevy_api_key:
                raise ValueError(
                    "Hevy API key is not configured. Please configure it in your profile."
                )

            # Initialize Hevy API
            hevy_api = HevyAPI(api_key=user.hevy_api_key, is_encrypted=True)

            # Save routine folder
            saved_folder = hevy_api.save_routine_folder(
                routine_folder=routine_folder,
                user_id=user_id,
                db=db,
            )

            if not saved_folder:
                raise ValueError("Failed to save routine to Hevy. Please try again.")

            logger.info(f"Routine saved to Hevy successfully for user {user_id}")
            return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error saving routine to Hevy: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to save routine to Hevy: {str(e)}")
