from datetime import datetime
from enum import Enum
from typing import List, Optional

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
    id: str
    username: str
    email: EmailStr
    password_hash: SecretStr
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Hevy API Integration
    hevy_api_key: Optional[SecretStr] = None
    hevy_api_key_updated_at: Optional[datetime] = None

    # Physical Characteristics
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    sex: Optional[Sex] = None
    age: Optional[int] = Field(None, ge=13, le=120)

    # Fitness Information
    fitness_goals: List[FitnessGoal] = []
    injuries: List[Injury] = []

    # Additional Information
    preferred_workout_days: List[str] = []  # e.g., ["Monday", "Wednesday", "Friday"]
    preferred_workout_time: Optional[str] = (
        None  # e.g., "morning", "afternoon", "evening"
    )
    experience_level: Optional[str] = (
        None  # e.g., "beginner", "intermediate", "advanced"
    )
    notes: Optional[str] = None

    # CouchDB specific
    _rev: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
