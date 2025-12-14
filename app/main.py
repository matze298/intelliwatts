"""Main entrypoint for the IntelliWatts app."""

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Intervals Coach")

app.include_router(router)
