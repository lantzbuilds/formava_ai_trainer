# FastAPI REST API

This FastAPI application runs alongside the Gradio interface during the migration period.

## Running the API

### Development Mode

```bash
# Using Python directly
python -m app.api.main

# Or using uvicorn
uvicorn app.api.main:app --reload --port 8000
```

### Environment Variables

- `API_PORT`: Port for the API (default: 8000)
- `ENV`: Environment (development/staging/production)
- `FRONTEND_URL`: Production frontend URL for CORS

## Endpoints

### Health Check
- `GET /`: Root endpoint with API info
- `GET /health`: Health check endpoint

### Authentication (Coming in Step 1.3)
- `POST /api/auth/login`: User login
- `POST /api/auth/register`: User registration
- `POST /api/auth/logout`: User logout
- `POST /api/auth/demo-login`: Demo account login

### Dashboard (Coming in Step 1.3)
- `GET /api/users/{user_id}/dashboard`: Get dashboard data

### Profile (Coming in Step 1.3)
- `GET /api/users/{user_id}/profile`: Get user profile (read-only)

### AI Recommendations (Coming in Step 1.3)
- `POST /api/users/{user_id}/generate-routine`: Generate AI workout routine
- `POST /api/users/{user_id}/save-to-hevy`: Save routine to Hevy

### Sync (Coming in Step 1.3)
- `POST /api/users/{user_id}/sync-hevy`: Trigger Hevy sync
- `GET /api/users/{user_id}/sync-status`: Get sync status

## Testing

```bash
# Test the health endpoint
curl http://localhost:8000/health

# Should return: {"status": "healthy"}
```

