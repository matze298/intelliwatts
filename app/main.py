"""Main entrypoint for the IntelliWatts app."""

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import api, web
from app.services.planner import generate_weekly_plan
from app.config import GLOBAL_SETTINGS, LanguageModel

app = FastAPI(title="Intervals Coach", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api.router)
app.include_router(web.router)

# Add settings to the App state
app.state.settings = {"settings": GLOBAL_SETTINGS, "models": LanguageModel}


@app.get("/health", tags=["infra"])
def health_check() -> dict[str, str]:
    """Health check for the app.

    Returns:
        The status of the app.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    # Run code without FastAPI
    logging.basicConfig(level=logging.DEBUG)
    content = generate_weekly_plan()
    print("Training plan:")
    print(10 * "=")
    print(content["plan"])
    print(3 * "\n")
    print("Weekly Summary:")
    print(10 * "=")
    print(content["summary"])
