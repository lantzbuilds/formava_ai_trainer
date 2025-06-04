import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

import openai
import requests
from dotenv import load_dotenv
from openai import OpenAI

from app.config.database import Database
from app.services.hevy_api import HevyAPI
from app.services.routine_folder_builder import RoutineFolderBuilder
from app.services.vector_store import ExerciseVectorStore
from app.utils.crypto import decrypt_api_key

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

    # def analyze_workout_form(
    #     self, exercise_name: str, description: str
    # ) -> Dict[str, Any]:
    #     """
    #     Analyze workout form based on exercise name and description.

    #     Args:
    #         exercise_name: Name of the exercise
    #         description: Description of the exercise form

    #     Returns:
    #         Analysis results
    #     """
    #     prompt = f"""
    #     I need an analysis of the following exercise form:

    #     Exercise: {exercise_name}
    #     Description: {description}

    #     Please provide feedback on:
    #     1. Proper form and technique
    #     2. Common mistakes to avoid
    #     3. Tips for improvement
    #     4. Safety considerations

    #     Format the response as a JSON object with the following structure:
    #     {{
    #         "proper_form": "Description of proper form",
    #         "common_mistakes": ["Mistake 1", "Mistake 2", ...],
    #         "improvement_tips": ["Tip 1", "Tip 2", ...],
    #         "safety_considerations": ["Consideration 1", "Consideration 2", ...]
    #     }}
    #     """

    #     try:
    #         response = self.client.chat.completions.create(
    #             model="gpt-4o",
    #             messages=[
    #                 {
    #                     "role": "system",
    #                     "content": "You are an expert personal trainer with deep knowledge of exercise form and technique.",
    #                 },
    #                 {"role": "user", "content": prompt},
    #             ],
    #             temperature=0.7,
    #             max_tokens=1000,
    #         )

    #         # Parse the response
    #         content = response.choices[0].message.content

    #         # Clean the content by removing control characters
    #         content = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", content)

    #         # Extract JSON from the response
    #         json_start = content.find("{")
    #         json_end = content.rfind("}") + 1

    #         if json_start >= 0 and json_end > json_start:
    #             json_str = content[json_start:json_end]
    #             try:
    #                 return json.loads(json_str)
    #             except json.JSONDecodeError as e:
    #                 print(f"Error parsing JSON response: {e}")
    #                 print(f"Response content: {content}")
    #                 return {
    #                     "proper_form": "Unable to analyze form",
    #                     "common_mistakes": [],
    #                     "improvement_tips": [],
    #                     "safety_considerations": [],
    #                 }
    #         else:
    #             print("Could not extract JSON from response")
    #             print(f"Response content: {content}")
    #             return {
    #                 "proper_form": "Unable to analyze form",
    #                 "common_mistakes": [],
    #                 "improvement_tips": [],
    #                 "safety_considerations": [],
    #             }
    #     except Exception as e:
    #         print(f"Error analyzing form: {e}")
    #         return {
    #             "proper_form": "Unable to analyze form",
    #             "common_mistakes": [],
    #             "improvement_tips": [],
    #             "safety_considerations": [],
    #         }

    # TODO: add workout history to prompt
    def _create_routine_prompt(
        self,
        day: str,
        focus: str,
        exercises: List[Dict[str, Any]],
        context: dict,
        include_cardio: bool,
        similar_workouts: List[Dict] = None,
    ) -> str:
        """Create the prompt for OpenAI to generate a workout routine.

        Args:
            day: Day of the week
            focus: Focus of the workout
            exercises: List of available exercises
            context: User context and preferences
            include_cardio: Whether to include cardio in the routine
            similar_workouts: List of similar workouts from user's history

        Returns:
            Formatted prompt string
        """
        user_profile = context["user_profile"]
        experience_level = user_profile["experience_level"]
        fitness_goals = user_profile["fitness_goals"]
        injuries = user_profile.get("injuries", [])
        preferred_duration = user_profile.get("preferred_workout_duration", 60)
        split_type = context.get("generation_preferences", {}).get("split_type", "auto")

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

        # Format similar workouts for the prompt
        workout_history_text = ""
        if similar_workouts:
            workout_history_text = "\n\nSimilar workouts from user's history:\n"
            for workout in similar_workouts:
                workout_history_text += f"- {workout['title']} ({workout['start_time']}): {workout['exercise_count']} exercises\n"

        # Add split type to user profile
        split_text = f"- Workout Split Type: {split_type}" if split_type else ""

        # Create the prompt
        prompt = f"""
        Create a {focus} workout routine for {day} that is appropriate for a {experience_level} level user.
        
        User Profile:
        - Experience Level: {experience_level}
        - Fitness Goals: {', '.join(fitness_goals)}
        - Active Injuries: {injury_text}
        - Preferred Workout Duration: {preferred_duration} minutes
        {split_text}
        {workout_history_text}
        
        Available Exercises:
        {json.dumps(exercises, indent=2)}
        
        Please create a workout routine that:
        1. Targets the specified muscle groups effectively
        2. Is appropriate for the user's experience level
        3. Avoids exercises that could aggravate injuries
        4. Includes appropriate rest periods
        5. Stays within the preferred workout duration
        6. Builds upon the user's previous workout patterns
        7. Follows a {split_type} split for this day (if applicable)
        {f"8. Includes at least {preferred_duration // 10} minutes of cardio, using appropriate exercises from the list above, if possible." if include_cardio else ""}
        
        Return the response in JSON format that matches the Hevy API requirements:
        {{
            "routine_description": "A detailed description of the routine's goals and approach",
            "hevy_api": {{
                "routine": {{
                    "title": "string",
                    "folder_id": null,
                    "notes": "string",
                    "exercises": [
                        {{
                            "exercise_template_id": "string (MUST match the exercise_template_id from the exercises list above)",
                            "superset_id": number or null,
                            "rest_seconds": number,
                            "notes": "string",
                            "sets": [
                                {{
                                    "type": "warmup|normal|failure|dropset",
                                    "weight_kg": number or null,
                                    "reps": number or null,
                                    "distance_meters": number or null,
                                    "duration_seconds": number or null,
                                    "custom_metric": number or null
                                }}
                            ]
                        }}
                    ]
                }}
            }}
        }}

        Important Notes:
        - You MUST use ONLY the exact exercise_template_ids from the exercises list above
        - The exercise_template_id field is REQUIRED and cannot be null
        - Set types can be: "warmup", "normal", "failure", or "dropset"
        - Include appropriate notes for both the routine and individual exercises
        - For timed exercises, use duration_seconds
        - For cardio/distance exercises, use distance_meters
        - For stair machine exercises, use custom_metric for floors/steps
        - For standard exercises, use weight_kg and reps
        - Include rest_seconds between sets (typically 60-90 seconds for strength training)
        - While we can see RPE in the user's history, we cannot include it in the generated routine
        
        Exercise Requirements:
        - Weight training exercises MUST have at least 3 sets
        - Weight training exercises MUST specify weight_kg for each set
        - Warm-up sets should be included for compound movements
        - For strength-focused exercises, use 3-5 sets of 3-6 reps
        - For hypertrophy-focused exercises, use 3-4 sets of 8-12 reps
        - For endurance-focused exercises, use 2-3 sets of 12-15+ reps
        - Cardio exercises should specify either duration_seconds or distance_meters
        - Bodyweight exercises should still specify weight_kg as 0
        
        Superset Guidelines:
        - Use supersets to pair complementary exercises (e.g., push/pull, agonist/antagonist)
        - Assign the same superset_id number to exercises that should be performed together
        - Limit supersets to 2-3 exercises to maintain intensity and form
        - Consider the user's experience level when creating supersets
        - Include appropriate rest periods between supersets
        - Add notes to explain the superset pairing and execution
        """

        return prompt

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
            # TODO: can add equipment as filter_criteria to search_exercises
            exercises = self.vector_store.search_exercises(query)

            if not exercises:
                logger.error(f"No exercises found for query: {query}")
                return None

            logger.info(f"Found {len(exercises)} exercises for {focus} routine")

            # Create a mapping of exercise_template_id to exercise name
            exercise_names = {
                ex.get("exercise_template_id")
                or ex.get("id"): ex.get("name")
                or ex.get("title")
                for ex in exercises
            }

            # Ensure we have enough unique exercises
            unique_exercises = []
            seen_names = set()
            for exercise in exercises:
                name = exercise.get("name") or exercise.get("title")
                if name and name not in seen_names:
                    unique_exercises.append(exercise)
                    seen_names.add(name)
                    if len(unique_exercises) >= 10:  # Limit to 10 exercises
                        break

            logger.info(f"Using {len(unique_exercises)} unique exercises for routine")

            # Get similar workouts from user's history
            user_id = context.get("user_id")
            if user_id:
                similar_workouts = self.vector_store.search_workout_history(
                    query=f"{focus} workout routine",
                    user_id=user_id,
                    k=3,  # Get top 3 similar workouts
                )
                logger.info(
                    f"Found {len(similar_workouts)} similar workouts in history"
                )
            else:
                similar_workouts = []
                logger.warning("No user ID provided, skipping workout history search")

            # Create the prompt for OpenAI
            prompt = self._create_routine_prompt(
                day=day,
                focus=focus,
                exercises=unique_exercises,
                context=context,
                include_cardio=include_cardio,
                similar_workouts=similar_workouts,
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

                # Add exercise names to the routine data
                if "hevy_api" in routine_json and "routine" in routine_json["hevy_api"]:
                    for exercise in routine_json["hevy_api"]["routine"]["exercises"]:
                        exercise_id = exercise.get("exercise_template_id")
                        if exercise_id in exercise_names:
                            exercise["name"] = exercise_names[exercise_id]
                        else:
                            # Fallback: try to look up in the vector store
                            exercise["name"] = (
                                self._lookup_exercise_name(exercise_id)
                                or "Unknown Exercise"
                            )
                            logger.warning(
                                f"Exercise name not found for ID {exercise_id}, using fallback."
                            )
                    # Log any exercises still missing a name
                    for exercise in routine_json["hevy_api"]["routine"]["exercises"]:
                        if "name" not in exercise:
                            logger.error(
                                f"Exercise missing name after all lookups: {exercise}"
                            )

                return routine_json
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {str(e)}")
                logger.error(f"Raw response: {response.choices[0].message.content}")
                return None

        except Exception as e:
            logger.error(f"Error generating routine: {str(e)}")
            return None

    def _lookup_exercise_name(self, exercise_id):
        """Lookup an exercise name by its template ID using the vector store."""
        exercise = self.vector_store.get_exercise_by_id(exercise_id)
        if exercise:
            return exercise.get("title") or exercise.get("name")
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
                    include_cardio=context.get("generation_preferences", {}).get(
                        "include_cardio", False
                    ),
                )
                if routine_data:
                    # Add the day and focus to the routine data
                    routine_data["day"] = routine["day"]
                    routine_data["focus"] = routine["focus"]
                    generated_routines.append(routine_data)

            if not generated_routines:
                logger.error("Failed to generate any routines")
                return None

            # Get date range
            date_range = RoutineFolderBuilder.get_date_range(period)

            # Build the routine folder using RoutineFolderBuilder
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
