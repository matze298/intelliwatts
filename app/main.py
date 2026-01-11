"""Main entrypoint for the IntelliWatts app."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth.auth import hash_password
from app.config import GLOBAL_SETTINGS, LanguageModel
from app.db import init_db
from app.dev.bootstrap import bootstrap_dev_user
from app.models.user import User
from app.routes import api, auth, secrets, web
from app.services.planner import generate_weekly_plan

_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:  # noqa: RUF029, ARG001
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
app.include_router(secrets.router)
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
    if GLOBAL_SETTINGS.DEV_USER is None or GLOBAL_SETTINGS.DEV_PASSWORD is None:
        msg = "DEV_USER and DEV_PASSWORD must be set to run main()"
        raise ValueError(msg)
    content = generate_weekly_plan(
        user=User(email=GLOBAL_SETTINGS.DEV_USER, password_hash=hash_password(GLOBAL_SETTINGS.DEV_PASSWORD)),
    )
    _LOGGER.info("Generated plan:\n%s", content)
