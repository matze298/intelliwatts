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
API Tokens are used to authenticate with the respective APIs (Intervals.icu, OpenAI, Google Gemini). For local development, they are stored in the `.env` file which **must not be shared publicly**. For all required keys, checkout the `env.example` file.
End users can manage their API keys via the Secrets page after login.

## Intervals.icu
Authentication to intervals.icu is required to parse past workouts.
Go to https://intervals.icu/settings `Settings -> Dev --> API-Key` and set `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID` in `./env`.

## Language Model
The API key for the language model selected must be set correctly either via  `.env` or via the Secrets page after login. The default model is Gemini Flash which provides free usage.

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
2.  **Start the development server:** Run `uvicorn app.main:app --reload`.
3.  **Access the application:** Open a web browser and navigate to the exposed link, e.g. `http://localhost:8000/`.
4.  **Generate a plan:** Interact with the UI to generate training plans.

## Via FastAPI (Dev)
1. Run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` to start the FastAPI server.
2. Call `curl -X POST http://localhost:8000/api/generate-plan` to retrieve the request.

## Via Python (Dev)
1. Run `python app/main.py` to generate the training plan.

# Settings
The settings for the app are defined in `app/config.py`. There are three types of settings:

1. Settings that can be updated via the App interface (e.g., `SYSTEM_PROMPT`, `USER_PROMPT`, `weekly_hours`, `weekly_sessions`).
2. Settings that are managed via `.env`, Env variables or the Secrets page (e.g., `INTERVALS_API_KEY`, `INTERVALS_ATHLETE_ID`, `OPENAI_API_KEY`, `GEMINI_API_KEY`).
3. Settings that are hardcoded and cannot be changed (e.g., `CACHE_INTERVALS_HOURS`).

# Local Development Setup

To set up the local DevEnv, run the `setup.sh` script in your project's root directory:

```bash
./setup.sh
```

This script will:
- Create and activate a Python virtual environment.
- Install Python dependencies using `uv`.
- Install pre-commit hooks.

# DevContainer Setup

For a fully isolated and reproducible development environment, you can use the provided DevContainer configuration. This setup ensures that all necessary tools and dependencies, including Docker itself, are available within the container.

**To set up the DevContainer:**

1.  **Open the project in VS Code.**
2.  **Follow the prompt:** VS Code will detect the `.devcontainer` folder and typically prompt you to "Reopen in Container".
3.  **Alternatively, use the Command Palette:** If not prompted, open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on macOS), search for "Dev Containers: Open Folder in Container", and select your project folder.
4.  **Build and Start:** VS Code will build the Docker image and start the container. This may take a few minutes on the first run.
5.  **Use the Integrated Terminal:** Once the container is ready, open a terminal within VS Code. You can now run all project commands, including the Gemini CLI and the project's sandbox commands (e.g., `docker compose -f sandbox/docker-compose.yml run sandbox <command>`), directly from this terminal.

This DevContainer setup ensures consistency across different development machines and simplifies dependency management. **Note:** The `sandbox` directory is still required for running the application and tests, as mandated by the project's `GEMINI.md`. The DevContainer provides the environment to *execute* these sandbox commands.

# Web Page Style & Themes
This application uses [Tailwind CSS](https://tailwindcss.com/) for its styling, processed via PostCSS.
To generate the static css files, execute the `build_tailwind.sh` script. This script will **build Tailwind CSS assets for all available themes**, generating `app/static/tailwind-<theme>.css`

Currently available themes are:
1.  **Retro90s (Default)**: A nostalgic, terminal-inspired look with a dark background, neon pink text, and light blue accents.
2.  **Minimalistic**: A clean, accessible design with a light background and subtle colors.

The themes are defined in `app/static/style-<theme>.css`.
Switching themes is managed entirely on the client-side via a dropdown menu.
