"""
Hevy Sync API routes.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter()


class SyncRequest(BaseModel):
    sync_type: Literal["recent", "full"] = "recent"


@router.post("/users/{user_id}/sync-hevy")
async def sync_hevy(
    user_id: str,
    request: SyncRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger a Hevy data sync for the user.

    Requires authentication. Users can only sync their own data.
    """
    # Verify user can only sync their own data
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only sync your own data",
        )

    try:
        # Build user dict for sync service
        user = {
            "id": user_id,
            "username": current_user["username"],
            "email": current_user.get("email", ""),
        }

        result = SyncService.start_sync(user, request.sync_type)
        return result
    except Exception as e:
        logger.error(f"Sync error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get("/users/{user_id}/sync-status")
async def get_sync_status(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get the current sync status.

    Requires authentication. Users can only check their own sync status.
    """
    # Verify user can only check their own status
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check your own sync status",
        )

    try:
        status_data = SyncService.get_sync_status()
        return status_data
    except Exception as e:
        logger.error(f"Get sync status error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
