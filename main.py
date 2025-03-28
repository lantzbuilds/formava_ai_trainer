import json
import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class WorkoutTrainer:
    def __init__(self):
        self.workout_app_api_key = os.getenv("WORKOUT_APP_API_KEY")
        self.workout_app_api_url = os.getenv("WORKOUT_APP_API_URL")

    def fetch_workout_history(self) -> Dict[str, Any]:
        """Fetch workout history from the weight training app."""
        headers = {
            "Authorization": f"Bearer {self.workout_app_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                f"{self.workout_app_api_url}/workout-history", headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workout history: {e}")
            raise

    def generate_workout_plan(
        self, workout_history: Dict[str, Any], fitness_goals: str
    ) -> Dict[str, Any]:
        """Generate a personalized workout plan using ChatGPT."""
        prompt = f"""
        Based on the following workout history and fitness goals, create a personalized workout routine.
        Return the response in JSON format that matches the weight training app's API requirements.

        Workout History:
        {json.dumps(workout_history, indent=2)}

        Fitness Goals:
        {fitness_goals}

        Please create a detailed workout plan that:
        1. Builds upon previous progress
        2. Addresses the user's fitness goals
        3. Follows proper exercise progression
        4. Includes appropriate rest periods
        5. Maintains proper form and safety

        Return the response in JSON format.
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert personal trainer creating personalized workout routines.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            # Parse the response and ensure it's valid JSON
            workout_plan = json.loads(response.choices[0].message.content)
            return workout_plan
        except Exception as e:
            print(f"Error generating workout plan: {e}")
            raise

    def upload_workout_plan(self, workout_plan: Dict[str, Any]) -> bool:
        """Upload the generated workout plan to the weight training app."""
        headers = {
            "Authorization": f"Bearer {self.workout_app_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{self.workout_app_api_url}/workout-plans",
                headers=headers,
                json=workout_plan,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error uploading workout plan: {e}")
            return False


def main():
    trainer = WorkoutTrainer()

    try:
        # Fetch workout history
        print("Fetching workout history...")
        workout_history = trainer.fetch_workout_history()

        # Get fitness goals from user
        fitness_goals = input("Please enter your fitness goals: ")

        # Generate personalized workout plan
        print("Generating personalized workout plan...")
        workout_plan = trainer.generate_workout_plan(workout_history, fitness_goals)

        # Upload the new workout plan
        print("Uploading new workout plan...")
        if trainer.upload_workout_plan(workout_plan):
            print("Success! Your new workout plan has been uploaded.")
        else:
            print("Failed to upload the workout plan.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
