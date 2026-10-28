"""The single local athlete profile used by the application."""

from uuid import UUID

from sqlmodel import Session

from app.db import engine
from app.models.user import User

PROFILE_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_profile() -> User:
    """Return the persistent internal profile, creating it on first use."""
    with Session(engine) as session:
        profile = session.get(User, PROFILE_ID)
        if profile is None:
            profile = User(id=PROFILE_ID, email="local", password_hash="")
            session.add(profile)
            session.commit()
            session.refresh(profile)
        return profile
