"""Dev settings for local debugging."""

from sqlmodel import Session, select

from app.auth.auth import hash_password
from app.config import GLOBAL_SETTINGS
from app.db import engine
from app.models.user import User, UserSecrets


def bootstrap_dev_user() -> None:
    """Fills the SQL database with a dev user and secrets for local debugging."""
    if not GLOBAL_SETTINGS.DEV_USER or not GLOBAL_SETTINGS.DEV_PASSWORD:
        return

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == GLOBAL_SETTINGS.DEV_USER)).first()

        if not user:
            user = User(
                email=GLOBAL_SETTINGS.DEV_USER,
                password_hash=hash_password(GLOBAL_SETTINGS.DEV_PASSWORD),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        secrets = session.exec(select(UserSecrets).where(UserSecrets.user_id == user.id)).first()

        if not secrets:
            secrets = user.create_secrets(
                intervals_athlete_id=GLOBAL_SETTINGS.INTERVALS_ATHLETE_ID,
                intervals_api_key=GLOBAL_SETTINGS.INTERVALS_API_KEY,
                openai_api_key=GLOBAL_SETTINGS.OPENAI_API_KEY,
                gemini_api_key=GLOBAL_SETTINGS.GEMINI_API_KEY,
            )
            session.add(secrets)
            session.commit()


if __name__ == "__main__":
    bootstrap_dev_user()
