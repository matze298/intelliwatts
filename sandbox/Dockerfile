FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    bindfs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_PREFERENCE=only-system
ENV PATH="/venv/bin:$PATH"

# Default command
CMD ["bash"]
