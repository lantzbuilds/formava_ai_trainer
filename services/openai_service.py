import json
import os
from typing import Any, Dict, List, Optional

import openai
from dotenv import load_dotenv

load_dotenv()


class OpenAIService:
    """Service for interacting with OpenAI API to generate workout recommendations."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        openai.api_key = self.api_key

    def generate_workout_recommendation(
        self,
        user_profile: Dict[str, Any],
        recent_workouts: List[Dict[str, Any]],
        num_workouts: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized workout recommendations based on user profile and workout history.

        Args:
            user_profile: User profile dictionary
            recent_workouts: List of recent workout dictionaries
            num_workouts: Number of workout recommendations to generate

        Returns:
            List of workout recommendation dictionaries
        """
        # Prepare user profile information
        profile_info = {
            "age": user_profile.get("age"),
            "sex": user_profile.get("sex"),
            "height_cm": user_profile.get("height_cm"),
            "weight_kg": user_profile.get("weight_kg"),
            "fitness_goals": user_profile.get("fitness_goals", []),
            "experience_level": user_profile.get("experience_level"),
            "injuries": user_profile.get("injuries", []),
        }

        # Prepare workout history
        workout_history = []
        for workout in recent_workouts[:5]:  # Use last 5 workouts
            workout_history.append(
                {
                    "title": workout.get("title"),
                    "date": workout.get("start_time"),
                    "exercises": [
                        {
                            "name": exercise.get("title"),
                            "sets": len(exercise.get("sets", [])),
                            "reps": (
                                exercise.get("sets", [{}])[0].get("reps")
                                if exercise.get("sets")
                                else None
                            ),
                            "weight": (
                                exercise.get("sets", [{}])[0].get("weight_kg")
                                if exercise.get("sets")
                                else None
                            ),
                        }
                        for exercise in workout.get("exercises", [])
                    ],
                }
            )

        # Create the prompt
        prompt = f"""
        I need a personalized workout recommendation based on the following user profile and workout history:
        
        User Profile:
        {json.dumps(profile_info, indent=2)}
        
        Recent Workout History:
        {json.dumps(workout_history, indent=2)}
        
        Please generate {num_workouts} workout recommendations in the following JSON format:
        {{
            "workouts": [
                {{
                    "title": "Workout Title",
                    "description": "Brief description of the workout",
                    "exercises": [
                        {{
                            "name": "Exercise Name",
                            "sets": 3,
                            "reps": 10,
                            "weight": "80% of 1RM",
                            "notes": "Form tips or variations"
                        }}
                    ]
                }}
            ]
        }}
        
        The recommendations should:
        1. Align with the user's fitness goals
        2. Be appropriate for their experience level
        3. Account for any injuries or limitations
        4. Provide progression from their recent workouts
        5. Include a mix of compound and isolation exercises
        """

        try:
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert personal trainer and fitness coach.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            # Parse the response
            content = response.choices[0].message.content

            # Extract JSON from the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                recommendations = json.loads(json_str)
                return recommendations.get("workouts", [])
            else:
                print("Could not extract JSON from OpenAI response")
                return []

        except Exception as e:
            print(f"Error generating workout recommendations: {e}")
            return []

    def analyze_workout_form(
        self, exercise_name: str, description: str
    ) -> Dict[str, Any]:
        """
        Analyze workout form based on exercise description.

        Args:
            exercise_name: Name of the exercise
            description: Description of how the exercise was performed

        Returns:
            Dictionary with form analysis and recommendations
        """
        prompt = f"""
        Analyze the following exercise performance and provide form feedback:
        
        Exercise: {exercise_name}
        Description: {description}
        
        Please provide feedback in the following JSON format:
        {{
            "form_analysis": "Detailed analysis of the form",
            "correct_form": "Description of correct form",
            "common_mistakes": ["List of common mistakes"],
            "recommendations": ["List of recommendations for improvement"]
        }}
        """

        try:
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert personal trainer specializing in exercise form.",
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
                print("Could not extract JSON from OpenAI response")
                return {
                    "form_analysis": "Unable to analyze form",
                    "correct_form": "Please consult a fitness professional",
                    "common_mistakes": [],
                    "recommendations": [],
                }

        except Exception as e:
            print(f"Error analyzing workout form: {e}")
            return {
                "form_analysis": "Error analyzing form",
                "correct_form": "Please consult a fitness professional",
                "common_mistakes": [],
                "recommendations": [],
            }
