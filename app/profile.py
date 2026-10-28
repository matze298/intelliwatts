"""The single local athlete profile used by the application."""

from uuid import UUID

from sqlmodel import Session, select

from app.db import engine
from app.models.user import User

PROFILE_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_profile() -> User:
    """Return the persistent profile, creating it when the database is empty.

    Returns:
        The single saved profile.

    Raises:
        RuntimeError: If more than one profile exists.
    """
    with Session(engine) as session:
        existing_profiles = session.exec(select(User).limit(2)).all()
        if len(existing_profiles) > 1:
            msg = "The single-profile app requires one profile row; consolidate existing profiles before startup."
            raise RuntimeError(msg)
        if existing_profiles:
            return existing_profiles[0]

        profile = User(id=PROFILE_ID)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile
