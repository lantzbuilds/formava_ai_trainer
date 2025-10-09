"""
Authentication API routes.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.auth import create_access_token
from app.services.auth_service import AuthError, AuthService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    age: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    experience_level: str = "beginner"
    preferred_units: str = "imperial"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate a user with username and password.

    Returns JWT token and user info on success.
    """
    try:
        user = AuthService.login(request.username, request.password)

        # Create JWT token
        access_token = create_access_token(
            data={"sub": user["id"], "username": user["username"]}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user account.

    Returns JWT token and user info on success.
    """
    try:
        user = AuthService.register(
            username=request.username,
            email=request.email,
            password=request.password,
            age=request.age,
            sex=request.sex,
            height_cm=request.height_cm,
            weight_kg=request.weight_kg,
            experience_level=request.experience_level,
            preferred_units=request.preferred_units,
        )

        # Create JWT token
        access_token = create_access_token(
            data={"sub": user["id"], "username": user["username"]}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post("/demo-login", response_model=AuthResponse)
async def demo_login():
    """
    Login with the demo account.

    Returns JWT token and user info on success.
    """
    try:
        user = AuthService.demo_login()

        # Create JWT token
        access_token = create_access_token(
            data={"sub": user["id"], "username": user["username"]}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Demo login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    In a JWT-based system, logout is primarily client-side (deleting the token).
    This endpoint is provided for API completeness.
    """
    return {"message": "Logged out successfully"}
