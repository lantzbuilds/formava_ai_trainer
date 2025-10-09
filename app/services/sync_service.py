"""
Sync service - handles Hevy data synchronization.
Shared between Gradio and FastAPI interfaces.
"""

import logging
import threading
from typing import Any, Dict, Literal

from app.services.sync import sync_hevy_data
from app.state.sync_status import SYNC_STATUS

logger = logging.getLogger(__name__)


class SyncService:
    """Service for handling Hevy data synchronization."""

    @staticmethod
    def start_sync(
        user: Dict[str, Any], sync_type: Literal["recent", "full"] = "recent"
    ) -> Dict[str, str]:
        """
        Start a background sync of Hevy data.

        Args:
            user: User dictionary with id, username, email
            sync_type: Type of sync - "recent" (last 30 days) or "full" (all history)

        Returns:
            Dictionary with status message
        """
        try:
            if SYNC_STATUS["status"] == "syncing":
                return {
                    "status": "already_syncing",
                    "message": "Sync already in progress",
                }

            def run_sync():
                try:
                    sync_hevy_data(user, sync_type)
                    SYNC_STATUS["status"] = "complete"
                except Exception as e:
                    logger.error(f"Error syncing workouts: {e}", exc_info=True)
                    SYNC_STATUS["status"] = "error"

            SYNC_STATUS["status"] = "syncing"
            threading.Thread(target=run_sync, daemon=True).start()

            return {"status": "syncing", "message": "Sync started"}

        except Exception as e:
            logger.error(f"Error starting sync: {str(e)}", exc_info=True)
            SYNC_STATUS["status"] = "error"
            return {"status": "error", "message": f"Failed to start sync: {str(e)}"}

    @staticmethod
    def get_sync_status() -> Dict[str, str]:
        """
        Get the current sync status.

        Returns:
            Dictionary with current sync status
        """
        status = SYNC_STATUS["status"]

        status_messages = {
            "idle": "No sync in progress",
            "syncing": "Syncing workouts...",
            "complete": "Sync complete!",
            "error": "Sync failed!",
        }

        return {
            "status": status,
            "message": status_messages.get(status, "Unknown status"),
        }

    @staticmethod
    def reset_sync_status() -> None:
        """Reset sync status to idle (after completion or error)."""
        SYNC_STATUS["status"] = "idle"
