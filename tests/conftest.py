"""Global test configuration."""

import os

from cryptography.fernet import Fernet

# Mock environment variables before importing app modules
os.environ["INTERVALS_ATHLETE_ID"] = "test_athlete_id"
os.environ["INTERVALS_API_KEY"] = "test_api_key"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret"  # noqa: S105
os.environ["APP_SECRET_KEY"] = Fernet.generate_key().decode()
os.environ["LANGUAGE_MODEL"] = "gemini-flash-latest"
