"""Main entrypoint for the IntelliWatts app."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.access import AccessMiddleware, login, login_page, logout
from app.config import LanguageModel, get_settings
from app.db import init_db
from app.profile import get_profile
from app.routes import api, web
from app.routes import settings as settings_routes
from app.services.planner import generate_weekly_plan

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncGenerator[None]:  # ruff: ignore[unused-function-argument]
    """Lifespan for the FastAPI app.

    Yields:
        None
    """
    get_profile()
    yield


app = FastAPI(title="Intervals Coach", version="0.1.0", lifespan=lifespan)
app.add_middleware(AccessMiddleware)
app.add_api_route("/login", login_page, methods=["GET"], include_in_schema=False)
app.add_api_route("/login", login, methods=["POST"], include_in_schema=False)
app.add_api_route("/logout", logout, methods=["POST"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api.router)
app.include_router(web.planner_router)
app.include_router(web.router)
app.include_router(settings_routes.router)
init_db()

# Add settings to the App state for templates
app.state.settings = {"settings": get_settings(), "models": LanguageModel}
app.state.render_planner_error_response = web.render_planner_error_response


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
    content = asyncio.run(generate_weekly_plan(user=get_profile()))
    _LOGGER.info("Generated plan:\n%s", content)
