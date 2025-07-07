# Environment Configuration Guide

## Overview

The application supports multiple environments with different configuration files:
- **`.env.local`** - Local development overrides
- **`.env.production`** - Production environment (Render production)
- **`.env.staging`** - Staging environment (Render staging) 
- **`.env`** - Default fallback environment

## Current Environment Loading Logic

The application currently loads environment files in this order:
1. `.env.local` (if exists) - Local development overrides
2. `.env.production` (if `ENV=production`) OR `.env` (default)

## Recommended: Add Staging Support

You should create a `.env.staging` file and update the configuration logic to support staging environments.

### Step 1: Create `.env.staging`

Create a `.env.staging` file in your project root with these variables:

```bash
# Environment identifier
ENV=staging

# CouchDB Configuration (from Render dashboard)
COUCHDB_URL=your_staging_couchdb_internal_url
COUCHDB_USER=your_staging_couchdb_user
COUCHDB_PASSWORD=your_staging_couchdb_password
COUCHDB_DB=ai_trainer_staging

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Hevy API Configuration (optional)
HEVY_API_KEY=your_hevy_api_key

# Gradio Configuration for staging
GRADIO_SHARE=false
GRADIO_DEBUG=false
GRADIO_ANALYTICS_ENABLED=false
GRADIO_MAX_THREADS=40

# Security Configuration
GRADIO_ALLOW_FLAGGING=never
GRADIO_SHOW_ERROR=false
```

### Step 2: Update Configuration Logic

The current logic in `app/config/config.py` needs to be updated to support staging:

```python
# Current logic (lines 10-20)
env_files = [
    ".env.local",  # Local development overrides
    (
        ".env.production" if os.getenv("ENV") == "production" else ".env"
    ),  # Default env files
]

# Recommended updated logic:
env_files = [
    ".env.local",  # Local development overrides
    (
        ".env.production" if os.getenv("ENV") == "production" 
        else ".env.staging" if os.getenv("ENV") == "staging"
        else ".env"
    ),  # Environment-specific files
]
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENV` | Environment identifier | `staging`, `production`, `development` |
| `COUCHDB_URL` | CouchDB connection URL | `https://your-couchdb.render.com` |
| `COUCHDB_USER` | CouchDB username | `admin` |
| `COUCHDB_PASSWORD` | CouchDB password | `your-secure-password` |
| `COUCHDB_DB` | Database name | `ai_trainer_staging` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HEVY_API_KEY` | Hevy API key for sync | None |
| `GRADIO_SHARE` | Enable public sharing | `false` |
| `GRADIO_DEBUG` | Enable debug mode | `false` |
| `GRADIO_ANALYTICS_ENABLED` | Enable analytics | `false` |
| `GRADIO_MAX_THREADS` | Max concurrent threads | `40` |

## Render Environment Variables

When deploying to Render, you should set these environment variables in the Render dashboard:

### For Staging Service:
1. Go to your staging service in Render dashboard
2. Navigate to "Environment" tab
3. Add these variables:
   - `ENV=staging`
   - `COUCHDB_URL` (internal URL from your CouchDB service)
   - `COUCHDB_USER` (from your CouchDB service)
   - `COUCHDB_PASSWORD` (from your CouchDB service)
   - `COUCHDB_DB=ai_trainer_staging`
   - `OPENAI_API_KEY` (your OpenAI key)

### For Production Service:
1. Go to your production service in Render dashboard
2. Navigate to "Environment" tab
3. Add these variables:
   - `ENV=production`
   - `COUCHDB_URL` (internal URL from your CouchDB service)
   - `COUCHDB_USER` (from your CouchDB service)
   - `COUCHDB_PASSWORD` (from your CouchDB service)
   - `COUCHDB_DB=ai_trainer_production`
   - `OPENAI_API_KEY` (your OpenAI key)

## Database Naming Convention

Use different database names for each environment:
- **Local**: `ai_trainer` or `ai_trainer_dev`
- **Staging**: `ai_trainer_staging`
- **Production**: `ai_trainer_production`

This ensures complete data isolation between environments.

## Security Best Practices

1. **Never commit `.env.*` files** to version control
2. **Use different passwords** for each environment
3. **Use separate databases** for each environment
4. **Rotate API keys** regularly
5. **Use internal URLs** for service-to-service communication on Render

## Running the Seeding Script

For staging environment:
```bash
ENV=staging python seed_staging_data.py
```

The script will automatically load the `.env.staging` file and connect to your staging database.

## Troubleshooting

### Common Issues:

1. **Environment not loading**: Check that `ENV` variable is set correctly
2. **Database connection fails**: Verify CouchDB URL and credentials
3. **Seeding script fails**: Ensure staging database exists and is accessible
4. **API errors**: Check that OpenAI API key is valid and has credits

### Debug Environment Loading:

The application logs which environment files it's loading. Check the logs for:
```
Loading environment from .env.staging
```

If you don't see this, the environment detection isn't working correctly. 