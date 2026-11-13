"""Hub runtime: UI broadcast, the CYD link, simulations, display source."""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from datetime import timedelta
from typing import Any

from fastapi import WebSocket
from sqlmodel import select

from . import cricapi, ipl, matches
from .db import get_setting, log_activity, session, set_setting
from .engine import Engine
from .models import CommandLog, DeviceTelemetry, Match, Snapshot, now
from .simulator import roll, situation_for

log = logging.getLogger("hub")
FW_COMMANDS = {"brightness", "rotate", "invert", "identify", "reboot", "demo", "ping", "wifi_add", "wifi_forget", "qr"}
SIM_SPEEDS = {"broadcast": 4.0, "quick": 1.2, "turbo": 0.25}


def short_name(full: str) -> str:
    """'Aarav Kulkarni' -> 'A. KULKARNI' (CYD style)."""
    if not full:
        return ""
    parts = full.split()
    if len(parts) == 1:
        return parts[0].upper()[:23]
    return f"{parts[0][0]}. {' '.join(parts[1:])}".upper()[:23]


def to_device(st: dict) -> dict:
    def bat(b):
        return {"n": short_name(b.get("name", "")), "r": b.get("runs", 0), "b": b.get("balls", 0)}
    bw = st.get("bowler") or {}
    ca, cb = ipl.pair_colors(st["teamA"].get("short") or st["teamA"].get("name"), st["teamB"].get("short") or st["teamB"].get("name"))
    return {
        "ca": ca[1:], "cb": cb[1:],
        "t": "state", "series": (st.get("series") or "")[:47].upper(), "format": st.get("format", "T20")[:7],
        "a": st["teamA"]["short"][:5], "b": st["teamB"]["short"][:5], "batA": st["battingIsA"],
        "inn": st["innings"], "r": st["runs"], "w": st["wkts"], "bl": st["balls"], "tb": st["totalBalls"],
        "tgt": st["target"], "st": bat(st.get("striker") or {}), "ns": bat(st.get("nonStriker") or {}),
        "bw": {"n": short_name(bw.get("name", "")), "b": bw.get("balls", 0), "m": bw.get("maidens", 0),
               "r": bw.get("runs", 0), "w": bw.get("wkts", 0)},
        "nb": short_name(st.get("nextBat", "")), "nw": short_name(st.get("nextBowl", "")),
        "ov": [c[:3] for c in (st.get("thisOver") or [])[-8:]], "status": (st.get("status") or "")[:63],
        "live": st["live"], "ended": st["ended"], "hp": st.get("hasPlayers", False),
        "ev": st.get("lastEvent", "none"), "es": st.get("eventSeq", 0),
    }


def summary(st: dict) -> str:
    if not st:
        return ""
    bat = st["teamA"]["short"] if st["battingIsA"] else st["teamB"]["short"]
    return f"{bat} {st['runs']}/{st['wkts']} ({st['balls'] // 6}.{st['balls'] % 6})"


class Hub:
    def __init__(self) -> None:
        self.ui: set[WebSocket] = set()
        self.device: WebSocket | None = None
        self.device_info: dict[str, Any] = {}
        self.device_seen: float = 0
        self.last_tm: dict[str, Any] = {}
        self.cmd_seq = 0
        self.pending: dict[int, asyncio.Future] = {}
        self.sims: dict[int, asyncio.Task] = {}
        self.sim_speed: dict[int, str] = {}
        self.last_pushed: dict | None = None

    # ---------------- UI ----------------
    async def broadcast(self, kind: str, data: Any) -> None:
        msg = json.dumps({"type": kind, "data": data}, default=str)
        dead = []
        for ws in list(self.ui):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.ui.discard(ws)

    async def activity(self, kind: str, text: str) -> None:
        a = log_activity(kind, text)
        await self.broadcast("activity", {"id": a.id, "ts": a.ts.isoformat(), "kind": kind, "text": text})

    # ---------------- display source ----------------
    # ---------------- display: Screen 1 (live) / Screen 2 (simulation) ----------------
    def source(self) -> dict:
        src = get_setting("display_source", {"kind": "live"})
        if src.get("kind") not in ("live", "sim", "match"):
            src = {"kind": "live"}
        return src

    async def set_source(self, src: dict) -> None:
        set_setting("display_source", src)
        asyncio.create_task(self.command("demo", {"on": False}, log_it=False, timeout=2))   # TEMPORARY exhibition: a dashboard choice ends the CYD demo
        await self.push_display(force=True)
        await self.broadcast("device.status", self.device_status())

    async def toggle_screen(self) -> None:
        """CYD tap: Screen 1 (live) <-> Screen 2 (simulation)."""
        cur = self.source().get("kind")
        await self.set_source({"kind": "live"} if cur == "sim" else {"kind": "sim"})

    def _display_match(self) -> tuple[Match | None, str]:
        """The match the CYD should show now, plus a message for when there is none."""
        src = self.source()
        kind = src.get("kind")
        with session() as s:
            if kind == "match":
                return s.get(Match, src.get("match_id")), "Match not found"
            if kind == "sim":
                m = s.get(Match, src.get("match_id")) if src.get("match_id") else None
                if m is None or m.source != "sim":
                    m = s.exec(select(Match).where(Match.source == "sim", Match.status == "live")
                               .order_by(Match.id.desc())).first() or \
                        s.exec(select(Match).where(Match.source == "sim").order_by(Match.id.desc())).first()
                return m, "SIMULATION: set it up on the dashboard"
            live = s.exec(select(Match).where(Match.source.in_(["api", "local"]), Match.status == "live")
                          .order_by(Match.updated_at.desc())).first()
            if live is not None and (live.source == "local" or ipl.in_scope(live.team_a_name, live.team_b_name)):
                return live, ""
            nxt = s.exec(select(Match).where(Match.status == "scheduled", Match.source.in_(["api", "local"]),
                                             Match.scheduled_at.is_not(None))
                         .order_by(Match.scheduled_at)).first()
        msg = "No live IPL match" if ipl.live_scope() == "ipl" else "No live match"
        if nxt is not None:
            msg += f". Next: {nxt.team_a_short} v {nxt.team_b_short} {nxt.scheduled_at:%d %b %H:%M}"
        return None, msg

    @staticmethod
    def idle_payload(screen: str, message: str) -> dict:
        """A state with no teams: the CYD shows `status` as a full-screen message."""
        return {"t": "state", "series": ("SIMULATION" if screen == "sim" else "LIVE"), "format": "T20",
                "a": "", "b": "", "ca": "", "cb": "", "batA": True, "inn": 1, "r": 0, "w": 0, "bl": 0, "tb": 120,
                "tgt": 0, "st": {"n": "", "r": 0, "b": 0}, "ns": {"n": "", "r": 0, "b": 0},
                "bw": {"n": "", "b": 0, "m": 0, "r": 0, "w": 0}, "nb": "", "nw": "", "ov": [],
                "status": message[:63], "live": False, "sim": screen == "sim", "ended": False, "hp": False, "ev": "none", "es": 0}

    async def push_display(self, force: bool = False) -> None:
        if self.device is None:
            return
        screen = self.source().get("kind")
        m, msg = self._display_match()
        if m is not None and m.state:
            payload = to_device(m.state)
            if screen == "sim" or m.source == "sim":
                # Screen 2 is a simulation, never live: the CYD must not show the LIVE tag for it.
                payload["live"], payload["sim"] = False, True
                if not payload["series"]:
                    payload["series"] = "SIMULATION"
        else:
            payload = self.idle_payload(screen, msg or "Waiting for match data")
        if not force and payload == self.last_pushed:
            return
        try:
            await self.device.send_text(json.dumps(payload))
            self.last_pushed = payload
            if m is not None and m.state:
                with session() as s:
                    s.add(Snapshot(match_id=m.id, origin="hub", summary=summary(m.state), state=payload))
                    s.commit()
        except Exception as e:
            log.warning("push to CYD failed: %s", e)

    async def match_changed(self, match_id: int, state: dict | None = None) -> None:
        if state is None:
            with session() as s:
                m = s.get(Match, match_id)
                state = m.state if m else None
        if state is not None:
            await self.broadcast("match.update", {"id": match_id, "state": state})
        await self.push_display()

    # ---------------- device ----------------
    def device_status(self) -> dict:
        online = self.device is not None
        return {"online": online, "info": self.device_info, "lastSeen": self.device_seen or None,
                "telemetry": self.last_tm, "source": self.source()}

    async def device_connected(self, ws: WebSocket) -> None:
        if self.device is not None:
            try:
                await self.device.close()
            except Exception:
                pass
        self.device = ws
        self.device_seen = time.time()
        self.last_pushed = None
        await self.activity("device", "CYD connected to hub")
        await self.broadcast("device.status", self.device_status())

    async def device_message(self, msg: dict) -> None:
        self.device_seen = time.time()
        t = msg.get("t")
        if t == "wifi":
            self.device_info["wifi"] = {k: msg.get(k) for k in ("ssid", "ip", "rssi", "saved")}
            await self.broadcast("device.status", self.device_status())
            return
        if t == "hello":
            self.device_info = {k: msg.get(k) for k in ("fw", "mac", "ip", "board", "ssid")}
            self.device_info["link"] = "wire" if msg.get("uno") == "uart" else "wifi"
            await self.command("demo", {"on": False}, log_it=False)   # older firmware: stop its built-in loop
            await self.push_display(force=True)
        elif t == "tap":
            await self.toggle_screen()
        elif t == "tm":
            self.last_tm = {k: msg.get(k) for k in ("fps", "heap", "maxblk", "rssi", "uptime", "brightness", "showing", "rot")}
            self.last_tm["ts"] = time.time()
            with session() as s:
                s.add(DeviceTelemetry(device=self.device_info.get("mac") or "", fps=msg.get("fps", 0),
                                      heap=msg.get("heap", 0), maxblk=msg.get("maxblk", 0), rssi=msg.get("rssi", 0),
                                      uptime=msg.get("uptime", 0), brightness=msg.get("brightness", 0),
                                      showing=str(msg.get("showing", ""))[:80]))
                s.commit()
            await self.broadcast("device.telemetry", self.last_tm)
        elif t == "ack":
            fut = self.pending.pop(int(msg.get("id", -1)), None)
            if fut and not fut.done():
                fut.set_result(msg)
        elif t == "shown":
            with session() as s:
                s.add(Snapshot(origin="device", summary=str(msg.get("summary", ""))[:80], state=msg))
                s.commit()

    async def device_gone(self, ws: WebSocket) -> None:
        if self.device is ws:
            self.device = None
            await self.activity("device", "CYD disconnected")
            await self.broadcast("device.status", self.device_status())

    async def command(self, name: str, args: dict | None = None, log_it: bool = True, timeout: float = 4.0) -> dict:
        if name not in FW_COMMANDS:
            raise ValueError(f"unknown command {name}")
        args = args or {}
        row = None
        logged_args = {k: ("***" if k == "pass" else v) for k, v in args.items()}
        if log_it:
            with session() as s:
                row = CommandLog(name=name, args=logged_args)
                s.add(row)
                s.commit()
                s.refresh(row)
        if self.device is None:
            if row:
                self._finish(row.id, "offline", "CYD not connected")
                await self.broadcast("command.update", self.command_row(row.id))
            return {"status": "offline"}
        self.cmd_seq += 1
        cid = self.cmd_seq
        fut = asyncio.get_running_loop().create_future()
        self.pending[cid] = fut
        try:
            await self.device.send_text(json.dumps({"t": "cmd", "id": cid, "name": name, "args": args}))
        except Exception as e:
            self.pending.pop(cid, None)
            if row:
                self._finish(row.id, "failed", str(e))
            return {"status": "failed"}
        if row:
            await self.broadcast("command.update", self.command_row(row.id))
        try:
            ack = await asyncio.wait_for(fut, timeout)
            status = "acked" if ack.get("ok", True) else "failed"
            detail = str(ack.get("detail", ""))
        except asyncio.TimeoutError:
            self.pending.pop(cid, None)
            status, detail = "timeout", "no ack within %.0fs" % timeout
        if row:
            self._finish(row.id, status, detail)
            await self.broadcast("command.update", self.command_row(row.id))
        return {"status": status, "detail": detail}

    def _finish(self, cid: int, status: str, detail: str) -> None:
        with session() as s:
            r = s.get(CommandLog, cid)
            r.status, r.detail = status, detail
            if status == "acked":
                r.acked_at = now()
            s.add(r)
            s.commit()

    def command_row(self, cid: int) -> dict:
        with session() as s:
            r = s.get(CommandLog, cid)
            return r.model_dump(mode="json")

    # ---------------- simulation ----------------
    def start_sim(self, match_id: int, speed: str) -> None:
        self.sim_speed[match_id] = speed if speed in SIM_SPEEDS else "quick"
        if match_id in self.sims and not self.sims[match_id].done():
            return
        self.sims[match_id] = asyncio.create_task(self._run_sim(match_id))

    def stop_sim(self, match_id: int) -> None:
        t = self.sims.pop(match_id, None)
        if t:
            t.cancel()

    async def _run_sim(self, match_id: int) -> None:
        rng = random.Random()
        try:
            while True:
                with session() as s:
                    m = s.get(Match, match_id)
                if m is None or m.status != "live":
                    break
                eng = Engine(matches.meta_for(m))
                balls = matches.deliveries(match_id)
                state = eng.replay(balls)
                ctx = eng.next_delivery_context(balls)
                if ctx is None:
                    break
                kw = roll(situation_for(eng, state, ctx), rng)
                st = matches.add_ball(match_id, **kw)
                await self.match_changed(match_id, st)
                if st["ended"]:
                    await self.activity("sim", f"Simulation finished: {st['result']}")
                    break
                delay = SIM_SPEEDS[self.sim_speed.get(match_id, "quick")]
                if st.get("lastEvent") == "wicket":
                    delay *= 1.6
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("simulation %s crashed", match_id)
        finally:
            self.sims.pop(match_id, None)

    # ---------------- housekeeping ----------------
    async def watchdog(self) -> None:
        while True:
            await asyncio.sleep(5)
            if self.device is not None and time.time() - self.device_seen > 15:
                ws = self.device
                self.device = None
                try:
                    await ws.close()
                except Exception:
                    pass
                await self.activity("device", "CYD stopped responding")
                await self.broadcast("device.status", self.device_status())
            # prune telemetry older than 3 days
            if int(time.time()) % 600 < 5:
                with session() as s:
                    cutoff = now() - timedelta(days=3)
                    for r in s.exec(select(DeviceTelemetry).where(DeviceTelemetry.ts < cutoff)):
                        s.delete(r)
                    s.commit()

    async def on_usage(self) -> None:
        await self.broadcast("api.usage", cricapi.latest_usage())


hub = Hub()
