"""Dev settings for local debugging."""

from sqlmodel import Session, select

from app.auth.auth import hash_password
from app.config import GLOBAL_SETTINGS
from app.db import engine
from app.models.user import User, UserSecrets
from app.security.crypto import encrypt


def bootstrap_dev_user() -> None:
    """Fills the database with a dev user and secrets for local debugging."""
    if not GLOBAL_SETTINGS.DEV_USER:
        return

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == GLOBAL_SETTINGS.DEV_USER)).first()

        if not user:
            if GLOBAL_SETTINGS.DEV_PASSWORD is None:
                msg = "DEV_PASSWORD must be set if DEV_USER is set!"
                raise ValueError(msg)
            user = User(
                email=GLOBAL_SETTINGS.DEV_USER,
                password_hash=hash_password(GLOBAL_SETTINGS.DEV_PASSWORD),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        secrets = session.exec(select(UserSecrets).where(UserSecrets.user_id == user.id)).first()

        if not secrets:
            secrets = UserSecrets(
                user_id=user.id,
                intervals_athlete_id=GLOBAL_SETTINGS.INTERVALS_ATHLETE_ID,
                intervals_api_key=encrypt(GLOBAL_SETTINGS.INTERVALS_API_KEY),
                openai_api_key=encrypt(GLOBAL_SETTINGS.OPENAI_API_KEY) if GLOBAL_SETTINGS.OPENAI_API_KEY else None,
                gemini_api_key=encrypt(GLOBAL_SETTINGS.GEMINI_API_KEY) if GLOBAL_SETTINGS.GEMINI_API_KEY else None,
            )
            session.add(secrets)
            session.commit()


if __name__ == "__main__":
    bootstrap_dev_user()
