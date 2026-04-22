"""Dev settings for local debugging."""

from sqlmodel import Session, select

from app.auth.auth import hash_password
from app.config import get_settings
from app.db import engine
from app.models.user import User, UserSecrets


def bootstrap_dev_user() -> None:
    """Fills the SQL database with a dev user and secrets for local debugging."""
    settings = get_settings()
    if not settings.DEV_USER or not settings.DEV_PASSWORD:
        return

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == settings.DEV_USER)).first()

        if not user:
            user = User(
                email=settings.DEV_USER,
                password_hash=hash_password(settings.DEV_PASSWORD),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        secrets = session.exec(select(UserSecrets).where(UserSecrets.user_id == user.id)).first()

        if not secrets:
            secrets = user.create_secrets(
                intervals_athlete_id=settings.INTERVALS_ATHLETE_ID,
                intervals_api_key=settings.INTERVALS_API_KEY,
                openai_api_key=settings.OPENAI_API_KEY,
                gemini_api_key=settings.GEMINI_API_KEY,
            )
            session.add(secrets)
            session.commit()


if __name__ == "__main__":
    bootstrap_dev_user()
