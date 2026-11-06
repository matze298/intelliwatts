# IntelliWatts

IntelliWatts is a personal cycling training application. It imports workout and wellness data from [Intervals.icu](https://intervals.icu), displays performance and recovery metrics, and generates structured weekly training plans with an LLM.

[![Gatekeeper](https://github.com/matze298/intelliwatts/actions/workflows/gatekeeper.yml/badge.svg?branch=main)](https://github.com/matze298/intelliwatts/actions/workflows/gatekeeper.yml)
[![codecov](https://codecov.io/github/matze298/intelliwatts/graph/badge.svg)](https://codecov.io/github/matze298/intelliwatts)

## Application

The web application has three primary views:

| View | Route | Features |
|---|---|---|
| Plan | `/` | Long-term goals, target date, weekly hours and session limits, model selection, recovery-data inclusion, plan generation and publishing |
| Dashboard | `/dashboard` | Training load (CTL, ATL, TSB), HRV, resting heart rate, sleep, activity mix, weekly volume, power curve, intensity distribution and recent activities |
| Settings | `/settings` | Training and model preferences, including developer-mode options |

The Dashboard supports a selectable analysis window of 7–90 days. Recent activity history shows five sessions initially, with older sessions available through an expandable list. Cycling activities are displayed as **Cycling**.

The interface uses server-rendered Jinja2 templates, Tailwind CSS, the IntelliWatts stylesheet, and Chart.js. It supports desktop and mobile layouts.

## Integrations

- **Intervals.icu:** Activity, power, training-stress and wellness data, and workout publishing.
- **OpenAI:** Plan generation with configured OpenAI API credentials.
- **Google Gemini:** Plan generation with configured Gemini API credentials.

The selected model, prompt overrides and relevant training preferences are configurable through application settings. External API access requires the corresponding credentials.

## Requirements

- Python 3.14 or newer
- `uv`
- PostgreSQL
- Node.js and npm for building CSS assets
- Intervals.icu API key and athlete ID
- At least one supported LLM API key

## Configuration

Copy `.env.example` to `.env` and configure the values required for your installation. Do not commit `.env` or API tokens.

| Setting | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection URL |
| `APP_PASSWORD` | Password for the web interface |
| `SESSION_SECRET` | Random secret used to sign session cookies |
| `APP_ORIGIN` | Public HTTPS origin or `http://localhost:8000` for local development |
| `INTERVALS_API_KEY` | Intervals.icu API key |
| `INTERVALS_ATHLETE_ID` | Intervals.icu athlete ID |
| `OPENAI_API_KEY` | OpenAI credential when using OpenAI |
| `GEMINI_API_KEY` | Gemini credential when using Gemini |
| `LANGUAGE_MODEL` | Default language-model selection |
| `SESSION_COOKIE_SECURE` | Secure cookie setting; use `false` only with local HTTP |

Generate a session secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The app uses a shared password and a signed session cookie. Sessions last 12 hours. The installed instance is intended for a single athlete profile.

## Local development

```bash
./setup.sh
uv run alembic upgrade head
./run.sh
```

Open `http://localhost:8000/` and sign in with `APP_PASSWORD`.

FastAPI can also be started directly:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

A hosted instance is available at [intelliwatts.onrender.com](https://intelliwatts.onrender.com) (password required). The health endpoint is `GET /health`.

## Database

IntelliWatts stores plans, preferences and application state in PostgreSQL using SQLModel/SQLAlchemy. Alembic manages schema migrations.

```bash
uv run alembic upgrade head
```

Database backups can be created with `pg_dump` and restored with `pg_restore`. Store backups separately from the application host.

## CSS assets

Tailwind CSS assets are generated from the styles under `app/static/` and the application templates. The current web UI loads `app/static/tailwind-light.css` followed by `app/static/intelliwatts-ui.css`.

```bash
npm ci
npm run build:css
```

The generated CSS files are committed to the repository and checked by CI.

## Tests

Use a disposable PostgreSQL database or a separate test database/branch. Set `TEST_DATABASE_URL` to its connection URL.

```bash
uv sync --extra dev --extra test
uv run playwright install chromium
TEST_DATABASE_URL="postgresql://user:password@host/test_database" uv run pytest tests/
```

GitHub Actions **Gatekeeper** runs linting, unit/browser tests and a CSS-build consistency check. It does not generate or commit screenshots.

## Manual browser screenshots

A standalone Playwright utility is available at `scripts/capture_ui_screenshots.py`. It captures Planner and Dashboard at desktop and mobile widths from a running local IntelliWatts instance.

```bash
export INTELLIWATTS_SCREENSHOT_PASSWORD="your-local-app-password"
uv run python scripts/capture_ui_screenshots.py --base-url http://127.0.0.1:8000
```

Output is written to `artifacts/ui-screenshots/`, which is gitignored. Captures can contain personal training and wellness data. Agent-specific instructions are in [AGENTS.md](AGENTS.md).
