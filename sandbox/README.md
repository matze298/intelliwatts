# Secure Sandbox Environment

This directory contains the configuration for a secure, isolated execution environment used by AI agents for all code analysis, testing, and execution tasks.

## Why a Sandbox?

To ensure maximum safety and reproducibility, we execute code within a **gVisor-isolated** container. This provides:
- **Kernel-level Isolation**: Uses `runsc` to filter system calls, protecting the host machine from potentially untrusted code or dependencies.
- **Environment Parity**: Precisely mirrors the project's Python 3.12 environment, ensuring that tests and analysis are consistent across all sessions.
- **Dependency Isolation**: The sandbox uses its own isolated virtual environment (`/venv` inside the container) to prevent interference with your local `.venv`.

## How it Works

The sandbox is built on a `python:3.12-slim` image and managed via Docker Compose.

### Key Components
- **gVisor (`runsc`)**: The container runtime that provides the security boundary.
- **Isolated Venv**: The virtual environment is stored in a Docker named volume (`venv`) and mounted to `/venv` inside the container.
- **UV**: Used for high-speed, reliable dependency management.

## Usage

All project-related commands should be proxied through the sandbox.

### 1. Sync Dependencies
Ensure the sandbox environment is up to date with your `uv.lock`:
```bash
docker compose -f sandbox/docker-compose.yml run sandbox uv sync --extra dev --extra test
```

### 2. Run Tests
```bash
docker compose -f sandbox/docker-compose.yml run sandbox pytest
```

### 3. Arbitrary Commands
```bash
docker compose -f sandbox/docker-compose.yml run sandbox <your-command>
```

## Troubleshooting

### Permissions & Mounts
The sandbox uses a named volume for the virtual environment to avoid common filesystem issues (like symlink resolution or permission denied errors) often encountered when using gVisor with Windows/WSL2 host mounts. If the environment becomes corrupted, you can reset it by removing the volume:
```bash
docker compose -f sandbox/docker-compose.yml down -v
```
