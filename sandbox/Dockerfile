FROM python:3.12-slim

# Install system dependencies including Node.js (for Tailwind CSS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv for high-performance dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Configure environment for uv and Python
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Pre-install Python dependencies into /opt/venv
COPY pyproject.toml uv.lock ./

# Pre-install dependencies including tests to ensure tools like pytest are available
RUN uv sync --frozen --no-install-project --no-dev --extra test

# Add the virtual environment to the PATH
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["uv", "run"]
