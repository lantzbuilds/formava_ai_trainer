import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

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
            print("OpenAI API key is not configured")
            return None

        try:
            # Extract user profile information
            user_profile = context.get("user_profile", {})
            experience_level = user_profile.get("experience_level", "beginner")
            fitness_goals = user_profile.get("fitness_goals", [])
            preferred_duration = user_profile.get("preferred_duration", 60)
            active_injuries = user_profile.get("active_injuries", [])
            workout_schedule = user_profile.get("workout_schedule", [])

            # Get relevant exercises based on user's goals and experience level
            relevant_exercises = []
            try:
                vector_store = ExerciseVectorStore()

                # Get exercises based on fitness goals
                for goal in fitness_goals:
                    # Search for exercises relevant to this goal
                    exercises = vector_store.search_exercises(
                        f"exercises for {goal} goal", k=5
                    )

                    # Convert to the format we need
                    for exercise in exercises:
                        if exercise.get("name") not in [
                            e.get("name") for e in relevant_exercises
                        ]:
                            relevant_exercises.append(
                                {
                                    "title": exercise.get("name"),
                                    "exercise_template_id": exercise.get(
                                        "exercise_template_id"
                                    ),
                                    "description": exercise.get("description", ""),
                                    "muscle_groups": exercise.get("muscle_groups", []),
                                    "equipment": exercise.get("equipment", []),
                                    "difficulty": exercise.get(
                                        "difficulty", "beginner"
                                    ),
                                }
                            )

                # If no exercises found, get some general exercises
                if not relevant_exercises:
                    exercises = vector_store.search_exercises("general exercises", k=10)
                    for exercise in exercises:
                        relevant_exercises.append(
                            {
                                "title": exercise.get("name"),
                                "exercise_template_id": exercise.get(
                                    "exercise_template_id"
                                ),
                                "description": exercise.get("description", ""),
                                "muscle_groups": exercise.get("muscle_groups", []),
                                "equipment": exercise.get("equipment", []),
                                "difficulty": exercise.get("difficulty", "beginner"),
                            }
                        )

                logger.info(
                    f"Found {len(relevant_exercises)} relevant exercises for the routine"
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
            - Preferred Workout Schedule: {', '.join(workout_schedule) if workout_schedule else 'Not specified'}

            Available Exercises (you MUST use these exact exercises):
            {json.dumps(relevant_exercises, indent=2)}

            Requirements:
            1. Create a weekly routine that matches the user's preferred workout schedule
            2. Each session should be approximately {preferred_duration} minutes long
            3. Include enough exercises per session to fill the time appropriately
            4. Design a balanced program that:
               - Aligns with the user's specific fitness goals
               - Is appropriate for their experience level
               - Uses ONLY the exercises from the list above
               - Provides specific sets, reps, and intensity recommendations
               - Includes modifications for any injuries or limitations
               - Incorporates progressive overload principles
               - Includes appropriate rest periods between sets
            5. Include active recovery recommendations for non-workout days
            6. Ensure proper exercise selection and volume to fill the entire session duration

            Format your response as a JSON object with the following structure:
            {{
                "routine_description": "A detailed description of the routine's goals, considerations, and overall approach",
                "hevy_api": {{
                    "routine": {{
                        "title": "string",
                        "folder_id": null,
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
            - Each session should have enough exercises to properly fill the {preferred_duration} minute duration
            - Include appropriate rest periods between sets (typically 60-90 seconds)
            - Ensure exercises are properly balanced across muscle groups
            - Include warm-up and cool-down recommendations in the session descriptions
            - Make sure the total volume (sets × reps × weight) is appropriate for the experience level
            - The number of sessions should match the user's preferred workout schedule
            - For the hevy_api format:
              * You MUST use ONLY the exact titles and exercise_template_ids from the exercises list above
              * The title and exercise_template_id fields are REQUIRED and cannot be null
              * Set folder_id to null as we'll handle folder assignment separately
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
            print(f"OpenAI Response Content: {content}")  # Debug log

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
                        print("Missing required fields in response")
                        print(f"Response content: {content}")
                        return None

                    if not all(key in routine["hevy_api"] for key in ["routine"]):
                        print("Missing required fields in hevy_api")
                        print(f"Response content: {content}")
                        return None

                    if not all(
                        key in routine["hevy_api"]["routine"]
                        for key in ["title", "notes", "exercises"]
                    ):
                        print("Missing required fields in routine")
                        print(f"Response content: {content}")
                        return None

                    # Validate each exercise has required fields
                    for exercise in routine["hevy_api"]["routine"]["exercises"]:
                        required_fields = [
                            "title",
                            "sets",
                            "exercise_description",
                        ]
                        if not all(key in exercise for key in required_fields):
                            print(f"Missing required fields in exercise: {exercise}")
                            print(f"Required fields: {required_fields}")
                            return None

                    print(
                        f"Parsed Routine: {json.dumps(routine, indent=2)}"
                    )  # Debug log
                    return routine
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON response: {e}")
                    print(f"Response content: {content}")
                    return None
            else:
                print("Could not extract JSON from response")
                print(f"Response content: {content}")
                return None
        except Exception as e:
            print(f"Error generating routine: {str(e)}")
            return None

    def generate_routine_folder(
        self, name: str, description: str, routines: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a routine folder structure using OpenAI.

        Args:
            name: Name of the folder
            description: Description of the folder
            routines: List of routines to organize

        Returns:
            Dictionary containing the generated folder structure or None if failed
        """
        if not self.api_key:
            print("OpenAI API key is not configured")
            return None

        try:
            # Create prompt for OpenAI
            prompt = f"""
            You are an AI personal trainer. Organize the following workout routines into a logical folder structure:

            Folder Name: {name}
            Description: {description}

            Routines:
            {json.dumps(routines, indent=2)}

            Please organize these routines into a logical folder structure that:
            1. Groups routines by similar focus (e.g., strength, cardio, flexibility)
            2. Creates a progression path from beginner to advanced
            3. Separates routines by target muscle groups or body parts
            4. Provides a clear organization that makes it easy to find specific routines

            Format your response as a JSON object with the following structure:
            {{
                "name": "string",
                "description": "string",
                "subfolders": [
                    {{
                        "name": "string",
                        "description": "string",
                        "routines": ["routine_id"]
                    }}
                ]
            }}
            """

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an AI personal trainer."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            # Extract and parse response
            content = response.choices[0].message.content
            folder_structure = json.loads(content)

            return folder_structure
        except Exception as e:
            print(f"Error generating routine folder: {str(e)}")
            return None
