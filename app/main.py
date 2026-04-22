"""Main entrypoint for the IntelliWatts app."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth.auth import hash_password
from app.config import LanguageModel, get_settings
from app.db import init_db
from app.dev.bootstrap import bootstrap_dev_user
from app.models.user import User
from app.routes import api, auth, secrets, web
from app.services.planner import generate_weekly_plan

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
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

# Add settings to the App state for templates
app.state.settings = {"settings": get_settings(), "models": LanguageModel}


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
    settings = get_settings()
    if settings.DEV_USER is None or settings.DEV_PASSWORD is None:
        msg = "DEV_USER and DEV_PASSWORD must be set to run main()"
        raise ValueError(msg)
    content = asyncio.run(
        generate_weekly_plan(
            user=User(email=settings.DEV_USER, password_hash=hash_password(settings.DEV_PASSWORD)),
        )
    )
    _LOGGER.info("Generated plan:\n%s", content)
