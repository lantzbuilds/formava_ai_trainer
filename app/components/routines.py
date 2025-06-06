"""
Routines page for the AI Personal Trainer application.
This page allows users to view their existing workout routines.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import streamlit as st
from config.database import Database
from models.user import UserProfile
from pydantic import BaseModel
from services.hevy_api import HevyAPI
from services.openai_service import OpenAIService

# Configure logging
logger = logging.getLogger(__name__)

# Initialize services
db = Database()
openai_service = OpenAIService()


class ExerciseInRoutine(BaseModel):
    """Model for an exercise in a routine."""

    exercise_id: str
    title: str
    sets: int
    reps: Optional[str] = None
    rpe: Optional[float] = None
    notes: Optional[str] = None
    modifications: Optional[List[str]] = None


class CardioInRoutine(BaseModel):
    """Model for cardio in a routine."""

    type: str
    duration: str
    intensity: str


class DayInRoutine(BaseModel):
    """Model for a day in a routine."""

    day_number: int
    focus: str
    exercises: List[ExerciseInRoutine]
    cardio: Optional[CardioInRoutine] = None


class WeekInRoutine(BaseModel):
    """Model for a week in a routine."""

    week_number: int
    rpe: float
    days: List[DayInRoutine]
    deload_guidance: Optional[str] = None


class Routine(BaseModel):
    """Model for a workout routine."""

    name: str
    description: str
    weeks: List[WeekInRoutine]
    estimated_duration: int  # in minutes
    difficulty: str  # beginner, intermediate, advanced
    target_muscle_groups: List[str]
    equipment_needed: List[str]


def routines_page():
    """Display the routines page."""
    st.title("Workout Routines")

    # Check if user is logged in
    if "user_id" not in st.session_state:
        st.warning("Please log in to view your routines.")
        return

    # Get user document from database
    user_doc = db.get_document(st.session_state.user_id)
    if not user_doc:
        st.error("User profile not found")
        return

    # Create UserProfile instance
    user = UserProfile(**user_doc)

    # Check if Hevy API key is configured
    if not user.hevy_api_key:
        st.warning("Hevy API key is not configured")
        st.write("Please configure your Hevy API key in the Profile page first.")
        return

    # Initialize Hevy API
    hevy_api = HevyAPI(user.hevy_api_key)

    # Get routines from Hevy
    routines = hevy_api.get_routines()

    if not routines:
        st.info(
            "You don't have any routines yet. Generate a routine from the AI Recommendations page."
        )
    else:
        # Display routines
        for routine in routines:
            with st.expander(f"{routine.get('name', 'Unnamed Routine')}"):
                st.write(
                    f"**Description:** {routine.get('description', 'No description')}"
                )

                # Check if routine has the new format with weeks
                if "weeks" in routine and routine["weeks"]:
                    # Display weeks
                    for week in routine["weeks"]:
                        st.subheader(
                            f"Week {week.get('week_number', '?')} - RPE {week.get('rpe', '?')}"
                        )

                        # Display days
                        for day in week.get("days", []):
                            st.write(
                                f"**Day {day.get('day_number', '?')} - {day.get('focus', 'Unknown Focus')}**"
                            )

                            # Display exercises
                            if "exercises" in day and day["exercises"]:
                                for exercise in day["exercises"]:
                                    st.write(
                                        f"- {exercise.get('title', 'Unknown Exercise')}"
                                    )
                                    if "sets" in exercise and "reps" in exercise:
                                        st.write(
                                            f"  Sets: {exercise['sets']}, Reps: {exercise['reps']}, RPE: {exercise.get('rpe', '?')}"
                                        )

                                    # Display modifications if any
                                    if (
                                        "modifications" in exercise
                                        and exercise["modifications"]
                                    ):
                                        st.write("  **Modifications:**")
                                        for mod in exercise["modifications"]:
                                            st.write(f"  - {mod}")

                            # Display cardio if any
                            if "cardio" in day and day["cardio"]:
                                cardio = day["cardio"]
                                st.write(
                                    f"**Cardio:** {cardio.get('type', 'Unknown')} - {cardio.get('duration', '?')} at {cardio.get('intensity', '?')} intensity"
                                )

                        # Display deload guidance if any
                        if "deload_guidance" in week and week["deload_guidance"]:
                            st.write(f"**Deload Guidance:** {week['deload_guidance']}")
                else:
                    # Display exercises in the old format
                    if "exercises" in routine and routine["exercises"]:
                        st.write("**Exercises:**")
                        for exercise in routine["exercises"]:
                            st.write(f"- {exercise.get('title', 'Unknown Exercise')}")
                            if "sets" in exercise and "reps" in exercise:
                                st.write(
                                    f"  Sets: {exercise['sets']}, Reps: {exercise['reps']}"
                                )
                            elif "sets" in exercise and "duration" in exercise:
                                st.write(
                                    f"  Sets: {exercise['sets']}, Duration: {exercise['duration']} seconds"
                                )

                # Display estimated duration
                if "estimated_duration" in routine:
                    st.write(
                        f"**Estimated Duration:** {routine['estimated_duration']} minutes"
                    )

                # Display difficulty
                if "difficulty" in routine:
                    st.write(f"**Difficulty:** {routine['difficulty']}")

                # Display target muscle groups
                if (
                    "target_muscle_groups" in routine
                    and routine["target_muscle_groups"]
                ):
                    st.write("**Target Muscle Groups:**")
                    for muscle in routine["target_muscle_groups"]:
                        st.write(f"- {muscle}")

                # Display equipment needed
                if "equipment_needed" in routine and routine["equipment_needed"]:
                    st.write("**Equipment Needed:**")
                    for equipment in routine["equipment_needed"]:
                        st.write(f"- {equipment}")

                # Button to start workout from this routine
                if st.button("Start Workout", key=f"start_{routine.get('id', '')}"):
                    st.session_state.current_routine = routine
                    st.session_state.page = "workout"
                    st.experimental_rerun()
