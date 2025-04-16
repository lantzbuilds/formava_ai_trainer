import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI

from config.database import Database
from services.hevy_api import HevyAPI
from services.routine_folder_builder import RoutineFolderBuilder
from services.vector_store import ExerciseVectorStore
from utils.crypto import decrypt_api_key

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class OpenAIService:
    """Service for interacting with OpenAI API to generate workout recommendations."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=self.api_key)
        self._vector_store = None
        self._hevy_api = None
        self.db = Database()  # Initialize database connection

    @property
    def vector_store(self):
        """Lazy load the vector store."""
        if self._vector_store is None:
            self._vector_store = ExerciseVectorStore()
        return self._vector_store

    # TODO: Should user be retrieved in __init__ and HevyAPI be initialized there?
    def _get_hevy_api(self, encrypted_api_key: str) -> HevyAPI:
        """Get or create a HevyAPI instance with the given encrypted API key.

        Args:
            encrypted_api_key: The encrypted API key to use

        Returns:
            HevyAPI instance
        """
        if not self._hevy_api:
            self._hevy_api = HevyAPI(encrypted_api_key)
        return self._hevy_api

    def analyze_workout_form(
        self, exercise_name: str, description: str
    ) -> Dict[str, Any]:
        """
        Analyze workout form based on exercise name and description.

        Args:
            exercise_name: Name of the exercise
            description: Description of the exercise form

        Returns:
            Analysis results
        """
        prompt = f"""
        I need an analysis of the following exercise form:
        
        Exercise: {exercise_name}
        Description: {description}
        
        Please provide feedback on:
        1. Proper form and technique
        2. Common mistakes to avoid
        3. Tips for improvement
        4. Safety considerations
        
        Format the response as a JSON object with the following structure:
        {{
            "proper_form": "Description of proper form",
            "common_mistakes": ["Mistake 1", "Mistake 2", ...],
            "improvement_tips": ["Tip 1", "Tip 2", ...],
            "safety_considerations": ["Consideration 1", "Consideration 2", ...]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert personal trainer with deep knowledge of exercise form and technique.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            # Parse the response
            content = response.choices[0].message.content

            # Clean the content by removing control characters
            content = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", content)

            # Extract JSON from the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON response: {e}")
                    print(f"Response content: {content}")
                    return {
                        "proper_form": "Unable to analyze form",
                        "common_mistakes": [],
                        "improvement_tips": [],
                        "safety_considerations": [],
                    }
            else:
                print("Could not extract JSON from response")
                print(f"Response content: {content}")
                return {
                    "proper_form": "Unable to analyze form",
                    "common_mistakes": [],
                    "improvement_tips": [],
                    "safety_considerations": [],
                }
        except Exception as e:
            print(f"Error analyzing form: {e}")
            return {
                "proper_form": "Unable to analyze form",
                "common_mistakes": [],
                "improvement_tips": [],
                "safety_considerations": [],
            }

    def generate_routine(
        self,
        user_id: str,
        routine_folder_id: str,
        day: str,
        focus: str,
        experience_level: str,
        goal: str,
    ) -> Dict:
        """Generate a workout routine for a specific day."""
        try:
            logger.info(f"Generating routine for {day} - {focus}")

            # Get user document from database
            user_doc = self.db.get_document(user_id)
            if not user_doc:
                raise ValueError(f"User document not found for user_id: {user_id}")

            # Search for relevant exercises
            relevant_exercises = []

            if focus.lower() == "full body":
                # For full body workouts, search for exercises targeting different muscle groups
                muscle_groups = ["chest", "back", "legs", "shoulders", "arms"]
                for muscle_group in muscle_groups:
                    logger.info(
                        f"Searching for {muscle_group} exercises with query: Primary muscles: {muscle_group}"
                    )
                    exercises = self.vector_store.search_exercises(
                        query=f"Primary muscles: {muscle_group}",
                        k=5,  # Get 5 exercises per muscle group
                    )
                    # Add exercises that aren't already in the list
                    for exercise in exercises:
                        if not any(
                            e["id"] == exercise["id"] for e in relevant_exercises
                        ):
                            relevant_exercises.append(exercise)

                logger.info(
                    f"Found {len(relevant_exercises)} exercises for full body routine"
                )
                logger.info(
                    f"Exercises by muscle group: {[e['title'] for e in relevant_exercises]}"
                )
            else:
                # For other workout types, use the focus directly
                search_query = f"{focus} exercises for {experience_level} level"
                logger.info(f"Searching for exercises with query: {search_query}")
                relevant_exercises = self.vector_store.search_exercises(
                    query=search_query,
                    k=10,  # Get more exercises for variety
                )
                logger.info(
                    f"Found {len(relevant_exercises)} exercises for {focus} routine"
                )

            # Ensure we have enough exercises
            if not relevant_exercises:
                logger.warning("No exercises found, trying fallback search")
                relevant_exercises = self.vector_store.search_exercises(
                    query=f"exercises for {experience_level} level",
                    k=10,
                )
                if not relevant_exercises:
                    raise ValueError("No exercises found for routine generation")

            # Use only unique exercises
            unique_exercises = []
            seen_ids = set()
            for exercise in relevant_exercises:
                if exercise["id"] not in seen_ids:
                    seen_ids.add(exercise["id"])
                    unique_exercises.append(exercise)

            logger.info(f"Using {len(unique_exercises)} unique exercises for routine")

            # Create prompt for OpenAI
            prompt = f"""
            You are an expert personal trainer with deep knowledge of exercise science and workout programming. Your response must be a valid JSON object with no additional text before or after. The JSON must include 'routine_description' and 'hevy_api' fields.

            Create a personalized workout routine based on the following information:

            User Profile:
            - Experience Level: {experience_level}
            - Fitness Goals: {goal}
            - Medical Concerns: {', '.join([f"{i['description']} ({i['body_part']})" for i in user_doc.get('injuries', []) if i.get('is_active', False)]) if user_doc.get('injuries') else 'None'}
            - Preferred Session Duration: {user_doc.get('preferred_workout_duration', 60)} minutes
            - Focus: {focus}
            - Folder ID: {routine_folder_id}

            Available Exercises (you MUST use these exact exercises):
            {json.dumps([{
                'title': exercise['title'],
                'exercise_template_id': exercise['id'],
                'muscle_groups': exercise['muscle_groups'],
                'equipment': exercise['equipment']
            } for exercise in unique_exercises], indent=2)}

            Requirements:
            1. Create a {focus} workout that lasts approximately {user_doc.get('preferred_workout_duration', 60)} minutes
            2. Include enough exercises to fill the time appropriately
            3. Design a balanced program that:
               - Focuses on the {focus} muscle groups
               - Is appropriate for {experience_level} level
               - Uses ONLY the exercises from the list above
               - Provides specific sets, reps, and intensity recommendations
               - Includes modifications for any injuries or limitations
               - Incorporates progressive overload principles
               - Includes appropriate rest periods between sets
            4. Include warm-up and cool-down recommendations
            5. Ensure proper exercise selection and volume to fill the entire session duration

            Format your response as a JSON object with the following structure:
            {{
                "routine_description": "A detailed description of the routine's goals, considerations, and overall approach",
                "hevy_api": {{
                    "routine": {{
                        "title": "string",
                        "folder_id": "{routine_folder_id}",
                        "notes": "string",
                        "exercises": [
                            {{
                                "title": "string (MUST be one of the exact titles from the exercises list above)",
                                "exercise_template_id": "string (MUST match the exercise_template_id from the exercises list above)",
                                "superset_id": null,
                                "rest_seconds": number,
                                "notes": "string",
                                "exercise_description": "A detailed explanation of why this exercise is included in the routine, including its benefits and how it contributes to the user's goals",
                                "sets": [
                                    {{
                                        "type": "normal",
                                        "weight_kg": number or null,
                                        "reps": number or null,
                                        "distance_meters": number or null,
                                        "duration_seconds": number or null,
                                        "custom_metric": null
                                    }}
                                ]
                            }}
                        ]
                    }}
                }}
            }}

            Important Notes:
            - The workout should focus on {focus} exercises
            - Include appropriate rest periods between sets (typically 60-90 seconds)
            - Ensure exercises are properly balanced for the {focus} focus
            - Include warm-up and cool-down recommendations
            - Make sure the total volume (sets × reps × weight) is appropriate for {experience_level} level
            - For the hevy_api format:
              * You MUST use ONLY the exact titles and exercise_template_ids from the exercises list above
              * The title and exercise_template_id fields are REQUIRED and cannot be null
              * Set folder_id to "{routine_folder_id}" as this routine belongs to a specific folder
              * Include appropriate rest_seconds between sets
              * Set type to "normal" for all sets
              * Set distance_meters, duration_seconds, and custom_metric to null unless specifically needed
              * Include helpful notes for each exercise
              * Provide a detailed exercise_description explaining why each exercise is included
            """

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert personal trainer with deep knowledge of exercise science and workout programming. Your response must be a valid JSON object with no additional text before or after. The JSON must include 'routine_description' and 'hevy_api' fields.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            # Extract and parse response
            content = response.choices[0].message.content
            logger.debug(f"OpenAI Response Content: {content}")

            # Clean the content by removing control characters and any text before/after JSON
            content = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", content)
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                try:
                    routine = json.loads(json_str)
                    # Log the generated routine
                    logger.info("Generated routine JSON:")
                    logger.info(json.dumps(routine, indent=2))

                    # Validate the required fields
                    if not all(
                        key in routine for key in ["routine_description", "hevy_api"]
                    ):
                        logger.error("Missing required fields in response")
                        return None

                    if not all(key in routine["hevy_api"] for key in ["routine"]):
                        logger.error("Missing required fields in hevy_api")
                        return None

                    if not all(
                        key in routine["hevy_api"]["routine"]
                        for key in ["title", "notes", "exercises"]
                    ):
                        logger.error("Missing required fields in routine")
                        return None

                    # Validate each exercise has required fields
                    for exercise in routine["hevy_api"]["routine"]["exercises"]:
                        required_fields = ["title", "sets", "exercise_description"]
                        if not all(key in exercise for key in required_fields):
                            logger.error(
                                f"Missing required fields in exercise: {exercise}"
                            )
                            return None

                    # Ensure folder_id is set correctly
                    routine["hevy_api"]["routine"]["folder_id"] = routine_folder_id

                    logger.debug(f"Parsed Routine: {json.dumps(routine, indent=2)}")
                    return routine
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON response: {e}")
                    return None
            else:
                logger.error("Could not extract JSON from response")
                return None
        except Exception as e:
            logger.error(f"Error generating routine: {str(e)}")
            return None

    def _get_date_range(self, period: Literal["week", "month"]) -> str:
        """
        Get a formatted date range string for the given period, starting from the next full week.

        Args:
            period: Either "week" or "month" to determine the date range

        Returns:
            Formatted date range string (e.g., "Mar 25-31, 2024" or "Mar 25 - Apr 21, 2024")
        """
        today = datetime.now()

        # Calculate days until next Monday (0 = Monday, 1 = Tuesday, etc.)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            # If today is Monday, start next week
            days_until_monday = 7

        start_date = today + timedelta(days=days_until_monday)

        if period == "week":
            end_date = start_date + timedelta(days=6)
            return f"{start_date.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"
        else:  # month
            end_date = start_date + timedelta(days=27)  # 4 weeks
            return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"

    def generate_routine_folder(
        self, name: str, description: str, context: dict, period: str = "week"
    ) -> Optional[dict]:
        """Generate a routine folder with multiple workout routines based on popular splits.

        Args:
            name: Name of the routine folder
            description: Description of the routine folder
            context: Dictionary containing user profile and other context
            period: Time period for the routines ("week" or "month")

        Returns:
            Dictionary containing the routine folder structure or None if generation fails
        """
        try:
            # Extract user profile from context
            user_profile = context.get("user_profile", {})
            experience_level = user_profile.get("experience_level", "beginner")
            fitness_goals = user_profile.get("fitness_goals", [])
            workout_schedule = user_profile.get("workout_schedule", {})
            days_per_week = workout_schedule.get("days_per_week", 3)

            # Determine workout split and routine configurations
            split_type, routines = RoutineFolderBuilder.determine_workout_split(
                days_per_week, experience_level
            )

            logger.info(f"Generating routines for split type: {split_type}")
            logger.info(f"Routines to generate: {routines}")

            # Generate individual routines for each day
            generated_routines = []
            for routine in routines:
                logger.info(
                    f"Generating routine for {routine['day']} - {routine['focus']}"
                )

                # Generate the routine using generate_routine
                day_routine = self.generate_routine(
                    user_id=context["user_id"],
                    routine_folder_id=None,  # Will be set when routines are saved to Hevy
                    day=routine["day"],
                    focus=routine["focus"],
                    experience_level=experience_level,
                    goal=fitness_goals[0] if fitness_goals else "General Fitness",
                )

                if day_routine:
                    logger.info(f"Successfully generated routine for {routine['day']}")
                    logger.debug(
                        f"Generated routine: {json.dumps(day_routine, indent=2)}"
                    )
                    generated_routines.append(day_routine)
                else:
                    logger.error(f"Failed to generate routine for {routine['day']}")

            if not generated_routines:
                logger.error("Failed to generate any routines")
                return None

            # Build the routine folder structure
            date_range = RoutineFolderBuilder.get_date_range(period)
            routine_folder = RoutineFolderBuilder.build_routine_folder(
                name=name,
                description=description,
                split_type=split_type,
                routines=routines,
                period=period,
                date_range=date_range,
            )
            routine_folder["routines"] = generated_routines

            logger.info(
                f"Successfully generated routine folder with {len(generated_routines)} routines"
            )
            return routine_folder

        except Exception as e:
            logger.error(f"Error generating routine folder: {str(e)}")
            return None
