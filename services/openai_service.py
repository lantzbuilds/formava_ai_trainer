import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI

from services.vector_store import ExerciseVectorStore

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


class OpenAIService:
    """Service for interacting with OpenAI API to generate workout recommendations."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=self.api_key)
        self.vector_store = ExerciseVectorStore()

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
        self, name: str, description: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a workout routine using OpenAI based on user's fitness goals and preferences.

        Args:
            name: Name of the routine
            description: Description of the routine
            context: Context including user profile and available exercises

        Returns:
            Dictionary containing the generated routine or None if failed
        """
        if not self.api_key:
            logger.error("OpenAI API key is not configured")
            return None

        try:
            # Extract user profile information
            user_profile = context.get("user_profile", {})
            experience_level = user_profile.get("experience_level", "beginner")
            fitness_goals = user_profile.get("fitness_goals", [])
            preferred_duration = user_profile.get("preferred_duration", 60)
            active_injuries = user_profile.get("active_injuries", [])
            workout_schedule = user_profile.get("workout_schedule", [])
            folder_id = context.get("folder_id")

            # Get relevant exercises based on user's goals and experience level
            relevant_exercises = []
            try:
                vector_store = ExerciseVectorStore()

                # Get exercises based on fitness goals and focus
                focus = description.split("workout")[0].strip().lower()
                search_query = f"{focus} exercises for {experience_level} level"

                # Search for exercises relevant to this focus
                exercises = vector_store.search_exercises(
                    search_query, k=20, filter_criteria={"difficulty": experience_level}
                )

                # Convert to the format we need
                for exercise in exercises:
                    if exercise.get("name") not in [
                        e.get("name") for e in relevant_exercises
                    ]:
                        relevant_exercises.append(
                            {
                                "title": exercise.get("name"),
                                "exercise_template_id": exercise.get("id"),
                                "description": exercise.get("description", ""),
                                "muscle_groups": exercise.get("muscle_groups", []),
                                "equipment": exercise.get("equipment", []),
                                "difficulty": exercise.get("difficulty", "beginner"),
                            }
                        )

                # If no exercises found, get some general exercises
                if not relevant_exercises:
                    exercises = vector_store.search_exercises(
                        f"general {focus} exercises",
                        k=20,
                        filter_criteria={"difficulty": experience_level},
                    )
                    for exercise in exercises:
                        relevant_exercises.append(
                            {
                                "title": exercise.get("name"),
                                "exercise_template_id": exercise.get("id"),
                                "description": exercise.get("description", ""),
                                "muscle_groups": exercise.get("muscle_groups", []),
                                "equipment": exercise.get("equipment", []),
                                "difficulty": exercise.get("difficulty", "beginner"),
                            }
                        )

                logger.info(
                    f"Found {len(relevant_exercises)} relevant exercises for {focus} routine"
                )

            except Exception as e:
                logger.error(f"Error getting relevant exercises: {str(e)}")
                return None

            # Create prompt for OpenAI
            prompt = f"""
            You are an expert personal trainer with deep knowledge of exercise science and workout programming. Your response must be a valid JSON object with no additional text before or after. The JSON must include 'routine_description' and 'hevy_api' fields.

            Create a personalized workout routine based on the following information:

            User Profile:
            - Experience Level: {experience_level}
            - Fitness Goals: {', '.join(fitness_goals)}
            - Medical Concerns: {', '.join(active_injuries) if active_injuries else 'None'}
            - Preferred Session Duration: {preferred_duration} minutes
            - Focus: {focus}
            - Folder ID: {folder_id}

            Available Exercises (you MUST use these exact exercises):
            {json.dumps(relevant_exercises, indent=2)}

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
            4. Include warm-up and cool-down recommendations
            5. Ensure proper exercise selection and volume to fill the entire session duration

            Format your response as a JSON object with the following structure:
            {{
                "routine_description": "A detailed description of the routine's goals, considerations, and overall approach",
                "hevy_api": {{
                    "routine": {{
                        "title": "string",
                        "folder_id": "{folder_id}",
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
              * Set folder_id to "{folder_id}" as this routine belongs to a specific folder
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
                    routine["hevy_api"]["routine"]["folder_id"] = folder_id

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
        self,
        name: str,
        description: str,
        context: Dict[str, Any],
        period: Literal["week", "month"] = "week",
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a routine folder with multiple workout routines based on popular splits.

        Args:
            name: Name of the routine folder
            description: Description of the routine folder
            context: Context including user profile and available exercises
            period: Time period for the routine ("week" or "month")

        Returns:
            Dictionary containing the generated routine folder or None if failed
        """
        try:
            # Extract user profile information
            user_profile = context.get("user_profile", {})
            experience_level = user_profile.get("experience_level", "beginner")
            fitness_goals = user_profile.get("fitness_goals", [])
            preferred_duration = user_profile.get("preferred_duration", 60)
            workout_schedule = user_profile.get("workout_schedule", [])
            days_per_week = len(workout_schedule)

            # Get date range and create folder title
            date_range = self._get_date_range(period)
            folder_title = f"{name} - {date_range}"

            # First, create the routine folder via HevyAPI
            folder_data = {"routine_folder": {"title": folder_title}}

            try:
                response = requests.post(
                    "https://api.hevyapp.com/v1/routine_folder",
                    headers={
                        "Authorization": f"Bearer {os.getenv('HEVY_API_KEY')}",
                        "Content-Type": "application/json",
                    },
                    json=folder_data,
                )
                response.raise_for_status()
                folder_response = response.json()

                # Extract folder ID from response
                folder_id = folder_response.get("id")
                if not folder_id:
                    logger.error("Failed to get folder ID from HevyAPI response")
                    return None

                logger.info(f"Created routine folder with ID: {folder_id}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error creating routine folder via HevyAPI: {str(e)}")
                return None

            # Determine appropriate split based on days per week
            if days_per_week == 3:
                # Full Body or Upper/Lower split
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
                # Upper/Lower split
                split_type = "upper_lower"
                routines = [
                    {"day": "Monday", "focus": "Upper Body"},
                    {"day": "Tuesday", "focus": "Lower Body"},
                    {"day": "Thursday", "focus": "Upper Body"},
                    {"day": "Friday", "focus": "Lower Body"},
                ]
            elif days_per_week >= 5:
                # Push/Pull/Legs split
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

            # Generate individual routines for each day
            generated_routines = []
            for routine in routines:
                # Add folder_id to the context for the routine generation
                routine_context = context.copy()
                routine_context["folder_id"] = folder_id

                day_routine = self.generate_routine(
                    name=f"{routine['day']} {routine['focus']}",
                    description=f"{routine['focus']} workout for {routine['day']}",
                    context=routine_context,
                )
                if day_routine:
                    # Update the routine's folder_id
                    day_routine["hevy_api"]["routine"]["folder_id"] = folder_id
                    generated_routines.append(day_routine)

            if not generated_routines:
                logger.error("Failed to generate any routines")
                return None

            # Create the routine folder structure
            routine_folder = {
                "name": folder_title,
                "description": description,
                "split_type": split_type,
                "days_per_week": days_per_week,
                "period": period,
                "date_range": date_range,
                "folder_id": folder_id,
                "routines": generated_routines,
            }

            return routine_folder

        except Exception as e:
            logger.error(f"Error generating routine folder: {str(e)}")
            return None
