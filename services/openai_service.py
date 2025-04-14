import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class OpenAIService:
    """Service for interacting with OpenAI API to generate workout recommendations."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=self.api_key)

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
                model="gpt-4",
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

            # Extract JSON from the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            else:
                print("Could not extract JSON from response")
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

            # Get target muscle groups from fitness goals
            target_muscle_groups = set()
            for goal in fitness_goals:
                if goal == "strength":
                    target_muscle_groups.update(
                        ["chest", "back", "legs", "shoulders", "arms"]
                    )
                elif goal == "endurance":
                    target_muscle_groups.update(["legs", "core"])
                elif goal == "flexibility":
                    target_muscle_groups.update(["core", "back", "legs"])
                elif goal == "weight_loss":
                    target_muscle_groups.update(
                        ["chest", "back", "legs", "shoulders", "arms", "core"]
                    )

            # Get relevant exercises using vector store
            from services.vector_store import ExerciseVectorStore

            vector_store = ExerciseVectorStore()

            relevant_exercises = []
            for muscle_group in target_muscle_groups:
                exercises = vector_store.get_exercises_by_muscle_group(
                    muscle_group=muscle_group, difficulty=experience_level, k=10
                )
                relevant_exercises.extend(exercises)

            # Remove duplicates and limit to most relevant
            seen_ids = set()
            unique_exercises = []
            for exercise in relevant_exercises:
                if exercise["id"] not in seen_ids:
                    seen_ids.add(exercise["id"])
                    unique_exercises.append(exercise)

            # Limit to 50 most relevant exercises
            relevant_exercises = sorted(
                unique_exercises,
                key=lambda x: x.get("similarity_score", 0),
                reverse=True,
            )[:50]

            # Create prompt for OpenAI
            prompt = f"""
            You are an expert personal trainer with deep knowledge of exercise science and workout programming.

            Create a personalized workout routine based on the following information:

            User Profile:
            - Experience Level: {experience_level}
            - Fitness Goals: {', '.join(fitness_goals)}
            - Medical Concerns: {', '.join(active_injuries) if active_injuries else 'None'}
            - Preferred Session Duration: {preferred_duration} minutes
            - Preferred Workout Schedule: {', '.join(workout_schedule) if workout_schedule else 'Not specified'}

            Available Exercises (most relevant to your goals):
            {json.dumps(relevant_exercises, indent=2)}

            Requirements:
            1. Create a weekly routine that matches the user's preferred workout schedule
            2. Each session should be approximately {preferred_duration} minutes long
            3. Include enough exercises per session to fill the time appropriately
            4. Design a balanced program that:
               - Aligns with the user's specific fitness goals
               - Is appropriate for their experience level
               - Uses exercises from the available exercises list
               - Provides specific sets, reps, and intensity recommendations
               - Includes modifications for any injuries or limitations
               - Incorporates progressive overload principles
               - Includes appropriate rest periods between sets
            5. Include active recovery recommendations for non-workout days
            6. Ensure proper exercise selection and volume to fill the entire session duration

            Format your response as a JSON object with the following structure:
            {{
                "human_readable": {{
                    "title": "string",
                    "description": "string",
                    "warm_up": {{
                        "duration_minutes": number,
                        "exercises": [
                            {{
                                "name": "string",
                                "duration": "string",
                                "notes": "string"
                            }}
                        ]
                    }},
                    "strength_training": {{
                        "duration_minutes": number,
                        "exercises": [
                            {{
                                "name": "string",
                                "sets": number,
                                "reps": number,
                                "rest_time": "string",
                                "notes": "string"
                            }}
                        ]
                    }},
                    "cardio": {{
                        "duration_minutes": number,
                        "exercises": [
                            {{
                                "name": "string",
                                "duration": "string",
                                "intensity": "string",
                                "notes": "string"
                            }}
                        ]
                    }},
                    "cool_down": {{
                        "duration_minutes": number,
                        "exercises": [
                            {{
                                "name": "string",
                                "duration": "string",
                                "notes": "string"
                            }}
                        ]
                    }}
                }},
                "hevy_api": {{
                    "title": "string",
                    "description": "string",
                    "sessions": [
                        {{
                            "title": "string",
                            "duration_minutes": number,
                            "exercises": [
                                {{
                                    "title": "string",
                                    "notes": "string",
                                    "sets": [
                                        {{
                                            "reps": number,
                                            "weight_kg": number,
                                            "rest_seconds": number
                                        }}
                                    ]
                                }}
                            ]
                        }}
                    ],
                    "rest_days": [
                        {{
                            "title": "string",
                            "description": "string"
                        }}
                    ]
                }}
            }}

            Important Notes:
            - Each session should have enough exercises to properly fill the {preferred_duration} minute duration
            - Include appropriate rest periods between sets (typically 60-90 seconds)
            - Ensure exercises are properly balanced across muscle groups
            - Include warm-up and cool-down recommendations in the session descriptions
            - Make sure the total volume (sets × reps × weight) is appropriate for the experience level
            - The number of sessions should match the user's preferred workout schedule
            - For the human_readable format, include detailed notes and explanations for each exercise
            - For the hevy_api format, ensure the structure matches the Hevy API specifications exactly
            - The human_readable format should be a detailed, well-formatted text that explains the reasoning behind each exercise and recommendation
            - Ensure consistency between formats:
              * Use the same title and description in both formats
              * For strength exercises, include the same number of sets in both formats
              * For cardio exercises, convert duration strings to appropriate rest_seconds in the Hevy format
              * Maintain the same exercise order and structure in both formats
            """

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert personal trainer with deep knowledge of exercise science and workout programming.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            # Extract and parse response
            content = response.choices[0].message.content
            routine = json.loads(content)

            # Print the JSON version for development
            print("\nGenerated Routine (JSON format):")
            print(json.dumps(routine["hevy_api"], indent=2))
            print("\n")

            # Add name and description from parameters to both formats
            routine["hevy_api"]["name"] = name
            routine["hevy_api"]["description"] = description
            routine["human_readable"]["title"] = name
            routine["human_readable"]["description"] = description

            return routine

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
                model="gpt-4",
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
