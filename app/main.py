"""Main entrypoint for the IntelliWatts app."""

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import api, web
from app.services.planner import generate_weekly_plan

app = FastAPI(title="Intervals Coach")
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api.router)
app.include_router(web.router)


if __name__ == "__main__":
    # Run code without FastAPI
    logging.basicConfig(level=logging.DEBUG)
    content = generate_weekly_plan()
    print("Training plan: \n 10*'=' \n", content["plan"])
    print(3 * "\n")
    print("Weekly Summary: \n 10*'=' \n", content["summary"])
