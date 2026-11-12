from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class Tournament(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    format: str = "T20"
    overs: int = 20
    venue: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = "upcoming"          # upcoming | active | completed
    created_at: datetime = Field(default_factory=now)


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    short: str
    city: str = ""
    manager: str = ""
    created_at: datetime = Field(default_factory=now)


class TournamentTeam(SQLModel, table=True):
    tournament_id: int = Field(foreign_key="tournament.id", primary_key=True)
    team_id: int = Field(foreign_key="team.id", primary_key=True)


class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    name: str
    role: str = "BAT"                 # BAT | BOWL | AR | WK
    bat: int = 50                     # 1..100 batting rating
    bowl: int = 20                    # 1..100 bowling rating
    style: str = ""                   # e.g. "RF", "SLA", "OB"
    created_at: datetime = Field(default_factory=now)


class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = "local"             # local | sim | api
    tournament_id: Optional[int] = Field(default=None, foreign_key="tournament.id")
    team_a_id: Optional[int] = Field(default=None, foreign_key="team.id")
    team_b_id: Optional[int] = Field(default=None, foreign_key="team.id")
    team_a_name: str = ""
    team_b_name: str = ""
    team_a_short: str = ""
    team_b_short: str = ""
    venue: str = ""
    scheduled_at: Optional[datetime] = None
    overs: int = 20
    status: str = "scheduled"         # scheduled | live | completed
    batting_first: str = "A"
    toss: str = ""
    xi_a: list = Field(default_factory=list, sa_column=Column(JSON))
    xi_b: list = Field(default_factory=list, sa_column=Column(JSON))
    bowlers_a: list = Field(default_factory=list, sa_column=Column(JSON))   # who may bowl for A (empty = anyone)
    bowlers_b: list = Field(default_factory=list, sa_column=Column(JSON))
    pending_bowler: Optional[int] = None
    swap_pending: bool = False
    result: str = ""
    api_id: Optional[str] = Field(default=None, index=True)
    series: str = ""
    state: dict = Field(default_factory=dict, sa_column=Column(JSON))   # latest computed/normalised state
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Ball(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="match.id", index=True)
    seq: int
    innings: int
    batter: int
    non_striker: int
    bowler: int
    runs_bat: int = 0
    extra_type: Optional[str] = None
    extras: int = 0
    wicket: bool = False
    wicket_kind: Optional[str] = None
    dismissed: Optional[int] = None
    created_at: datetime = Field(default_factory=now)


class Snapshot(SQLModel, table=True):
    """Every state the CYD was sent / reported showing."""
    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: Optional[int] = Field(default=None, index=True)
    ts: datetime = Field(default_factory=now, index=True)
    origin: str = "hub"               # hub | device
    summary: str = ""
    state: dict = Field(default_factory=dict, sa_column=Column(JSON))


class DeviceTelemetry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=now, index=True)
    device: str = ""
    fps: float = 0
    heap: int = 0
    maxblk: int = 0
    rssi: int = 0
    uptime: int = 0
    brightness: int = 0
    showing: str = ""


class CommandLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=now, index=True)
    name: str
    args: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = "sent"              # sent | acked | failed | timeout | offline
    detail: str = ""
    acked_at: Optional[datetime] = None


class ApiUsage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=now, index=True)
    day: str = Field(index=True)      # YYYY-MM-DD (UTC, CricketData resets daily)
    endpoint: str = "currentMatches"
    hits_today: int = 0
    hits_limit: int = 100
    ok: bool = True
    detail: str = ""


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=now, index=True)
    kind: str                         # tournament | match | team | player | device | api | sim | score
    text: str


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: Any = Field(default=None, sa_column=Column(JSON))
