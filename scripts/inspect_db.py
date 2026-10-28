"""Script to inspect the configured PostgreSQL database."""

import json
import uuid
from datetime import date, datetime
from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.db import DATABASE_URL
from app.models.plan import TrainingPhase, TrainingPlan
from app.models.user import User


def json_serial(obj: Any) -> str:  # ruff: ignore[any-type]
    """JSON serializer for objects not serializable by default json code.

    Args:
        obj: The object to serialize.

    Returns:
        A string representation of the object.

    Raises:
        TypeError: If the type is not serializable.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, bytes):
        return "[BYTES]"
    msg = f"Type {type(obj)} not serializable"
    raise TypeError(msg)


def inspect_table(session: Session, model: type[SQLModel], name: str, limit: int = 5) -> None:
    """Print the first few rows of a table.

    Args:
        session: The database session.
        model: The SQLModel class to inspect.
        name: The name of the table for display.
        limit: The maximum number of rows to show.
    """
    print(f"\n--- Table: {name} (Top {limit}) ---")  # ruff: ignore[print]
    statement = select(model).limit(limit)
    results = session.exec(statement).all()

    if not results:
        print("No data found.")  # ruff: ignore[print]
        return

    for row in results:
        # Convert to dict and handle UUIDs/dates
        data = row.model_dump()
        # Clean up some fields for display if needed
        # Pretty print
        print(json.dumps(data, indent=2, default=json_serial))  # ruff: ignore[print]


def main() -> None:
    """Main entry point for the script."""
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        inspect_table(session, User, "User")
        inspect_table(session, TrainingPhase, "TrainingPhase")
        inspect_table(session, TrainingPlan, "TrainingPlan")


if __name__ == "__main__":
    main()
