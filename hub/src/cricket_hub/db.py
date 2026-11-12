from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from .models import Activity, Setting

DB_PATH = Path(os.environ.get("HUB_DB") or Path(__file__).resolve().parents[2] / "cricket_hub.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Tiny forward-only migration: add columns that newer models have and an older DB lacks."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in have:
                    conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col.type.compile(engine.dialect)}'))


def session() -> Session:
    return Session(engine, expire_on_commit=False)


def get_setting(key: str, default: Any = None) -> Any:
    with session() as s:
        row = s.get(Setting, key)
        return default if row is None else row.value


def set_setting(key: str, value: Any) -> None:
    with session() as s:
        row = s.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=value)
        else:
            row.value = value
        s.add(row)
        s.commit()


def log_activity(kind: str, text: str) -> Activity:
    with session() as s:
        a = Activity(kind=kind, text=text)
        s.add(a)
        s.commit()
        s.refresh(a)
        return a


def recent_activity(limit: int = 30) -> list[Activity]:
    with session() as s:
        return list(s.exec(select(Activity).order_by(Activity.id.desc()).limit(limit)))
