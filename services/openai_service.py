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

    def get_workout_recommendations(self, context: Dict[str, Any]) -> str:
        """
        Get workout recommendations from OpenAI based on user profile and workout history.

        Args:
            context: Context including user profile, recent workouts, and available exercises

        Returns:
            String containing the recommendations
        """
        if not self.api_key:
            print("OpenAI API key is not configured")
            return (
                "OpenAI API key is not configured. Please set it in the Profile page."
            )

        try:
            # Extract user profile information
            user_profile = context.get("user_profile", {})
            experience_level = user_profile.get("experience_level", "beginner")
            fitness_goals = user_profile.get("fitness_goals", [])
            preferred_duration = user_profile.get("preferred_workout_duration", 60)
            active_injuries = user_profile.get("injuries", [])

            # Get cardio option
            cardio_option = context.get("cardio_option", "Include in workout routines")

            # Create prompt for OpenAI
            prompt = f"""
            You are an expert personal trainer with deep knowledge of exercise science and workout programming.

            Create personalized workout recommendations based on the following information:

            User Profile:
            - Experience Level: {experience_level}
            - Fitness Goals: {', '.join([g.get('value', '') for g in fitness_goals])}
            - Preferred Session Duration: {preferred_duration} minutes
            - Medical Concerns: {', '.join([i.get('description', '') for i in active_injuries if i.get('is_active', False)]) if active_injuries else 'None'}

            Recent Workout History:
            {json.dumps(context.get('recent_workouts', []), indent=2)}

            Available Exercises:
            {json.dumps(context.get('available_exercises', []), indent=2)}

            Cardio Option: {cardio_option}

            Design a comprehensive workout plan that:
            1. Aligns with the user's specific fitness goals
            2. Is appropriate for their experience level
            3. Uses exercises from the available exercises list
            4. Provides specific sets, reps, and intensity recommendations
            5. Includes modifications for any injuries or limitations
            6. Fits within the user's preferred workout duration
            7. Incorporates progressive overload principles
            8. Includes appropriate rest periods and recovery strategies
            """

            # Add specific instructions based on cardio option
            if cardio_option == "Recommend separately":
                prompt += """
                
                Format your response as a JSON object with the following structure:
                {
                    "workout_routine": "Detailed workout routine with exercises, sets, reps, etc.",
                    "cardio_recommendations": "Detailed cardio recommendations including frequency, duration, intensity, and types of cardio"
                }
                
                Make sure to provide comprehensive cardio recommendations that complement the workout routine.
                """
            else:
                prompt += """
                
                Format your response as a detailed workout plan that includes both strength training and cardio recommendations.
                """

            # Call OpenAI API
            response = openai.ChatCompletion.create(
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

            # Extract and return response
            content = response.choices[0].message.content

            # If cardio option is "Recommend separately", try to parse as JSON
            if cardio_option == "Recommend separately":
                try:
                    # Try to parse as JSON
                    recommendations = json.loads(content)
                    return recommendations
                except json.JSONDecodeError:
                    # If not valid JSON, return as is
                    return content

            return content
        except Exception as e:
            print(f"Error getting workout recommendations: {str(e)}")
            return f"Error getting workout recommendations: {str(e)}"

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
        
        The recommendations should be appropriate for the user's experience level and fitness goals, and should take into account any injuries or limitations.
        """

        try:
            response = openai.ChatCompletion.create(
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
                return {"workouts": []}
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return {"workouts": []}

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
            response = openai.ChatCompletion.create(
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

            # Determine equipment availability
            equipment = "full gym"  # default
            available_exercises = context.get("available_exercises", [])
            equipment_list = []
            for exercise in available_exercises:
                for eq in exercise.get("equipment", []):
                    if eq not in equipment_list:
                        equipment_list.append(eq)

            if (
                "barbell" in equipment_list
                or "dumbbell" in equipment_list
                or "machine" in equipment_list
            ):
                equipment = "full gym"
            elif "dumbbell" in equipment_list or "resistance band" in equipment_list:
                equipment = "home"
            elif not equipment_list or all(eq == "bodyweight" for eq in equipment_list):
                equipment = "bodyweight"

            # Create prompt for OpenAI
            prompt = f"""
            You are an expert personal trainer with deep knowledge of exercise science and workout programming.

            Create a personalized workout routine based on the following information:

            User Profile:
            - Experience Level: {experience_level}
            - Fitness Goals: {', '.join(fitness_goals)}
            - Available Equipment: {equipment}
            - Medical Concerns: {', '.join(active_injuries) if active_injuries else 'None'}
            - Preferred Session Duration: {preferred_duration} minutes

            Available Exercises:
            {json.dumps(available_exercises, indent=2)}

            Design a comprehensive workout routine that:
            1. Aligns with the user's specific fitness goals
            2. Is appropriate for their experience level
            3. Uses exercises from the available exercises list
            4. Provides specific sets, reps, and intensity recommendations
            5. Includes modifications for any injuries or limitations
            6. Fits within the user's preferred workout duration
            7. Incorporates progressive overload principles
            8. Includes appropriate rest periods and recovery strategies

            Format your response as a JSON object with the following structure:
            {{
                "name": "string",
                "description": "string",
                "weeks": [
                    {{
                        "week_number": number,
                        "rpe": number,
                        "days": [
                            {{
                                "day_number": number,
                                "focus": "string",
                                "exercises": [
                                    {{
                                        "exercise_id": "string",
                                        "name": "string",
                                        "sets": number,
                                        "reps": "string",
                                        "rpe": number,
                                        "notes": "string",
                                        "modifications": ["string"]
                                    }}
                                ],
                                "cardio": {{
                                    "type": "string",
                                    "duration": "string",
                                    "intensity": "string"
                                }}
                            }}
                        ],
                        "deload_guidance": "string"
                    }}
                ],
                "estimated_duration": number,
                "difficulty": "string",
                "target_muscle_groups": ["string"],
                "equipment_needed": ["string"]
            }}
            """

            # Call OpenAI API
            response = openai.ChatCompletion.create(
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
            response = openai.ChatCompletion.create(
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
