"""
Authentication service - handles login, registration, and demo account logic.
Shared between Gradio and FastAPI interfaces.
"""

import logging
import threading
from typing import Any, Dict, Optional, Tuple

from app.config.database import Database
from app.models.user import UserProfile
from app.services.sync import sync_hevy_data

logger = logging.getLogger(__name__)
db = Database()


class AuthError(Exception):
    """Custom exception for authentication errors."""

    pass


class AuthService:
    """Service for handling authentication operations."""

    @staticmethod
    def login(username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user with username and password.

        Args:
            username: User's username
            password: User's password

        Returns:
            Dictionary containing user info: {"id": str, "username": str, "email": str}

        Raises:
            AuthError: If authentication fails
        """
        try:
            logger.info(f"Attempting login for username: {username}")

            # Validate input
            if not username or not password:
                logger.warning("Login attempt with missing credentials")
                raise AuthError("Please enter both username and password.")

            # Get user from database
            user_doc = db.get_user_by_username(username)
            if not user_doc:
                logger.warning(f"User not found: {username}")
                raise AuthError(
                    "Invalid username or password. Please check your credentials and try again."
                )

            # Create UserProfile instance from document
            user_profile = UserProfile.from_dict(user_doc)

            # Verify password
            if not user_profile.verify_password(password):
                logger.warning(f"Invalid password for user: {username}")
                raise AuthError(
                    "Invalid username or password. Please check your credentials and try again."
                )

            # Return user object for state management
            user = {
                "id": user_doc["_id"],
                "username": user_doc["username"],
                "email": user_doc["email"],
            }
            logger.info(f"Login successful for user: {username}")

            # Start background sync of Hevy data
            threading.Thread(target=sync_hevy_data, args=(user,), daemon=True).start()

            return user

        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Login failed: {str(e)}", exc_info=True)
            raise AuthError(
                "An unexpected error occurred during login. Please try again."
            )

    @staticmethod
    def demo_login() -> Dict[str, Any]:
        """
        Login with the demo account.

        Returns:
            Dictionary containing user info: {"id": str, "username": str, "email": str}

        Raises:
            AuthError: If demo account cannot be found
        """
        try:
            logger.info("Attempting demo account login")

            # Get demo user from database
            demo_user_id = "075ce2423576c5d4a0d8f883aa4ebf7e"
            user_doc = db.get_document(demo_user_id)

            # Check if it's a valid user document
            if not user_doc or user_doc.get("type") != "user_profile":
                logger.warning(f"Demo user not found with ID: {demo_user_id}")
                # Try to find demo user by username as fallback
                user_doc = db.get_user_by_username("demo_user")

            if not user_doc:
                logger.error("Demo user not found in database!")
                raise AuthError("Demo account not found. Please contact support.")

            # Return user object for state management
            user = {
                "id": user_doc["_id"],
                "username": user_doc["username"],
                "email": user_doc["email"],
            }
            logger.info(f"Demo login successful, user: {user['username']}")

            # Sync Hevy data for demo user (full sync to get all historical workouts)
            threading.Thread(
                target=sync_hevy_data, args=(user, "full"), daemon=True
            ).start()

            return user

        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Demo login failed: {str(e)}", exc_info=True)
            raise AuthError("An unexpected error occurred. Please try again.")

    @staticmethod
    def register(
        username: str,
        email: str,
        password: str,
        age: Optional[int] = None,
        sex: Optional[str] = None,
        height_cm: Optional[float] = None,
        weight_kg: Optional[float] = None,
        experience_level: str = "beginner",
        preferred_units: str = "imperial",
    ) -> Dict[str, Any]:
        """
        Register a new user account.

        Args:
            username: Desired username
            email: User's email address
            password: User's password
            age: User's age (optional)
            sex: User's sex (optional)
            height_cm: User's height in cm (optional)
            weight_kg: User's weight in kg (optional)
            experience_level: Fitness experience level (default: "beginner")
            preferred_units: Preferred unit system (default: "imperial")

        Returns:
            Dictionary containing user info: {"id": str, "username": str, "email": str}

        Raises:
            AuthError: If registration fails
        """
        try:
            logger.info(f"Attempting to register user: {username}")

            # Validate required fields
            if not username or not email or not password:
                raise AuthError("Username, email, and password are required.")

            # Check if username already exists
            existing_user = db.get_user_by_username(username)
            if existing_user:
                logger.warning(f"Username already exists: {username}")
                raise AuthError(
                    "Username already exists. Please choose a different username."
                )

            # Create user profile
            user_profile = UserProfile(
                username=username,
                email=email,
                age=age,
                sex=sex,
                height_cm=height_cm,
                weight_kg=weight_kg,
                experience_level=experience_level,
                preferred_units=preferred_units,
            )

            # Set password (will be hashed)
            user_profile.set_password(password)

            # Save to database
            user_dict = user_profile.model_dump()
            user_dict["type"] = "user_profile"

            saved_doc = db.save_document(user_dict)
            user_id = saved_doc["id"]

            logger.info(f"User registered successfully: {username} (ID: {user_id})")

            # Return user object
            return {
                "id": user_id,
                "username": username,
                "email": email,
            }

        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}", exc_info=True)
            raise AuthError(
                "An unexpected error occurred during registration. Please try again."
            )

    @staticmethod
    def logout(user: Dict[str, Any]) -> None:
        """
        Logout a user (cleanup operations if needed).

        Args:
            user: User dictionary
        """
        logger.info(f"User logged out: {user.get('username', 'unknown')}")
        # In a stateless API, logout is mostly client-side (clearing tokens)
        # Add any server-side cleanup here if needed
