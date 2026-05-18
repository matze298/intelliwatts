# Project-Specific Instructions for IntelliWatts

These instructions apply to Codex work in this repository.

## Python and Backend
- Follow the Google Python Style Guide.
- Use Ruff for linting and formatting. Line length is 120.
- Treat Ruff errors as advisory, but fix them when practical.
- Do not add new ignores to `pyproject.toml` or any other config file without explicit user approval.
- Avoid module-level Ruff ignores. Prefer fixing the lint issue or scoping any temporary ignore to the smallest possible line.
- Add type hints to all function signatures and to complex variables.
- Use Google-style docstrings for all modules, classes, and functions.
- Use `uv` for dependency management.
- When dependencies change, update `pyproject.toml` first, then run `uv lock`.
- Use `uv sync` to install from the lock file.
- Follow `setup.sh` for the canonical installation procedure.
- Handle database schema changes manually or through bootstrap scripts such as `init_db` in `app/db.py`.
- Use absolute imports only. Do not use relative imports.

## Testing
- Use `pytest`.
- Every test function must follow GIVEN-WHEN-THEN and mark the sections with explicit comments:
  - `# GIVEN`
  - `# WHEN`
  - `# THEN`
- Keep test coverage high and verify with `pytest-cov`.
- Mock external services such as LLMs and the Intervals.icu API with `unittest.mock`.
- Mirror the `app/` structure in `tests/` exactly. For example:
  - `app/path/to/module.py` -> `tests/path/to/test_module.py`
  - `app/planning/providers/wellness.py` -> `tests/planning/providers/test_wellness.py`
- When behavior changes, add or update focused tests for the affected path before broadening scope.
- Run the narrowest relevant test subset first, then expand only if the change crosses module boundaries.

## Frontend and Styling
- Use Tailwind CSS.
- Run `./build_tailwind.sh` after any CSS or template changes so theme assets stay current.

## Security and Data
- Never hardcode secrets.
- Use environment variables or the encrypted `UserSecrets` model.
- Use `app.security.crypto` utilities for sensitive data stored in the database.

## Workflow and Environment
- Run all project commands from the project sandbox environment.
- Use `docker compose -f sandbox/docker-compose.yml run sandbox <command>` for project execution.
- Pre-commit hooks via `prek` may be run outside the sandbox if needed.
- Run `docker compose -f sandbox/docker-compose.yml run sandbox uv sync --extra dev --extra test` when tooling needs to be installed.
- Respect pre-commit hooks.
- Use branch names prefixed with `feature/` for feature work and `bugfix/` for fixes. Do not create branches prefixed with `codex/`.
- Use freeform, descriptive commit messages that explain why the change exists.
- Keep `README.md` updated when setup, usage, or features change.
- Keep `docs/improvement-plan.md` updated with the latest changes.
- Never commit files in `docs/superpowers/`.
- Keep diffs minimal and avoid unrelated refactors unless they are necessary to complete the task safely.

## Database Changes
- Prefer the existing bootstrap or migration path already used by the repo.
- For schema changes, update the SQLModel definitions first, then generate or edit the migration, then apply it.
- Use the repository's documented Alembic commands when migrations are required:
  - `uv run alembic revision --autogenerate -m "describe_change"`
  - `uv run alembic upgrade head`

## Review Checklist
- Update `README.md` when setup, usage, or features change.
- Update `docs/improvement-plan.md` when implementation work changes the project plan.
- Confirm no files under `docs/superpowers/` are committed.
- When opening a pull request, always use the repository's pull-request template.

## Known Best Practices
- Prefer small, focused commits.
- Never return bare tuples from functions; use a dataclass or `NamedTuple` instead.
- Use FastAPI `Depends` for shared logic and DB sessions when appropriate.
- Follow SQLModel conventions for database interactions.
