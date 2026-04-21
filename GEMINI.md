## Project-Specific Instructions (IntelliWatts)

### 🐍 Python & Backend
- **Style Guide**: Adhere strictly to the **Google Python Style Guide**.
- **Linting & Formatting**: Use **Ruff** for both linting and formatting. Line length is **120**. Ruff errors are **advisory** (non-blocker) but should be resolved when possible.
- **Type Safety**: Mandatory type hints for all function signatures and complex variables.
- **Docstrings**: Use **Google-style docstrings** for all modules, classes, and functions.
- **Dependency Management**: Use **`uv`** for all dependency operations. To update dependencies, first modify `pyproject.toml`, then run **`uv lock`** to regenerate the `uv.lock` file. Use **`uv sync`** to install dependencies from the lock file. Refer to `setup.sh` for the canonical installation procedure.
- **Database Migrations**: Handle schema changes manually or via bootstrap scripts (e.g., `init_db` in `app/db.py`).
- **Imports**: ALWAYS use **absolute imports** (e.g., `from app.models.user import User`). NEVER use relative imports (e.g., `from .user import User`).

### 🧪 Testing
- **Framework**: Use **`pytest`**.
- **Structure**: Follow the **GIVEN-WHEN-THEN** pattern and clearly mark each section with comments.
- **Coverage**: Maintain high test coverage; verify with `pytest-cov`.
- **Mocking**: Mock external services (LLMs, Intervals.icu API) using `unittest.mock`.
- **Mirror Structure**: The `tests/` directory structure and file naming MUST strictly mirror the `app/` directory structure (e.g., `app/path/to/module.py` should be tested in `tests/path/to/test_module.py`).

### 🎨 Frontend & Styling
- **Framework**: **Tailwind CSS**.
- **Build**: Run `./build_tailwind.sh` after any CSS or template changes to regenerate theme-specific assets.

### 🔒 Security & Data
- **Secrets**: Never hardcode keys. Use environment variables or the encrypted `UserSecrets` model.
- **Encryption**: Use `app.security.crypto` utilities for sensitive data in the database.

### 🛠️ Workflow & Environment
- **Development Environment**: **MANDATORY**. All project-related executions (tests, builds, commands) must be performed from within the project's configured sandbox (Python 3.14).
- **Sandbox Execution**: Use `docker compose -f sandbox/docker-compose.yml run sandbox <command>` for all executions.
- **Dependency Sync**: Run `docker compose -f sandbox/docker-compose.yml run sandbox uv sync --extra dev --extra test` to ensure all tools are available.
- **Pre-commit**: Ensure pre-commit hooks are respected (managed via `prek`).
- **Commit Messages**: Use **Freeform (Descriptive)** sentences. Focus on "why" rather than just "what".
- **Documentation**: Always keep **`README.md`** updated when making changes that affect setup, usage, or features.
- **Improvement Plan**: Always keep **`docs/improvement-plan.md`** updated with your latest changes.
- **Superpowers**: NEVER commit files in the **`docs/superpowers/`** directory. These are internal development aids.

## Known Best-Practices
- **Atomic Commits**: Prefer small, focused commits.
- **Test Structure**: The `tests/` directory structure and file naming must strictly mirror the `app/` directory structure (e.g., `app/path/to/module.py` should be tested in `tests/path/to/test_module.py`).
- **Interfaces**: NEVER use bare tuples as function outputs. Always prefer well-designed, named interfaces such as `Dataclass` or `NamedTuple` to ensure clarity and type safety.
- **FastAPI Dependency Injection**: Use FastAPI's `Depends` for shared logic and DB sessions where appropriate.
- **SQLModel**: Align with SQLModel conventions for database interactions.
