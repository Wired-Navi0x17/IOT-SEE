from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import select

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from . import auth, cricapi, matches, queries  # noqa: E402
from .db import init_db, session  # noqa: E402
from .models import CommandLog, DeviceTelemetry, Match, Player, Snapshot, Team, Tournament, TournamentTeam  # noqa: E402
from .service import SIM_SPEEDS, hub, summary  # noqa: E402

log = logging.getLogger("hub")
STATIC = ROOT / "static"


def lan_ip() -> str:
    # On the UNO Q hotspot there is no default route, so the probe below would give 127.0.0.1.
    if os.environ.get("HUB_ADVERTISE_IP"):
        return os.environ["HUB_ADVERTISE_IP"]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


async def advertise(port: int):
    try:
        from zeroconf import IPVersion, ServiceInfo
        from zeroconf.asyncio import AsyncZeroconf
        ip = lan_ip()
        info = ServiceInfo("_cricket._tcp.local.", "SEEv2 Cricket Hub._cricket._tcp.local.",
                           addresses=[socket.inet_aton(ip)], port=port, server="cricket-hub.local.",
                           properties={"path": "/ws/device"})
        zc = AsyncZeroconf(ip_version=IPVersion.V4Only)
        await zc.async_register_service(info)
        log.info("mDNS: cricket-hub.local -> %s:%d", ip, port)
        return zc, info
    except Exception as e:
        log.warning("mDNS advertise failed: %s", e)
        return None, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .seed import seed_if_empty
    seed_if_empty()
    port = int(os.environ.get("HUB_PORT", "8000"))
    from .discovery import beacon
    tasks = [asyncio.create_task(hub.watchdog()), asyncio.create_task(beacon(port)),
             asyncio.create_task(cricapi.poller(hub.match_changed, hub.on_usage))]
    # resume simulations that were running when the hub stopped
    with session() as s:
        for m in s.exec(select(Match).where(Match.source == "sim", Match.status == "live")):
            hub.start_sim(m.id, "quick")
    zc, info = await advertise(port)
    yield
    for t in tasks:
        t.cancel()
    if zc:
        await zc.async_unregister_service(info)
        await zc.async_close()


app = FastAPI(title="SEEv2 Cricket Hub", lifespan=lifespan)
admin = Depends(auth.require_admin)


def bad(e: Exception):
    raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------- auth
class PinIn(BaseModel):
    pin: str


@app.get("/api/auth")
def auth_status(request: Request):
    return {"admin": auth.is_admin(request)}


@app.post("/api/auth/unlock")
def unlock(body: PinIn, request: Request, response: Response):
    if not auth.check_pin(body.pin, request.client.host if request.client else ""):
        raise HTTPException(status_code=403, detail="Wrong PIN (5 misses lock unlocking for 60 s)")
    response.set_cookie(auth.COOKIE, auth.token(), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return {"admin": True}


@app.post("/api/auth/lock")
def lock(response: Response):
    response.delete_cookie(auth.COOKIE)
    return {"admin": False}


# ---------------------------------------------------------------- overview / system
@app.get("/api/overview")
def overview():
    return queries.overview()


@app.get("/api/system")
def system():
    return {"usage": cricapi.latest_usage(), "device": hub.device_status(), "lan": lan_ip(),
            "port": int(os.environ.get("HUB_PORT", "8000")), "time": datetime.now().isoformat(),
            "apiPolling": __import__("cricket_hub.db", fromlist=["get_setting"]).get_setting("api_polling", True)}


@app.get("/api/usage")
def usage():
    return {"current": cricapi.latest_usage(), "byDay": cricapi.usage_by_day()}


class TogglePolling(BaseModel):
    on: bool


@app.post("/api/cricapi/polling", dependencies=[admin])
async def toggle_polling(body: TogglePolling):
    from .db import set_setting
    set_setting("api_polling", body.on)
    if body.on:
        cricapi.wake()
    await hub.activity("api", f"CricketData polling {'enabled' if body.on else 'paused'}")
    return {"apiPolling": body.on}


@app.post("/api/cricapi/refresh", dependencies=[admin])
async def refresh_api():
    if not cricapi.api_key():
        raise HTTPException(400, "Add CRICAPI_KEY to hub/.env and restart the hub")
    cricapi.wake(force=True)
    return {"queued": True}


# ---------------------------------------------------------------- tournaments
class TournamentIn(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    format: str = "T20"
    overs: int = Field(20, ge=1, le=50)
    venue: str = ""
    start_date: str = ""
    end_date: str = ""
    team_ids: list[int] = []


@app.get("/api/tournaments")
def tournaments():
    out = []
    with session() as s:
        for t in s.exec(select(Tournament).order_by(Tournament.id.desc())):
            n = len(list(s.exec(select(TournamentTeam).where(TournamentTeam.tournament_id == t.id))))
            out.append({**t.model_dump(mode="json"), "teams": n})
    return out


@app.post("/api/tournaments", dependencies=[admin])
async def create_tournament(body: TournamentIn):
    with session() as s:
        t = Tournament(name=body.name, format=body.format, overs=body.overs, venue=body.venue,
                       start_date=body.start_date, end_date=body.end_date, status="upcoming")
        s.add(t)
        s.commit()
        s.refresh(t)
        for tid in body.team_ids:
            s.add(TournamentTeam(tournament_id=t.id, team_id=tid))
        s.commit()
    await hub.activity("tournament", f"Tournament created: {t.name}")
    return t


@app.get("/api/tournaments/{tid}")
def tournament(tid: int):
    with session() as s:
        t = s.get(Tournament, tid)
        if not t:
            raise HTTPException(404, "tournament not found")
        team_ids = [x.team_id for x in s.exec(select(TournamentTeam).where(TournamentTeam.tournament_id == tid))]
        teams = list(s.exec(select(Team).where(Team.id.in_(team_ids)))) if team_ids else []
        ms = list(s.exec(select(Match).where(Match.tournament_id == tid).order_by(Match.scheduled_at)))
    return {**t.model_dump(mode="json"), "teams": [x.model_dump(mode="json") for x in teams],
            "fixtures": [queries.match_row(m) for m in ms], "table": queries.points_table(tid)}


class TeamLink(BaseModel):
    team_id: int


@app.post("/api/tournaments/{tid}/teams", dependencies=[admin])
async def add_team_to_tournament(tid: int, body: TeamLink):
    with session() as s:
        if not s.get(TournamentTeam, (tid, body.team_id)):
            s.add(TournamentTeam(tournament_id=tid, team_id=body.team_id))
            s.commit()
    return tournament(tid)


class TStatus(BaseModel):
    status: str


@app.post("/api/tournaments/{tid}/status", dependencies=[admin])
async def tournament_status(tid: int, body: TStatus):
    if body.status not in ("upcoming", "active", "completed"):
        raise HTTPException(400, "bad status")
    with session() as s:
        t = s.get(Tournament, tid)
        t.status = body.status
        s.add(t)
        s.commit()
    await hub.activity("tournament", f"{t.name} is now {body.status}")
    return {"ok": True}


# ---------------------------------------------------------------- teams / players
class TeamIn(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    short: str = Field(min_length=2, max_length=4)
    city: str = ""
    manager: str = ""
    tournament_id: Optional[int] = None


class PlayerIn(BaseModel):
    name: str = Field(min_length=3, max_length=40)
    role: str = "BAT"
    bat: int = Field(50, ge=1, le=100)
    bowl: int = Field(20, ge=1, le=100)
    style: str = ""


@app.get("/api/teams")
def teams():
    with session() as s:
        ts = list(s.exec(select(Team).order_by(Team.name)))
        counts = {}
        for p in s.exec(select(Player)):
            counts[p.team_id] = counts.get(p.team_id, 0) + 1
    return [{**t.model_dump(mode="json"), "players": counts.get(t.id, 0)} for t in ts]


@app.post("/api/teams", dependencies=[admin])
async def create_team(body: TeamIn):
    with session() as s:
        t = Team(name=body.name, short=body.short.upper(), city=body.city, manager=body.manager)
        s.add(t)
        s.commit()
        s.refresh(t)
        if body.tournament_id:
            s.add(TournamentTeam(tournament_id=body.tournament_id, team_id=t.id))
            s.commit()
    await hub.activity("team", f"Team registered: {t.name}")
    return t


@app.get("/api/teams/{tid}")
def team(tid: int):
    stats = queries.player_stats()
    with session() as s:
        t = s.get(Team, tid)
        if not t:
            raise HTTPException(404, "team not found")
        ps = list(s.exec(select(Player).where(Player.team_id == tid).order_by(Player.id)))
    return {**t.model_dump(mode="json"),
            "players": [{**p.model_dump(mode="json"), "stats": stats.get(p.id)} for p in ps]}


@app.get("/api/teams/{tid}/default_xi")
def team_default_xi(tid: int):
    """Suggested XI in batting order, plus the bowlers that would bowl (top 6 by bowling rating)."""
    xi = matches.default_xi(tid)
    with session() as s:
        ps = {p.id: p for p in s.exec(select(Player).where(Player.id.in_(xi)))} if xi else {}
    bowlers = sorted(xi, key=lambda i: -ps[i].bowl)[:6]
    return {"xi": xi, "bowlers": bowlers}


@app.post("/api/teams/{tid}/players", dependencies=[admin])
async def add_player(tid: int, body: PlayerIn):
    with session() as s:
        if not s.get(Team, tid):
            raise HTTPException(404, "team not found")
        p = Player(team_id=tid, **body.model_dump())
        s.add(p)
        s.commit()
        s.refresh(p)
    await hub.activity("player", f"{p.name} registered")
    return p


@app.patch("/api/players/{pid}", dependencies=[admin])
def update_player(pid: int, body: PlayerIn):
    with session() as s:
        p = s.get(Player, pid)
        if not p:
            raise HTTPException(404, "player not found")
        for k, v in body.model_dump().items():
            setattr(p, k, v)
        s.add(p)
        s.commit()
        s.refresh(p)
        return p


@app.get("/api/players")
def players():
    stats = queries.player_stats()
    with session() as s:
        teams_ = {t.id: t.short for t in s.exec(select(Team))}
        return [{**p.model_dump(mode="json"), "team": teams_.get(p.team_id, ""), "stats": stats.get(p.id)}
                for p in s.exec(select(Player).order_by(Player.name))]


@app.get("/api/leaders")
def leaders():
    return queries.top_performers(10)


# ---------------------------------------------------------------- matches
class MatchIn(BaseModel):
    team_a_id: int
    team_b_id: int
    tournament_id: Optional[int] = None
    overs: int = Field(20, ge=1, le=50)
    venue: str = ""
    scheduled_at: Optional[datetime] = None


@app.get("/api/matches")
def list_matches(status: Optional[str] = None, source: Optional[str] = None):
    return queries.list_matches(status, source, limit=100)


@app.post("/api/matches", dependencies=[admin])
async def schedule(body: MatchIn):
    try:
        m = matches.create_match(body.team_a_id, body.team_b_id, tournament_id=body.tournament_id,
                                 overs=body.overs, venue=body.venue, scheduled_at=body.scheduled_at)
    except matches.ScoringError as e:
        bad(e)
    await hub.activity("match", f"Scheduled {m.team_a_short} v {m.team_b_short}")
    return queries.match_row(m)


@app.get("/api/matches/{mid}")
def get_match(mid: int):
    with session() as s:
        m = s.get(Match, mid)
        if not m:
            raise HTTPException(404, "match not found")
        xi_ids = list(m.xi_a or []) + list(m.xi_b or [])
        squad_a = list(s.exec(select(Player).where(Player.team_id == m.team_a_id))) if m.team_a_id else []
        squad_b = list(s.exec(select(Player).where(Player.team_id == m.team_b_id))) if m.team_b_id else []
    return {**queries.match_row(m), "state": m.state, "xiA": m.xi_a, "xiB": m.xi_b,
            "squadA": [p.model_dump(mode="json") for p in squad_a],
            "squadB": [p.model_dump(mode="json") for p in squad_b],
            "pendingBowler": m.pending_bowler, "swapPending": m.swap_pending, "xiIds": xi_ids}


class StartIn(BaseModel):
    toss_winner: str = "A"
    elected: str = "bat"
    xi_a: Optional[list[int]] = None
    xi_b: Optional[list[int]] = None
    bowlers_a: Optional[list[int]] = None
    bowlers_b: Optional[list[int]] = None


@app.post("/api/matches/{mid}/start", dependencies=[admin])
async def start(mid: int, body: StartIn):
    try:
        st = matches.start_match(mid, toss_winner=body.toss_winner, elected=body.elected, xi_a=body.xi_a, xi_b=body.xi_b,
                                 bowlers_a=body.bowlers_a, bowlers_b=body.bowlers_b)
    except matches.ScoringError as e:
        bad(e)
    await hub.activity("score", f"Live scoring started: {st['teamA']['short']} v {st['teamB']['short']}")
    await hub.match_changed(mid, st)
    return st


class BallIn(BaseModel):
    runs_bat: int = Field(0, ge=0, le=7)
    extra_type: Optional[str] = None
    extras: int = Field(0, ge=0, le=7)
    wicket: bool = False
    wicket_kind: Optional[str] = None
    dismissed: str = "striker"
    bowler: Optional[int] = None


@app.post("/api/matches/{mid}/ball", dependencies=[admin])
async def ball(mid: int, body: BallIn):
    try:
        st = matches.add_ball(mid, **body.model_dump())
    except matches.ScoringError as e:
        bad(e)
    if st.get("lastEvent") == "wicket":
        await hub.activity("score", f"Wicket: {summary(st)}")
    if st["ended"]:
        await hub.activity("match", f"Result: {st['result']}")
    await hub.match_changed(mid, st)
    return st


@app.post("/api/matches/{mid}/undo", dependencies=[admin])
async def undo(mid: int):
    try:
        st = matches.undo(mid)
    except matches.ScoringError as e:
        bad(e)
    await hub.match_changed(mid, st)
    return st


class PendingIn(BaseModel):
    bowler: Optional[int] = None
    swap: Optional[bool] = None


@app.post("/api/matches/{mid}/pending", dependencies=[admin])
async def pending(mid: int, body: PendingIn):
    try:
        st = matches.set_pending(mid, bowler=body.bowler, swap=body.swap)
    except matches.ScoringError as e:
        bad(e)
    await hub.match_changed(mid, st)
    return st


@app.get("/api/matches/{mid}/analytics")
def analytics(mid: int):
    return queries.match_analytics(mid)


# ---------------------------------------------------------------- simulation
class SimIn(BaseModel):
    team_a_id: int
    team_b_id: int
    xi_a: Optional[list[int]] = None
    xi_b: Optional[list[int]] = None
    overs: int = Field(20, ge=2, le=50)
    toss_winner: str = "A"
    elected: str = "bat"
    bowlers_a: Optional[list[int]] = None
    bowlers_b: Optional[list[int]] = None
    speed: str = "quick"
    show_on_cyd: bool = True


@app.post("/api/sim", dependencies=[admin])
async def start_sim(body: SimIn):
    try:
        m = matches.create_match(body.team_a_id, body.team_b_id, source="sim", overs=body.overs, venue="Simulation")
        st = matches.start_match(m.id, toss_winner=body.toss_winner, elected=body.elected, xi_a=body.xi_a, xi_b=body.xi_b)
    except matches.ScoringError as e:
        bad(e)
    hub.start_sim(m.id, body.speed)
    await hub.activity("sim", f"Simulation started: {m.team_a_short} v {m.team_b_short}, {body.overs} overs")
    if body.show_on_cyd:
        await hub.set_source({"kind": "sim", "match_id": m.id})
    await hub.match_changed(m.id, st)
    return {"id": m.id, "state": st}


class SpeedIn(BaseModel):
    speed: str


@app.post("/api/sim/{mid}/speed", dependencies=[admin])
async def sim_speed(mid: int, body: SpeedIn):
    if body.speed not in SIM_SPEEDS:
        raise HTTPException(400, f"speed must be one of {', '.join(SIM_SPEEDS)}")
    hub.sim_speed[mid] = body.speed
    return {"speed": body.speed}


@app.post("/api/sim/{mid}/pause", dependencies=[admin])
async def sim_pause(mid: int):  # async: runs on the loop that owns the sim task
    hub.stop_sim(mid)
    return {"running": False}


@app.post("/api/sim/{mid}/resume", dependencies=[admin])
async def sim_resume(mid: int):  # async: create_task needs the running loop
    hub.start_sim(mid, hub.sim_speed.get(mid, "quick"))
    return {"running": True}


@app.get("/api/sim/running")
def sim_running():
    return {"running": list(hub.sims.keys()), "speed": hub.sim_speed}


# ---------------------------------------------------------------- device
class CommandIn(BaseModel):
    name: str
    args: dict = {}


class SourceIn(BaseModel):
    kind: str                      # live (Screen 1) | sim (Screen 2) | match (pin one match)
    match_id: Optional[int] = None


@app.get("/api/device")
def device():
    with session() as s:
        tm = list(s.exec(select(DeviceTelemetry).order_by(DeviceTelemetry.id.desc()).limit(120)))
        cmds = list(s.exec(select(CommandLog).order_by(CommandLog.id.desc()).limit(30)))
        snaps = list(s.exec(select(Snapshot).order_by(Snapshot.id.desc()).limit(30)))
    return {**hub.device_status(),
            "history": [t.model_dump(mode="json") for t in reversed(tm)],
            "commands": [c.model_dump(mode="json") for c in cmds],
            "snapshots": [{"id": x.id, "ts": x.ts.isoformat(), "origin": x.origin, "summary": x.summary,
                           "matchId": x.match_id} for x in snaps]}


@app.post("/api/device/command", dependencies=[admin])
async def device_command(body: CommandIn):
    try:
        return await hub.command(body.name, body.args)
    except ValueError as e:
        bad(e)


@app.post("/api/device/source", dependencies=[admin])
async def device_source(body: SourceIn):
    if body.kind == "match":
        with session() as s:
            m = s.get(Match, body.match_id)
        if not m:
            raise HTTPException(404, "match not found")
        await hub.set_source({"kind": "match", "match_id": m.id})
        await hub.activity("device", f"CYD now showing {m.team_a_short} v {m.team_b_short}")
    elif body.kind in ("live", "sim"):
        await hub.set_source({"kind": body.kind, **({"match_id": body.match_id} if body.match_id else {})})
        await hub.activity("device", f"CYD switched to {'Screen 1 (live)' if body.kind == 'live' else 'Screen 2 (simulation)'}")
    else:
        raise HTTPException(400, "kind must be live, sim or match")
    return hub.device_status()


# ---------------------------------------------------------------- websockets
@app.websocket("/ws/ui")
async def ws_ui(ws: WebSocket):
    await ws.accept()
    hub.ui.add(ws)
    await ws.send_text(json.dumps({"type": "hello", "data": {"device": hub.device_status(),
                                                             "usage": cricapi.latest_usage()}}, default=str))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.ui.discard(ws)


@app.websocket("/ws/device")
async def ws_device(ws: WebSocket):
    await ws.accept()
    await hub.device_connected(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                await hub.device_message(json.loads(raw))
            except (ValueError, KeyError) as e:
                log.warning("bad device message: %s", e)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.device_gone(ws)


# ---------------------------------------------------------------- static web
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    root = STATIC.resolve()
    target = (STATIC / path).resolve()
    if path and target.is_relative_to(root) and target.is_file():   # no ../ escapes
        return FileResponse(target)
    index = STATIC / "index.html"
    if index.exists():
        return FileResponse(index)
    return Response("Dashboard not built yet: cd web && npm run build", media_type="text/plain")


def run() -> None:
    import uvicorn
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("HUB_PORT", "8000")), log_level="info")
