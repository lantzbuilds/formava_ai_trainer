"""
AI Recommendations API routes.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateRoutineRequest(BaseModel):
    split_type: str = "auto"
    period: str = "week"
    include_cardio: bool = True
    title: Optional[str] = None


@router.get("/users/{user_id}/ai-recommendations/summary")
async def get_ai_recs_summary(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get summary data for the AI recommendations page.

    Requires authentication. Users can only access their own data.
    """
    # Verify user can only access their own data
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own data",
        )

    try:
        summary_data = AIService.get_ai_recs_summary(user_id)
        return summary_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"AI recs summary error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post("/users/{user_id}/generate-routine")
async def generate_routine(
    user_id: str,
    request: GenerateRoutineRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate an AI-powered workout routine for the user.

    Requires authentication. Users can only generate routines for themselves.
    """
    # Verify user can only generate for themselves
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only generate routines for yourself",
        )

    try:
        routine_folder = AIService.generate_routine(
            user_id=user_id,
            split_type=request.split_type,
            period=request.period,
            include_cardio=request.include_cardio,
            title=request.title,
        )
        return routine_folder
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Generate routine error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post("/users/{user_id}/save-to-hevy")
async def save_to_hevy(
    user_id: str,
    routine_folder: dict = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Save a generated routine to Hevy.

    Requires authentication. Users can only save routines for themselves.
    """
    # Verify user can only save for themselves
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only save routines for yourself",
        )

    try:
        success = AIService.save_routine_to_hevy(user_id, routine_folder)
        return {"success": success, "message": "Routine saved to Hevy successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Save to Hevy error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
