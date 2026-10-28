"""Global test configuration."""

import os
import secrets

# Mock environment variables before importing app modules
os.environ["INTERVALS_ATHLETE_ID"] = "test_athlete_id"
os.environ["INTERVALS_API_KEY"] = "test_api_key"
os.environ["LANGUAGE_MODEL"] = "gemini-flash-latest"

os.environ["APP_PASSWORD"] = secrets.token_urlsafe(32)
os.environ["SESSION_SECRET"] = secrets.token_urlsafe(32)
os.environ["APP_ORIGIN"] = "https://testserver"
