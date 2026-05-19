# Repository Guidelines

## Project Structure & Module Organization
`app/` contains the FastAPI app, with `routes/`, `services/`, `planning/`, `intervals/`, `models/`, `security/`, and `templates/`. Static assets live in `app/static/`. Tests mirror `app/` under `tests/`. Database migrations live in `migrations/versions/`; docs and examples live in `docs/`.

## Build, Test, and Development Commands
- Prefer the sandbox wrapper for project commands: `docker compose -f sandbox/docker-compose.yml run sandbox <command>`.
- `./setup.sh`: create the virtualenv, install dependencies, and set up tooling.
- `uv sync` / `uv lock`: install from the lockfile and refresh it after dependency changes.
- `uv run uvicorn app.main:app --reload`: run the app locally.
- `uv run alembic upgrade head`: apply the latest schema.
- `uv run pytest` / `uv run pytest --cov`: run tests, with coverage when needed.
- `./build_tailwind.sh`: rebuild all theme CSS files in `app/static/`.
- `docker compose -f sandbox/docker-compose.yml run sandbox uv sync --extra dev --extra test`: install sandbox tooling; `prek` may run outside the sandbox if needed.

## Coding Style & Naming Conventions
Use Python 3.14+, absolute imports, type hints, and Google-style docstrings. Ruff formats and lints; keep line length at 120, treat Ruff errors as advisory, and do not add new ignores without approval. Use `snake_case` for functions, variables, and modules, `PascalCase` for classes, and keep filenames aligned with their feature area. When dependencies change, update `pyproject.toml` first, then run `uv lock`.

## Testing Guidelines
Use `pytest`. Tests should follow GIVEN-WHEN-THEN with explicit `# GIVEN`, `# WHEN`, and `# THEN` comments. Mirror the `app/` structure in `tests/`, mock external services such as OpenAI, Gemini, and intervals.icu with `unittest.mock` or focused fixtures, and start with the narrowest relevant subset. Keep coverage high and use `pytest-cov` for broader changes.

## Commit & Pull Request Guidelines
Use short commit prefixes like `feat:`, `fix:`, and `docs:`. Keep commits small and focused, with branch names prefixed `feature/` or `fix/`, not `codex/`. PRs must stay small enough to review in one pass; split oversized work into stacked PRs. Include the change summary, migration or asset rebuild notes when relevant, screenshots for UI work, and the repository PR template. Update `README.md` and `docs/improvement-plan.md` when setup, usage, or the plan changes.

## Security & Configuration Tips
Never commit secrets. Use `.env`, environment variables, or the app’s secrets storage for keys such as `INTERVALS_API_KEY`, `OPENAI_API_KEY`, and `GEMINI_API_KEY`. Keep `app.security.crypto` for sensitive database values. For schema changes, update the model first, then the Alembic migration, then run `uv run alembic upgrade head`; the bootstrap path in `app/db.py` is also available.

## Workflow Notes
Respect pre-commit hooks. Keep diffs minimal, avoid unrelated refactors, and never commit files in `docs/superpowers/`. Prefer small, focused commits with freeform messages that explain why the change exists. Avoid bare tuples from functions; use a dataclass or `NamedTuple`. Use FastAPI `Depends` for shared logic and DB sessions, and follow SQLModel conventions for database interactions.
