# IntelliWatts
IntelliWatts is a personal cycling coach that parses your training data from intervals.icu and generates a weekly training plan for you using an LLM of your choice.

It is customizable in terms of:
- Training goals
- Weekly training volume
- Available measurements
  - HR measurements
  - Power measurements

Current supported LLMs:
- OpenAI ChatGPT (requires subscription!)
- Google Gemini (free tier available!)

## Build Status
[![Gatekeeper](https://github.com/matze298/intelliwatts/actions/workflows/gatekeeper.yml/badge.svg?branch=main)](https://github.com/matze298/intelliwatts/actions/workflows/gatekeeper.yml)
[![codecov](https://codecov.io/github/matze298/intelliwatts/graph/badge.svg?token=HC93HLOWOB)](https://codecov.io/github/matze298/intelliwatts)



## 🌐 Live Demo
https://intelliwatts.onrender.com

## 🩺 Health Check
https://intelliwatts.onrender.com/health


> [!IMPORTANT] 
> The app is currently limited to personal usage as it uses the athlete ID and personal API-Token to parse intervals.icu.

# Initial SetUp
API Tokens are used to authenticate with the respective APIs (Intervals.icu, OpenAI, Google Gemini). Locally, they are stored in the `.env` file. For security reasons, `.env` is ignored from version control systems and must not be shared publicly. For all required keys, checkout the `env.example` file.

On prod (render), the env variables are currently managed via Environment variables, i.e., they cannot yet be customized for different users.

> [!WARNING]  
> Never share your tokens with anyone or commit them to version control systems!

## Intervals.icu
Authentication to intervals.icu is required for parsing your past workouts.
Go to https://intervals.icu/settings `Settings -> Dev --> API-Key` and set `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID` in `./env`.

## Language Model
The API key for the language model selected in `.env` must be set (defaults to Gemini for free usage)!

### OpenAI (optional)
1. Open https://platform.openai.com/api-keys
2. `Create new secret key`
3. Set `OPENAI_API_KEY` in `.env` to your key

### Google Gemini (optional)
1. Open https://aistudio.google.com/api-keys
2. Click "Create API Key"
3. Set `GEMINI_API_KEY` in `.env` to your key.


# Usage
## Via Deployed WebApp (Prod)
1. Go to https://intelliwatts.onrender.com

## Via Local WebApp (Dev)

1.  **Set up the environment:** Run `./setup.sh` in the project root to install dependencies and build static assets (including Tailwind CSS themes).
2.  **Start the development server:** Run `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Restart the server if you make significant code changes.
3.  **Access the application:** Open a web browser and navigate to `http://localhost:8000/`.
4.  **Generate a plan:** Interact with the UI to generate training plans.

## Via FastAPI (Dev)
1. Run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` to start the FastAPI server.
2. Call `curl -X POST http://localhost:8000/api/generate-plan` to retrieve the request.

## Via Python (Dev)

*Note: This section might describe a specific script for direct plan generation. For general plan generation, using the web app via `uvicorn` is recommended after running `./setup.sh`.*
1. Run `python app/main.py` to generate the training plan (if this script is intended for direct execution).

# Settings
The settings for the app are defined in `app/config.py`. There are three types of settings:

1. Settings that can be updated via the App interface (e.g., `SYSTEM_PROMPT`, `USER_PROMPT`, `weekly_hours`, `weekly_sessions`).
2. Settings that are managed via `.env` or Env variables (e.g., `INTERVALS_API_KEY`, `INTERVALS_ATHLETE_ID`, `OPENAI_API_KEY`, `GEMINI_API_KEY`).
3. Settings that are hardcoded and cannot be changed (e.g., `CACHE_INTERVALS_HOURS`).


# Development and Styling

## Local Development Setup

To set up the local development environment and ensure all necessary dependencies are installed and static assets are built, run the `setup.sh` script in your project's root directory:

```bash
./setup.sh
```

This script will:
- Create and activate a Python virtual environment.
- Install Python dependencies using `uv`.
- Install pre-commit hooks.
- **Build Tailwind CSS for both themes**, generating `app/static/tailwind-retro.css` and `app/static/tailwind-minimal.css`. This script performs a one-time build of the CSS assets.

## Styling and Theme Management

This application uses [Tailwind CSS](https://tailwindcss.com/) for its styling, processed via PostCSS. Two distinct themes are available:

1.  **Retro90s (Default)**: A nostalgic, terminal-inspired look with a dark background, neon pink text, and light blue accents.
2.  **Minimalistic**: A clean, accessible design with a light background and subtle colors.

**How Themes are Defined and Built:**

-   The input CSS for the **Retro90s** theme is located at `app/static/style-retro.css`.
-   The input CSS for the **Minimalistic** theme is located at `app/static/style-minimal.css`.

These input files (which import Tailwind CSS) are compiled into their respective output files:
-   `app/static/tailwind-retro.css`
-   `app/static/tailwind-minimal.css`

The compilation process is handled automatically by the `./setup.sh` script. The older `app/static/tailwind.css` file is no longer used.

**Theme Switching (Client-Side):**

Theme switching is managed entirely on the client-side using JavaScript.
-   A dropdown selector is available on all pages to allow users to choose their preferred theme. The default theme is Retro90s.
-   The selected theme preference is stored in your browser's `localStorage` to ensure persistence across different pages and future visits.
-   On page load, JavaScript checks for a saved preference and dynamically updates the `<link>` tag (with `id="theme-stylesheet"`) to load the appropriate stylesheet (`tailwind-retro.css` or `tailwind-minimal.css`).



