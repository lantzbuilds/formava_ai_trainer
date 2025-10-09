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
- `JWT_SECRET_KEY`: Secret key for JWT token generation (required for production)

## Endpoints

### Health Check
- `GET /`: Root endpoint with API info
- `GET /health`: Health check endpoint

### Authentication
- `POST /api/auth/login`: User login with username/password
  - Request: `{"username": "...", "password": "..."}`
  - Response: `{"access_token": "...", "token_type": "bearer", "user": {...}}`
  
- `POST /api/auth/register`: User registration
  - Request: `{"username": "...", "email": "...", "password": "...", ...}`
  - Response: `{"access_token": "...", "token_type": "bearer", "user": {...}}`
  
- `POST /api/auth/demo-login`: Demo account login
  - Response: `{"access_token": "...", "token_type": "bearer", "user": {...}}`
  
- `POST /api/auth/logout`: User logout (client-side cleanup)
  - Response: `{"message": "Logged out successfully"}`

### Dashboard (Protected)
- `GET /api/users/{user_id}/dashboard`: Get dashboard data
  - Headers: `Authorization: Bearer <token>`
  - Response: Contains workout stats, goals, injuries, etc.

### Profile (Protected, Read-only)
- `GET /api/users/{user_id}/profile`: Get user profile
  - Headers: `Authorization: Bearer <token>`
  - Response: User profile data (sanitized)

### AI Recommendations (Protected)
- `GET /api/users/{user_id}/ai-recommendations/summary`: Get AI recs page summary
  - Headers: `Authorization: Bearer <token>`
  - Response: Profile, workout, and exercise summaries
  
- `POST /api/users/{user_id}/generate-routine`: Generate AI workout routine
  - Headers: `Authorization: Bearer <token>`
  - Request: `{"split_type": "auto", "period": "week", "include_cardio": true, "title": "..."}`
  - Response: Generated routine folder with workouts
  
- `POST /api/users/{user_id}/save-to-hevy`: Save routine to Hevy
  - Headers: `Authorization: Bearer <token>`
  - Request: Routine folder object
  - Response: `{"success": true, "message": "..."}`

### Sync (Protected)
- `POST /api/users/{user_id}/sync-hevy`: Trigger Hevy sync
  - Headers: `Authorization: Bearer <token>`
  - Request: `{"sync_type": "recent"}` or `{"sync_type": "full"}`
  - Response: `{"status": "...", "message": "..."}`
  
- `GET /api/users/{user_id}/sync-status`: Get sync status
  - Headers: `Authorization: Bearer <token>`
  - Response: `{"status": "...", "message": "..."}`

## Testing

```bash
# Test the health endpoint
curl http://localhost:8000/health
# Should return: {"status": "healthy"}

# Test demo login
curl -X POST http://localhost:8000/api/auth/demo-login
# Returns: {"access_token": "...", "token_type": "bearer", "user": {...}}

# Test protected endpoint (replace TOKEN with actual token from login)
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/users/USER_ID/dashboard

# Or use the interactive API docs
# Visit http://localhost:8000/docs for Swagger UI
# Visit http://localhost:8000/redoc for ReDoc
```

