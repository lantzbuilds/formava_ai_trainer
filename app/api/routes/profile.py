"""
Profile API routes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users/{user_id}/profile")
async def get_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get user profile data (read-only for MVP).

    Requires authentication. Users can only access their own profile.
    """
    # Verify user can only access their own data
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile",
        )

    try:
        profile_data = DashboardService.get_user_profile(user_id)
        return profile_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Profile error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
