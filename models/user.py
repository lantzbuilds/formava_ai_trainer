from datetime import datetime
from enum import Enum
from typing import List, Optional

import bcrypt
from pydantic import BaseModel, EmailStr, Field, SecretStr


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class FitnessGoal(str, Enum):
    STRENGTH = "strength"
    MUSCLE_GAIN = "muscle_gain"
    WEIGHT_LOSS = "weight_loss"
    ENDURANCE = "endurance"
    FLEXIBILITY = "flexibility"
    GENERAL_FITNESS = "general_fitness"
    SPORTS_PERFORMANCE = "sports_performance"
    REHABILITATION = "rehabilitation"


class InjurySeverity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class Injury:
    def __init__(
        self,
        description: str,
        body_part: str,
        severity: InjurySeverity,
        date_injured: datetime,
        is_active: bool = True,
        notes: Optional[str] = None,
    ):
        self.description = description
        self.body_part = body_part
        self.severity = severity
        self.date_injured = date_injured
        self.is_active = is_active
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "body_part": self.body_part,
            "severity": self.severity.value,
            "date_injured": self.date_injured.isoformat(),
            "is_active": self.is_active,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Injury":
        return cls(
            description=data["description"],
            body_part=data["body_part"],
            severity=InjurySeverity(data["severity"]),
            date_injured=datetime.fromisoformat(data["date_injured"]),
            is_active=data["is_active"],
            notes=data.get("notes"),
        )


class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: f"user_{datetime.utcnow().timestamp()}")
    type: str = "user_profile"  # Add this field to identify user documents
    username: str
    email: EmailStr
    password_hash: str  # Will store bcrypt hash
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Hevy API Integration
    hevy_api_key: Optional[str] = None
    hevy_api_key_updated_at: Optional[datetime] = None

    # Physical Characteristics
    height_cm: float
    weight_kg: float
    sex: Sex
    age: int

    # Fitness Information
    fitness_goals: List[FitnessGoal] = []
    injuries: List[Injury] = []

    # Additional Information
    preferred_workout_days: List[str] = []  # e.g., ["Monday", "Wednesday", "Friday"]
    preferred_workout_time: Optional[str] = (
        None  # e.g., "morning", "afternoon", "evening"
    )
    experience_level: str  # beginner, intermediate, advanced
    notes: Optional[str] = None

    # CouchDB specific
    _rev: Optional[str] = None

    @classmethod
    def create_user(
        cls, username: str, email: str, password: str, **kwargs
    ) -> "UserProfile":
        """Create a new user with a hashed password."""
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)

        # Create the user profile with the hashed password
        return cls(
            username=username,
            email=email,
            password_hash=password_hash.decode("utf-8"),  # Store as string in DB
            **kwargs,
        )

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "injuries": [injury.to_dict() for injury in self.injuries],
            "hevy_api_key": self.hevy_api_key,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        return cls(
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            injuries=[
                Injury.from_dict(injury_data)
                for injury_data in data.get("injuries", [])
            ],
            hevy_api_key=data.get("hevy_api_key"),
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
