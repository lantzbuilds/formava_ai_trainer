"""
Dashboard API routes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users/{user_id}/dashboard")
async def get_dashboard(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get dashboard data for a user.

    Requires authentication. Users can only access their own dashboard.
    """
    # Verify user can only access their own data
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own dashboard",
        )

    try:
        dashboard_data = DashboardService.get_dashboard_data(user_id)
        return dashboard_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
