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

🔗 **Preview:**  
https://matze298.github.io/intelliwatts/example_output.html


> [!IMPORTANT] 
> The app is currently limited to personal usage as it uses the athlete ID and personal API-Token to parse intervals.icu.

# Initial SetUp
API Tokens are used to authenticate with the respective APIs (Intervals.icu, OpenAI, Google Gemini). They are stored in the `.env` file for security reasons, which is ignored from version control systems and must not be shared publicly.

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
## Via WebApp
1. Run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` to start the FastAPI server.
2. Open a web browser and navigate to `http://localhost:8000/`
3. Click "Generate Plan"
4. The plan and summary will be displayed in the web browser.

## Via FastAPI
1. Run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` to start the FastAPI server.
2. Call `curl -X POST http://localhost:8000/api/generate-plan` to retrieve the request.

## Via Python
1. Run `python app/main.py` to generate the training plan.

# Settings
The following settings are available via `.env`:
- `INTERVALS_API_KEY`: The API key for Intervals.icu.
- `INTERVALS_ATHLETE_ID`: The athlete ID for Intervals.icu.
- `OPENAI_API_KEY`: The API key for OpenAI.
- `GEMINI_API_KEY`: The API key for Google Gemini.
- `LANGUAGE_MODEL`: The type of Language Model to use.
- `CACHE_INTERVALS_HOURS`: The number of hours to cache the Intervals.icu data for. Defaults to 0 (no caching is used).