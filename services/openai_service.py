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

    def _create_routine_prompt(
        self,
        day: str,
        focus: str,
        exercises: List[Dict[str, Any]],
        context: dict,
        include_cardio: bool,
    ) -> str:
        """Create the prompt for OpenAI to generate a workout routine.

        Args:
            day: Day of the week
            focus: Focus of the workout
            exercises: List of available exercises
            context: User context and preferences
            include_cardio: Whether to include cardio in the routine

        Returns:
            Formatted prompt string
        """
        user_profile = context["user_profile"]
        experience_level = user_profile["experience_level"]
        fitness_goals = user_profile["fitness_goals"]
        injuries = user_profile.get("injuries", [])
        preferred_duration = user_profile.get("preferred_workout_duration", 60)

        # Format injuries for the prompt
        injury_text = (
            ", ".join(
                [
                    f"{i['description']} ({i['body_part']})"
                    for i in injuries
                    if i.get("is_active", False)
                ]
            )
            if injuries
            else "None"
        )

        return f"""
        You are an expert personal trainer with deep knowledge of exercise science and workout programming. Your response must be a valid JSON object with no additional text before or after. The JSON must include 'routine_description' and 'hevy_api' fields.

        Create a personalized workout routine based on the following information:

        User Profile:
        - Experience Level: {experience_level}
        - Fitness Goals: {', '.join(fitness_goals)}
        - Medical Concerns: {injury_text}
        - Preferred Session Duration: {preferred_duration} minutes
        - Focus: {focus}
        - Include Cardio: {include_cardio}

        Available Exercises (you MUST use these exact exercises):
        {json.dumps([{
            'title': exercise['title'],
            'exercise_template_id': exercise['id'],
            'muscle_groups': exercise['muscle_groups'],
            'equipment': exercise['equipment']
        } for exercise in exercises], indent=2)}

        Requirements:
        1. Create a {focus} workout that lasts approximately {preferred_duration} minutes
        2. Include enough exercises to fill the time appropriately
        3. Design a balanced program that:
           - Focuses on the {focus} muscle groups
           - Is appropriate for {experience_level} level
           - Uses ONLY the exercises from the list above
           - Provides specific sets, reps, and intensity recommendations
           - Includes modifications for any injuries or limitations
           - Incorporates progressive overload principles
           - Includes appropriate rest periods between sets
        4. {f"Include warm-up and cool-down recommendations" if experience_level == "beginner" else ""}
        5. Ensure proper exercise selection and volume to fill the entire session duration
        6. If Include Cardio is True, add appropriate cardio exercises to the routine:
           - For strength-focused days (Push/Pull), add 10-15 minutes of moderate cardio
           - For leg days, add 5-10 minutes of light cardio as warm-up
           - For full body days, distribute cardio throughout the workout
           - Adjust cardio duration based on the total workout time

        Format your response as a JSON object with the following structure:
        {{
            "routine_description": "A detailed description of the routine's goals, considerations, and overall approach",
            "hevy_api": {{
                "routine": {{
                    "title": "string",
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
                                    "type": "warmup|normal|failure|dropset",
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
        - {f"Include warm-up and cool-down recommendations" if experience_level == "beginner" else ""}
        - Make sure the total volume (sets × reps × weight) is appropriate for {experience_level} level
        - For the hevy_api format:
          * You MUST use ONLY the exact titles and exercise_template_ids from the exercises list above
          * The title and exercise_template_id fields are REQUIRED and cannot be null
          * Include appropriate rest_seconds between sets
          * Set types can be:
            - "warmup": Lighter sets to prepare for working sets
            - "normal": Standard working sets
            - "failure": Sets taken to muscular failure
            - "dropset": Sets with reduced weight after reaching failure
          * Set distance_meters, duration_seconds, and custom_metric to null unless specifically needed
          * Include helpful notes for each exercise
          * Provide a detailed exercise_description explaining why each exercise is included
        """

    def generate_routine(
        self, day: str, focus: str, context: dict, include_cardio: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Generate a workout routine for a specific day.

        Args:
            day: Day of the week
            focus: Focus of the workout
            context: User context and preferences
            include_cardio: Whether to include cardio in the routine

        Returns:
            Dictionary containing the generated routine
        """
        try:
            # Search for relevant exercises
            query = f"{focus} exercises for {context['user_profile']['experience_level']} level"
            exercises = self.vector_store.search_exercises(query)

            if not exercises:
                logger.error(f"No exercises found for query: {query}")
                return None

            logger.info(f"Found {len(exercises)} exercises for {focus} routine")

            # Ensure we have enough unique exercises
            unique_exercises = []
            seen_titles = set()
            for exercise in exercises:
                if exercise["title"] not in seen_titles:
                    unique_exercises.append(exercise)
                    seen_titles.add(exercise["title"])
                    if len(unique_exercises) >= 10:  # Limit to 10 exercises
                        break

            logger.info(f"Using {len(unique_exercises)} unique exercises for routine")

            # Create the prompt for OpenAI
            prompt = self._create_routine_prompt(
                day=day,
                focus=focus,
                exercises=unique_exercises,
                context=context,
                include_cardio=include_cardio,
            )

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            # Parse the response
            try:
                routine_json = json.loads(response.choices[0].message.content)
                logger.info("Generated routine JSON:")
                logger.info(json.dumps(routine_json, indent=2))
                return routine_json
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {str(e)}")
                logger.error(f"Raw response: {response.choices[0].message.content}")
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
        self, name: str, description: str, context: dict, period: str
    ) -> Optional[dict]:
        """Generate a complete workout routine folder using OpenAI.

        Args:
            name: Name of the routine folder
            description: Description of the routine folder
            context: User context and preferences
            period: Time period for the routines (week or month)

        Returns:
            Dictionary containing the routine folder structure
        """
        try:
            # Get user profile from context
            user_profile = context.get("user_profile", {})
            experience_level = user_profile.get("experience_level", "beginner")
            days_per_week = user_profile.get("workout_schedule", {}).get(
                "days_per_week", 3
            )
            preferred_split = context.get("generation_preferences", {}).get(
                "split_type", "auto"
            )
            fitness_goals = user_profile.get("fitness_goals", ["General Fitness"])

            # Determine workout split and get routine configurations
            split_type, routines = RoutineFolderBuilder.determine_workout_split(
                days_per_week=days_per_week,
                experience_level=experience_level,
                preferred_split=preferred_split,
            )

            # Generate routines for each day
            generated_routines = []
            for routine in routines[
                :days_per_week
            ]:  # Only generate for the requested number of days
                # Generate routine for this day
                routine_data = self.generate_routine(
                    day=routine["day"],
                    focus=routine["focus"],
                    context=context,
                    include_cardio=routine["focus"] == "full body",
                )
                if routine_data:
                    generated_routines.append(routine_data)

            if not generated_routines:
                logger.error("Failed to generate any routines")
                return None

            # Get date range
            date_range = RoutineFolderBuilder.get_date_range(period)

            # Build the routine folder
            routine_folder = RoutineFolderBuilder.build_routine_folder(
                name=name,
                description=description,
                split_type=split_type,
                routines=generated_routines,
                period=period,
                date_range=date_range,
            )

            return routine_folder

        except Exception as e:
            logger.error(f"Error generating routine folder: {str(e)}")
            return None
