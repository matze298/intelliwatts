<p align="center">
  <img src="app/static/intelliwatts-logo.webp" alt="IntelliWatts — road cyclist with brain and lightning wheels" width="280">
</p>

# IntelliWatts

**IntelliWatts** is a personal, cycling-focused training coach that brings together performance analytics, recovery signals, and AI-generated training plans. It reads workout and wellness data from [Intervals.icu](https://intervals.icu), lets you set longer-term goals and weekly limits, and generates structured workouts with OpenAI, Groq, or Google Gemini.

[![Gatekeeper](https://github.com/matze298/intelliwatts/actions/workflows/gatekeeper.yml/badge.svg?branch=main)](https://github.com/matze298/intelliwatts/actions/workflows/gatekeeper.yml)
[![codecov](https://codecov.io/github/matze298/intelliwatts/graph/badge.svg)](https://codecov.io/github/matze298/intelliwatts)

**Web app:** [intelliwatts.onrender.com](https://intelliwatts.onrender.com) (password required) · **Health check:** [GET /health](https://intelliwatts.onrender.com/health)

## Features

### Training planner

- **Long-term goal:** Define the main training objective and target date.
- **Planning horizon:** View the long-term plan and select the week to work on.
- **Weekly limits:** Set available training hours and the maximum number of planned sessions.
- **Recovery context:** Choose whether readiness and wellness signals are included in plan generation.
- **Model selection:** Select a configured OpenAI, Groq, or Gemini model.
- **Weekly workout generation:** Create a structured weekly plan based on the goal, selected week, constraints, and available context.
- **Review, update, and publish:** Inspect the generated plan, request an update, and publish the selected workout to Intervals.icu.

### Performance dashboard

The Dashboard contains the training analysis in one place. It includes:

| Area | Information |
|---|---|
| Training load | Fitness (CTL), fatigue (ATL), and form/training-stress balance (TSB) over time |
| Recovery | Heart-rate variability (HRV), resting heart rate, and sleep-quality trends |
| Activity mix | Training time grouped by sport, including Cycling, Soccer, Hiking, and Strength where present |
| Weekly volume | Stacked training hours or training stress (TSS) by activity type |
| Power | Cycling power–duration curve, including available comparison series |
| Intensity | Heart-rate and power-zone time distribution and training-style indicators |
| Session history | The most recent five activities, with an expandable list of older sessions |
| Plan context | The next planned workout, or a prompt to create a plan when none is available |

The analysis-window control supports **7 to 90 days**. Charts retain missing measurements as missing data rather than treating them as zero. Sport labels are human-readable; for example, an Intervals.icu `Ride` is displayed as **Cycling**.

### Settings

The Settings page stores profile preferences. Developer mode makes LLM prompt overrides available. Changes to prompts affect future plan generations; the user can leave an override empty to use the application default.

### Appearance

IntelliWatts supports light and dark appearance on the Dashboard, Planner, Settings, and sign-in page. The theme switch at the bottom of the navigation sidebar selects either appearance. The choice is stored in your browser and remains active across page navigation and reloads; when no choice has been saved, the app follows your device's appearance preference.

Charts adjust their axis labels, gridlines, legends, and tooltips to remain legible in both themes. The metric values, training data, and planning settings are the same in both modes.

## How to use the application

1. **Sign in.** Open the web app and enter the configured application password.
2. **Check the Dashboard.** Review training load, recent activities, recovery signals, and the current analysis window.
3. **Set your goal.** On the Plan page, enter the target and date, then save the long-term goal.
4. **Configure the week.** Select the planning week and define the weekly hours, session limit, model, and optional wellness context.
5. **Generate and review.** Generate the weekly plan, check the proposed workout and any available long-term context, and update it if needed.
6. **Publish.** Use the publish action to send the selected workout to Intervals.icu when it is ready.

The Planner, Dashboard, and Settings are available from the main navigation. On smaller screens the navigation moves into the page header.

## Supported integrations

| Integration | Usage |
|---|---|
| [Intervals.icu](https://intervals.icu) | Training activities, wellness data, power curves, training load, and workout publishing |
| [OpenAI](https://platform.openai.com/api-keys) | Supported LLM backend for training-plan generation |
| [Groq](https://console.groq.com/keys) | Supported LLM backend for training-plan generation |
| [Google Gemini](https://aistudio.google.com/api-keys) | Supported LLM backend for training-plan generation |

The available model identifiers are maintained in `app/config.py`. The configured API key for the selected provider is required whenever a plan is generated.

## Requirements

- Python **3.14+** with [uv](https://docs.astral.sh/uv/)
- PostgreSQL and a database connection URL
- Node.js and npm for rebuilding Tailwind CSS
- Intervals.icu athlete ID and API key
- API credentials for at least one supported LLM provider
- A strong application password and a session-signing secret

The hosted installation uses environment variables for credentials. For local development, configure a private `.env` file.

## Installation and local development

### 1. Configure environment variables

Copy the example file:

```bash
cp .env.example .env
```

Set the required values. Keep the real `.env` file out of source control.

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL URL used by the app and migrations |
| `APP_PASSWORD` | Web-interface password (at least 12 characters) |
| `SESSION_SECRET` | Session-signing secret (at least 32 characters) |
| `APP_ORIGIN` | Origin of the app, such as `http://localhost:8000` or an HTTPS domain |
| `SESSION_COOKIE_SECURE` | Set to `false` for local HTTP; use `true` for HTTPS |
| `INTERVALS_ATHLETE_ID` | Athlete identifier from Intervals.icu |
| `INTERVALS_API_KEY` | Intervals.icu API credential |
| `LANGUAGE_MODEL` | Default model identifier for plan generation |
| `OPENAI_API_KEY` | OpenAI credential, if using OpenAI |
| `GROQ_API_KEY` | Groq credential, if using Groq |
| `GEMINI_API_KEY` | Gemini credential, if using Gemini |
| `CACHE_INTERVALS_HOURS` | Number of hours to cache Intervals.icu API responses (default: 0) |
| `ANALYSIS_DAYS` | History window for coach context (default: 120) |
| `DASHBOARD_DAYS` | Default Dashboard display window (default: 42) |

Generate a session secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Intervals.icu API credentials are available from **Settings → Developer → API Key** in your Intervals.icu account.

### 2. Install dependencies

```bash
./setup.sh
```

Alternatively, install the Python environment directly:

```bash
uv sync
```

### 3. Apply database migrations

```bash
uv run alembic upgrade head
```

Use a dedicated development database. The app uses PostgreSQL for training plans, preferences, and application state.

### 4. Start the web server

```bash
./run.sh
```

Or start FastAPI directly:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://localhost:8000/](http://localhost:8000/) and sign in with `APP_PASSWORD`. The Dashboard is at `/dashboard` and Settings at `/settings`.

## Authentication and data handling

IntelliWatts is configured for a personal athlete profile. The app uses a password-protected interface and a signed session cookie. Sessions expire after 12 hours. Changing the app password or session secret invalidates existing sessions.

Workout and wellness information comes from Intervals.icu. The application stores its own planning and preference data in PostgreSQL. Protect both the database credentials and external API tokens, and use HTTPS for hosted installations.

### Database backup and migrations

Apply pending Alembic migrations after updating the code:

```bash
uv run alembic upgrade head
```

Use PostgreSQL backup tools such as `pg_dump` and `pg_restore` or your provider's backup facilities. Test restores against a separate database, not the active application database.

## Frontend and project structure

IntelliWatts uses **Python + FastAPI** for the backend and **Jinja2 + Tailwind CSS** for server-rendered pages. Interactive analytics are rendered with **Chart.js**. A small application stylesheet adds the IntelliWatts visual system.

| Location | Purpose |
|---|---|
| `app/routes/` | FastAPI HTTP routes |
| `app/planning/` and `app/services/` | Planning and application services |
| `app/intervals/` | Intervals.icu client, parsing and analytics |
| `app/models/` | Persistent data models |
| `app/templates/` | Jinja2 templates and shared UI macros |
| `app/static/` | CSS, JavaScript and logo artwork |
| `migrations/versions/` | Alembic migrations |
| `tests/` | Unit, integration and browser-flow tests |
| `scripts/` | Local developer and agent utilities |

The brand artwork is stored at [`app/static/intelliwatts-logo.webp`](app/static/intelliwatts-logo.webp). The navigation uses the same selected image.

### Rebuild styles

```bash
npm ci
npm run build:css
```

Generated Tailwind assets are committed and checked for consistency by CI. The app loads `tailwind-light.css`, `intelliwatts-ui.css`, and `intelliwatts-dark.css`. The theme switch uses `theme.js`, and Dashboard charts use `chart-theme.js`.

## Tests and quality checks

Install test dependencies and Playwright Chromium:

```bash
uv sync --extra dev --extra test
uv run playwright install chromium
```

Run the suite against a disposable PostgreSQL database or a separate test branch:

```bash
TEST_DATABASE_URL="postgresql://user:password@host/test_database" uv run pytest tests/
```

Run repository pre-commit checks:

```bash
uv run prek run --all-files --show-diff-on-failure
```

The GitHub **Gatekeeper** workflow runs code checks, unit/browser-flow tests, and generated-CSS verification. Screenshot creation is not part of Gatekeeper.

### Manual screenshots for agents

A standalone Playwright capture script produces desktop (1440 px) and mobile (390 px) screenshots for the Planner and Dashboard:

```bash
export INTELLIWATTS_SCREENSHOT_PASSWORD="your-local-app-password"
uv run python scripts/capture_ui_screenshots.py --base-url http://127.0.0.1:8000 --theme dark
```

Use `--theme light` for light-mode screenshots or omit `--theme` to use the system preference. Captures are written to `artifacts/ui-screenshots/`, which is gitignored. **Screenshots can contain personal fitness and health data**: inspect them before sharing or attaching them to a PR. The script is opt-in and runs only when invoked manually.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Sign-in fails | `APP_PASSWORD`, `APP_ORIGIN`, session cookie security setting, and the expected local/HTTPS origin |
| No workout or wellness data | Intervals.icu athlete ID, API key, account permissions, and data availability for the selected period |
| Plan generation fails | Selected model, corresponding provider API key, weekly limits, and server logs |
| Publishing fails | Intervals.icu authentication, the selected workout, and the publish status displayed in the Planner |
| Charts are empty | Whether the selected 7–90-day window contains activities, power, or wellness measurements |
| Styling is stale | Rebuild CSS with `npm ci && npm run build:css` and refresh the browser |
| Database errors | `DATABASE_URL`, database reachability, and `uv run alembic upgrade head` |

## Scope

IntelliWatts is a personal training-planning application, not a medical monitoring service. Its metrics and model-generated plans are training aids; they should be interpreted alongside the athlete's own experience and available data.
