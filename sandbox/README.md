# Sandbox Environment
This directory contains a containerized sandbox environment designed for secure execution of project code and tests.

## Architecture

The system follows a "Host-to-Sandbox" execution model:
1.  **Gemini CLI**: Runs directly on the host machine.
2.  **Project Execution Sandbox**: A Docker container managed via Docker Compose that provides an isolated environment for the project's code, tests, and build processes.

## Why use a Sandbox?
- **Isolation**: Prevents the project's code or tests from making unintended changes to the host system.
- **Consistency**: Ensures a reproducible environment (Python 3.12-slim) with all necessary dependencies pre-installed.
- **Security**: Uses `gVisor` (`runsc`) for kernel-level isolation, providing a layer of protection when executing code.

## How to use the Sandbox

### Automatic Usage (Gemini CLI)
Gemini CLI is configured to automatically run all project-related commands (tests, linting, builds, etc.) inside this sandbox. It uses the following command structure:

`docker compose -f sandbox/docker-compose.yml run --rm sandbox <command>`

### Manual Usage
If you need to run a command in the sandbox manually:
```bash
docker compose -f sandbox/docker-compose.yml run --rm sandbox <your_command>
```

To start the development server with port mapping enabled:
```bash
docker compose -f sandbox/docker-compose.yml run --rm --service-ports sandbox uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

To build or rebuild the sandbox image:
```bash
docker compose -f sandbox/docker-compose.yml build
```

## Configuration
- **Runtime**: gVisor/runsc can be optionally configured in docker-compose.
- **Base Image**: `python:3.12-slim`
- **Mounts**: The project root is mounted to `/app` inside the container.
- **Dependencies**: Managed via `uv`.
