# DevContainer Dockerfile for IntelliWatts project

ARG NODE_VERSION=20
ARG PYTHON_VERSION=3.12

FROM node:${NODE_VERSION}-slim as node_stage
FROM python:${PYTHON_VERSION}-slim as python_stage

# Install Docker and docker-compose for running the project's sandbox
# This allows running 'docker compose -f sandbox/docker-compose.yml run sandbox <command>' from within the DevContainer
RUN apt-get update && apt-get install -y --no-install-recommends 
    docker-ce 
    docker-ce-cli 
    containerd.io 
    docker-compose-plugin 
    && apt-get clean 
    && rm -rf /var/lib/apt/lists/*

# Install Node.js from the node stage
RUN apt-get update && apt-get install -y --no-install-recommends 
    ca-certificates 
    && rm -rf /var/lib/apt/lists/*
COPY --from=node_stage /usr/local/bin/node /usr/local/bin/node
COPY --from=node_stage /usr/local/bin/npm /usr/local/bin/npm

WORKDIR /app

# Copy project files
COPY . .

# The project's GEMINI.md mandates using uv for dependency management.
# We also install the gemini-cli here for convenience within the dev environment.

# Ensure gemini-cli is installed globally
RUN npm install -g @google/gemini-cli

# Install Python dependencies using uv sync as per project requirements.
RUN pip install uv
RUN uv sync

# Set default command for the container (optional, devcontainer.json overrides this)
CMD ["zsh"]
