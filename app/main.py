"""Main entrypoint for the IntelliWatts app."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import GLOBAL_SETTINGS, LanguageModel
from app.db import init_db
from app.dev.bootstrap import bootstrap_dev_user
from app.models.user import User
from app.routes import api, auth, secrets, web
from app.services.planner import generate_weekly_plan


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:  # noqa: RUF029
    """Lifespan for the FastAPI app.

    Yields:
        None
    """
    bootstrap_dev_user()
    yield


app = FastAPI(title="Intervals Coach", version="0.1.0", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api.router)
app.include_router(web.router)
app.include_router(auth.router)
app.include_router(secrets.router, prefix="/users")
init_db()

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
    content = generate_weekly_plan(user=User(id=1, email="test", password_hash="hash"))
    print("Training plan:")
    print(10 * "=")
    print(content["plan"])
    print(3 * "\n")
    print("Weekly Summary:")
    print(10 * "=")
    print(content["summary"])
