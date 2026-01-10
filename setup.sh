#!/usr/bin/env bash
set -euo pipefail

# Repo-root venv directory
VENV_DIR=".venv"
PYTHON_BIN="python3"

# Create or reuse virtual environment
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Using existing virtual environment in $VENV_DIR"
fi

# Activate virtual environment
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Python: $(python --version)"

# Ensure uv is available
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Installing uv into the virtual environment"
  pip install --upgrade pip
  pip install uv
fi

# Sync dependencies from uv.lock
if [ -f "uv.lock" ]; then
  echo "Syncing dependencies via uv.lock"
  uv sync --extra dev --extra test
else
  echo "No uv.lock found. Running uv sync anyway (will resolve dependencies)"
  uv sync --extra dev --extra test
fi

# Ensure pre-commit is installed
if ! command -v pre-commit >/dev/null 2>&1; then
  echo "Installing pre-commit"
  uv pip install pre-commit
fi

# Install pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
  echo "Installing pre-commit hooks"
  pre-commit install
else
  echo "WARNING: .pre-commit-config.yaml not found. Skipping hook installation."
fi

echo "Setup complete ✔"