from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

import bcrypt
from pydantic import BaseModel, EmailStr, Field, SecretStr


class InjurySeverity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class Injury(BaseModel):
    description: str
    body_part: str
    severity: InjurySeverity
    date_injured: datetime
    is_active: bool = True
    notes: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


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


class UserProfile(BaseModel):
    id: str = Field(
        default_factory=lambda: f"user_{datetime.now(timezone.utc).timestamp()}"
    )
    type: str = "user_profile"  # Add this field to identify user documents
    username: str
    email: EmailStr
    password_hash: str  # Will store bcrypt hash
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    injuries: List[Injury] = Field(default_factory=list)

    # Additional Information
    preferred_workout_days: List[str] = []  # e.g., ["Monday", "Wednesday", "Friday"]
    preferred_workout_time: Optional[str] = (
        None  # e.g., "morning", "afternoon", "evening"
    )
    experience_level: str  # beginner, intermediate, advanced
    notes: Optional[str] = None

    # CouchDB specific
    _rev: Optional[str] = None

    def model_dump(self, *args, **kwargs):
        """Override model_dump method to ensure datetime serialization."""
        d = super().model_dump(*args, **kwargs)
        # Convert any remaining datetime objects to ISO format strings
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, datetime):
                        d[key][i] = item.isoformat()
                    elif isinstance(item, dict):
                        for k, v in item.items():
                            if isinstance(v, datetime):
                                d[key][i][k] = v.isoformat()
        return d

    @classmethod
    def create_user(
        cls,
        username: str,
        email: str,
        password: str,
        height_cm: float,
        weight_kg: float,
        sex: Sex,
        age: int,
        fitness_goals: List[FitnessGoal],
        experience_level: str,
        hevy_api_key: Optional[str] = None,
        injuries: Optional[List[dict]] = None,
    ) -> "UserProfile":
        """Create a new user with a hashed password."""
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)

        return cls(
            username=username,
            email=email,
            password_hash=password_hash.decode("utf-8"),  # Store as string in DB
            height_cm=height_cm,
            weight_kg=weight_kg,
            sex=sex,
            age=age,
            fitness_goals=fitness_goals,
            experience_level=experience_level,
            hevy_api_key=hevy_api_key,
            injuries=[Injury(**injury) for injury in (injuries or [])],
        )

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        """Convert to dictionary with proper datetime serialization."""
        return self.model_dump()

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
