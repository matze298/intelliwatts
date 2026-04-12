# Sandbox Environment (gVisor)

This directory contains a containerized sandbox environment designed for secure execution of project code and tests.

## What it is
- **Runtime**: Uses `runsc` (gVisor) for strong kernel-level isolation.
- **Base**: Python 3.12-slim based on the project's dependencies.
- **Mounts**: The project root is mounted to `/app`, ensuring the sandbox always runs the latest codebase.

## Sandbox Types
2 sandboxes are involved when running this project with a coding agent, e.g. Gemini CLI:

1.  **Gemini CLI Internal Sandbox**: Constrains the Gemini CLI itself. 
    - **Status**: Enabled by running `gemini -s`. 
    - **Purpose**: Explicitly grant permissions for file/network access.
2.  **Project execution Sandbox**: Constrains the project's code and tests.
    - **Status**: Managed by Gemini CLI automatically via Docker/gVisor.
    - **Purpose**: Runs risky code (tests, scripts) in an isolated environment using `runsc`.

## How Gemini uses the Project Sandbox
- **Orchestration**: Gemini CLI automatically manages this sandbox for project execution. You do **not** need to manually start containers before calling Gemini.
- **Prerequisite**: Ensure your Docker daemon is running on your host.
- **Execution**: Gemini uses this to run tests, validate features, and execute scripts.
- **Command**: Gemini invokes tasks using `docker compose -f sandbox/docker-compose.yml run sandbox <command>`.

## Usage
- To run a specific command in the sandbox manually:
  `docker compose -f sandbox/docker-compose.yml run sandbox <command> [args...]`
  **Note**: Do not wrap the command and arguments in a single quoted string.
- To build/rebuild the sandbox:
  `docker compose -f sandbox/docker-compose.yml build`
