from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_database_tables() -> None:
    from app.database import models  # noqa: F401 - registers metadata

    Base.metadata.create_all(bind=engine)
    _add_sqlite_column_if_missing("support_tickets", "employee_id", "VARCHAR(50)")
    _add_sqlite_column_if_missing("ticket_drafts", "employee_id", "VARCHAR(50)")


def _add_sqlite_column_if_missing(table_name: str, column_name: str, column_type: str) -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
    if column_name in columns:
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
