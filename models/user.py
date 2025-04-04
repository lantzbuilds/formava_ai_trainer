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


class Injury(BaseModel):
    description: str
    body_part: str
    severity: int = Field(ge=1, le=10)  # 1-10 scale
    date_injured: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None


class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: f"user_{datetime.utcnow().timestamp()}")
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

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
