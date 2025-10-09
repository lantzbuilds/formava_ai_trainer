"""
Main FastAPI application entry point.
Runs on port 8000 alongside the Gradio app (port 7860).
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


# Define lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("FastAPI application starting up...")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")

    yield

    # Shutdown
    logger.info("FastAPI application shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Formava AI Trainer API",
    description="REST API for the AI Personal Trainer application",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
# In development, allow requests from the NextJS frontend (port 3000)
# In production, this should be restricted to your actual domain
origins = [
    "http://localhost:3000",  # NextJS dev server
    "http://127.0.0.1:3000",
    "http://localhost:7860",  # Gradio app (if it needs to call the API)
    "http://127.0.0.1:7860",
]

# Add production origins if specified
if production_origin := os.getenv("FRONTEND_URL"):
    origins.append(production_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "message": "Formava AI Trainer API",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers (will be added in next steps)
# from app.api.routes import auth, dashboard, profile, ai_recommendations, sync
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
# app.include_router(profile.router, prefix="/api", tags=["Profile"])
# app.include_router(ai_recommendations.router, prefix="/api", tags=["AI Recommendations"])
# app.include_router(sync.router, prefix="/api", tags=["Sync"])


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", 8000))
    env = os.getenv("ENV", "development")
    is_production = env in ["production", "staging"]

    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=not is_production,  # Enable auto-reload in development
        log_level="info",
    )
