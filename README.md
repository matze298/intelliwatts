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
1. Run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` to start the FastAPI server.
2. Open a web browser and navigate to `http://localhost:8000/`
3. Click "Generate Plan"
4. The plan and summary will be displayed in the web browser.

## Via FastAPI (Dev)
1. Run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` to start the FastAPI server.
2. Call `curl -X POST http://localhost:8000/api/generate-plan` to retrieve the request.

## Via Python (Dev)
1. Run `python app/main.py` to generate the training plan.

# Settings
The settings for the app are defined in `app/config.py`. There are three types of settings:

1. Settings that can be updated via the App interface (e.g., `SYSTEM_PROMPT`, `USER_PROMPT`, `weekly_hours`, `weekly_sessions`).
2. Settings that are managed via `.env` or Env variables (e.g., `INTERVALS_API_KEY`, `INTERVALS_ATHLETE_ID`, `OPENAI_API_KEY`, `GEMINI_API_KEY`).
3. Settings that are hardcoded and cannot be changed (e.g., `CACHE_INTERVALS_HOURS`).
