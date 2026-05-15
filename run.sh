#!/usr/bin/env bash
set -euo pipefail

# Repo-root venv directory
VENV_DIR=".venv"

# Activate virtual environment
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
else
  echo "Virtual environment not found. Please run ./setup.sh first."
  exit 1
fi

echo "Starting Uvicorn server..."
# Run the application using uvicorn
# Assuming the app instance is in app/main.py
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
