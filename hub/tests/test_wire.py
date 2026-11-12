"""Everything done on the dashboard must reach the CYD over the wire.

The wired path is hub /ws/device -> uno_q_link relay -> UNO Q MCU -> UART -> CYD. The relay forwards
lines unchanged, so the hub's WebSocket messages are exactly what the CYD firmware parses. This test
plays the CYD at the WebSocket and holds every message to the firmware's limits:

- feed_uart.cpp drops any line longer than its 1536-byte buffer;
- uno_q_link/sketch drops non-ASCII bytes, which would corrupt the JSON;
- state_json.cpp only knows the command names in FIRMWARE_COMMANDS.
"""
import json
import os
import tempfile
import threading
import time

os.environ["HUB_DB"] = os.path.join(tempfile.mkdtemp(), "wire.db")

from fastapi.testclient import TestClient  # noqa: E402

from cricket_hub import service  # noqa: E402
from cricket_hub.main import app  # noqa: E402

LINE_MAX = 1536 - 1          # feed_uart.cpp line buffer, minus the terminating NUL
FIRMWARE_COMMANDS = {"brightness", "rotate", "invert", "identify", "reboot", "qr", "demo", "ping", "hello",
                     "wifi_add", "wifi_forget"}


class FakeCyd:
    """Acks commands like the firmware and records what arrives, checking each line on the way in."""

    def __init__(self, ws):
        self.ws, self.msgs, self.problems = ws, [], []
        self.lock = threading.Lock()
        self.stop = False
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        while not self.stop:
            try:
                raw = self.ws.receive_text()
            except Exception:
                return
            if len(raw.encode()) > LINE_MAX:
                self.problems.append(f"line too long ({len(raw.encode())} B): {raw[:80]}")
            if not raw.isascii():
                self.problems.append(f"non-ASCII: {raw[:80]}")
            m = json.loads(raw)
            if m.get("t") == "cmd":
                if m["name"] not in FIRMWARE_COMMANDS:
                    self.problems.append(f"firmware does not know {m['name']}")
                self.ws.send_text(json.dumps({"t": "ack", "id": m["id"], "ok": True, "detail": m["name"]}))
            with self.lock:
                self.msgs.append(m)

    def mark(self):
        with self.lock:
            return len(self.msgs)

    def wait_for(self, pred, since=0, timeout=5.0):
        end = time.time() + timeout
        while time.time() < end:
            with self.lock:
                for m in self.msgs[since:]:
                    if pred(m):
                        return m
            time.sleep(0.02)
        raise AssertionError("CYD never received the expected message")


def is_state(series=None):
    return lambda m: m.get("t") == "state" and (series is None or m["series"] == series)


def is_cmd(name):
    return lambda m: m.get("t") == "cmd" and m["name"] == name


def test_dashboard_actions_reach_the_cyd_over_the_wire():
    service.SIM_SPEEDS.update(quick=0.05, turbo=0.02, broadcast=0.2)
    with TestClient(app) as c:
        assert c.post("/api/auth/unlock", json={"pin": os.environ.get("HUB_PIN", "4817")}).status_code == 200
        with c.websocket_connect("/ws/device") as ws:
            ws.send_text(json.dumps({"t": "hello", "fw": "1.2.0", "board": "ESP32-2432S028R", "uno": "uart"}))
            cyd = FakeCyd(ws)
            try:
                # Power-on: the hub stops the old demo and shows Screen 1.
                cyd.wait_for(is_cmd("demo"))
                assert cyd.wait_for(is_state("LIVE"))["status"].startswith("No live IPL match")
                assert c.get("/api/device").json()["info"]["link"] == "wire"

                # Screen switch from the dashboard.
                n = cyd.mark()
                assert c.post("/api/device/source", json={"kind": "sim"}).status_code == 200
                cyd.wait_for(is_state("SIMULATION"), n)
                n = cyd.mark()
                c.post("/api/device/source", json={"kind": "live"})
                cyd.wait_for(is_state("LIVE"), n)

                # Simulation set up on the dashboard: teams, batting order, bowlers.
                teams = c.get("/api/teams").json()
                a, b = teams[0]["id"], teams[1]["id"]
                xi_a = c.get(f"/api/teams/{a}/default_xi").json()
                xi_b = c.get(f"/api/teams/{b}/default_xi").json()
                order_a = xi_a["xi"][::-1]
                n = cyd.mark()
                r = c.post("/api/sim", json={"team_a_id": a, "team_b_id": b, "xi_a": order_a, "xi_b": xi_b["xi"],
                                              "bowlers_a": xi_a["bowlers"], "bowlers_b": xi_b["bowlers"],
                                              "overs": 2, "speed": "broadcast"})
                assert r.status_code == 200, r.text
                mid = r.json()["id"]
                first = cyd.wait_for(lambda m: m.get("t") == "state" and m["a"] == teams[0]["short"], n)
                opener = r.json()["state"]["striker"]["name"]
                assert first["st"]["n"] and opener.split()[-1].upper()[:3] in first["st"]["n"].upper()

                # Pause holds the score on the CYD; resume and speed change keep it moving.
                c.post(f"/api/sim/{mid}/pause")
                time.sleep(0.5)
                n = cyd.mark()
                time.sleep(0.8)
                assert not [m for m in cyd.msgs[n:] if m.get("t") == "state" and m.get("ev") not in (None, "none")
                            and m.get("bl", 0) > first.get("bl", 0) + 40]
                c.post(f"/api/sim/{mid}/resume")
                c.post(f"/api/sim/{mid}/speed", json={"speed": "turbo"})
                cyd.wait_for(lambda m: m.get("t") == "state" and m["bl"] >= 6 and m["a"] == teams[0]["short"], n)

                # Manual scoring from the dashboard.
                m2 = c.post("/api/matches", json={"team_a_id": teams[2]["id"], "team_b_id": teams[3]["id"], "overs": 2}).json()
                c.post(f"/api/matches/{m2['id']}/start", json={})
                n = cyd.mark()
                c.post("/api/device/source", json={"kind": "match", "match_id": m2["id"]})
                c.post(f"/api/matches/{m2['id']}/ball", json={"runs_bat": 4})
                four = cyd.wait_for(lambda m: m.get("t") == "state" and m["a"] == teams[2]["short"] and m["r"] == 4, n)
                assert four["ev"] == "four"

                # Device controls.
                for name, args in [("brightness", {"value": 120}), ("identify", {}), ("rotate", {}),
                                   ("invert", {}), ("qr", {"on": True, "url": "http://10.42.0.1:8000/"}),
                                   ("qr", {"on": False})]:
                    n = cyd.mark()
                    res = c.post("/api/device/command", json={"name": name, "args": args})
                    assert res.status_code == 200 and res.json()["status"] == "acked", (name, res.text)
                    assert cyd.wait_for(is_cmd(name), n)["args"] == args

                # A tap on the CYD switches screens, as the dashboard's Screen select does.
                n = cyd.mark()
                ws.send_text(json.dumps({"t": "tap"}))
                cyd.wait_for(lambda m: m.get("t") == "state", n)
                assert c.get("/api/device").json()["source"]["kind"] in ("live", "sim")

                assert cyd.problems == [], cyd.problems
                biggest = max(len(json.dumps(m)) for m in cyd.msgs if m.get("t") == "state")
                assert biggest < LINE_MAX
            finally:
                cyd.stop = True
