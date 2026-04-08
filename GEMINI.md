## Project-Specific Instructions (IntelliWatts)

### 🐍 Python & Backend
- **Style Guide**: Adhere strictly to the **Google Python Style Guide**.
- **Linting & Formatting**: Use **Ruff** for both linting and formatting. Line length is **120**. Ruff errors are **advisory** (non-blocker) but should be resolved when possible.
- **Type Safety**: Mandatory type hints for all function signatures and complex variables.
- **Docstrings**: Use **Google-style docstrings** for all modules, classes, and functions.
- **Dependency Management**: Use **`uv`** for all dependency operations. Update `pyproject.toml` and sync `uv.lock` accordingly.
- **Database Migrations**: Handle schema changes manually or via bootstrap scripts (e.g., `init_db` in `app/db.py`).

### 🧪 Testing
- **Framework**: Use **`pytest`**.
- **Structure**: Follow the **GIVEN-WHEN-THEN** pattern in test docstrings or comments.
- **Coverage**: Maintain high test coverage; verify with `pytest-cov`.
- **Mocking**: Mock external services (LLMs, Intervals.icu API) using `unittest.mock`.

### 🎨 Frontend & Styling
- **Framework**: **Tailwind CSS**.
- **Themes**: Support both "Retro90s" and "Minimalistic" themes.
- **Build**: Run `./build_tailwind.sh` after any CSS or template changes to regenerate theme-specific assets.

### 🔒 Security & Data
- **Secrets**: Never hardcode keys. Use environment variables or the encrypted `UserSecrets` model.
- **Encryption**: Use `app.security.crypto` utilities for sensitive data in the database.

### 🛠️ Workflow & Environment
- **Sandbox**: **MANDATORY**. All project-related executions (tests, builds, commands) must run inside the Docker sandbox:
  `docker compose -f sandbox/docker-compose.yml run sandbox <command>`
- **Pre-commit**: Ensure pre-commit hooks are respected (managed via `prek`).
- **Commit Messages**: Use **Freeform (Descriptive)** sentences. Focus on "why" rather than just "what".
- **Documentation**: Always keep **`README.md`** updated when making changes that affect setup, usage, or features.

## Known Best-Practices
- **Atomic Commits**: Prefer small, focused commits.
- **FastAPI Dependency Injection**: Use FastAPI's `Depends` for shared logic and DB sessions where appropriate.
- **SQLModel**: Align with SQLModel conventions for database interactions.
