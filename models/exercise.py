"""
Exercise model for the AI Personal Trainer application.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExerciseMuscle(BaseModel):
    """Muscle group targeted by an exercise."""

    id: str
    name: str
    is_primary: bool = False


class ExerciseEquipment(BaseModel):
    """Equipment used for an exercise."""

    id: str
    name: str


class ExerciseCategory(BaseModel):
    """Category of an exercise."""

    id: str
    name: str


class Exercise(BaseModel):
    """
    Exercise model representing an exercise from the Hevy API.
    """

    id: str
    name: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    muscle_groups: List[ExerciseMuscle] = Field(default_factory=list)
    equipment: List[ExerciseEquipment] = Field(default_factory=list)
    categories: List[ExerciseCategory] = Field(default_factory=list)
    difficulty: Optional[str] = None  # beginner, intermediate, advanced
    is_custom: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    embedding: Optional[List[float]] = None  # Store the OpenAI embedding

    @classmethod
    def from_hevy_api(cls, data: Dict[str, Any]) -> "Exercise":
        """
        Create an Exercise instance from Hevy API data.

        Args:
            data: Raw exercise data from Hevy API

        Returns:
            Exercise instance
        """
        # Extract muscle groups
        muscle_groups = []
        if "muscle_groups" in data:
            for muscle in data["muscle_groups"]:
                muscle_groups.append(
                    ExerciseMuscle(
                        id=muscle.get("id", ""),
                        name=muscle.get("name", ""),
                        is_primary=muscle.get("is_primary", False),
                    )
                )

        # Extract equipment
        equipment = []
        if "equipment" in data:
            for item in data["equipment"]:
                equipment.append(
                    ExerciseEquipment(id=item.get("id", ""), name=item.get("name", ""))
                )

        # Extract categories
        categories = []
        if "categories" in data:
            for category in data["categories"]:
                categories.append(
                    ExerciseCategory(
                        id=category.get("id", ""), name=category.get("name", "")
                    )
                )

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            instructions=data.get("instructions", ""),
            muscle_groups=muscle_groups,
            equipment=equipment,
            categories=categories,
            difficulty=data.get("difficulty", ""),
            is_custom=data.get("is_custom", False),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            embedding=data.get("embedding", None),  # Include embedding if it exists
        )


class ExerciseList(BaseModel):
    """
    Model for a list of exercises.
    """

    exercises: List[Exercise] = Field(default_factory=list)
    updated_at: Optional[str] = None

    @classmethod
    def from_hevy_api(
        cls, data: List[Dict[str, Any]], updated_at: Optional[str] = None
    ) -> "ExerciseList":
        """
        Create an ExerciseList instance from Hevy API data.

        Args:
            data: Raw exercise list data from Hevy API
            updated_at: Timestamp when the data was updated

        Returns:
            ExerciseList instance
        """
        exercises = [Exercise.from_hevy_api(exercise) for exercise in data]
        return cls(exercises=exercises, updated_at=updated_at)
