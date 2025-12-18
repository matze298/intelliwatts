"""Main entrypoint for the IntelliWatts app."""

from fastapi import FastAPI

from app.api.routes import main, router

app = FastAPI(title="Intervals Coach")

app.include_router(router)


if __name__ == "__main__":
    # Run code without FastAPI
    main()
