"""Global test configuration."""

import os


# Mock environment variables before importing app modules
os.environ["INTERVALS_ATHLETE_ID"] = "test_athlete_id"
os.environ["INTERVALS_API_KEY"] = "test_api_key"
os.environ["LANGUAGE_MODEL"] = "gemini-flash-latest"

os.environ["APP_PASSWORD"] = "test-password"
os.environ["SESSION_SECRET"] = "test-session-secret-12345678901234567890"
os.environ["APP_ORIGIN"] = "https://testserver"
