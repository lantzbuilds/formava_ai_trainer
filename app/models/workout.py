from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class Set(BaseModel):
    index: int
    type: str  # "normal" or other types
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    distance_meters: Optional[float] = None
    duration_seconds: Optional[int] = None
    rpe: Optional[float] = None
    custom_metric: Optional[float] = None


class Exercise(BaseModel):
    index: int
    title: str
    notes: Optional[str] = None
    exercise_template_id: str
    supersets_id: int
    sets: List[Set]


class Workout(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    updated_at: datetime
    created_at: datetime
    exercises: List[Exercise]
    _rev: Optional[str] = None  # CouchDB revision ID

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
