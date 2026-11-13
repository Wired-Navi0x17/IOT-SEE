"""Tiny client for the DesignCraft control port (JSON lines)."""
import json, socket

class DC:
    def __init__(self, port=47815):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=120)
        self.f = self.s.makefile("rwb")
        self.n = 0

    def call(self, method, params=None):
        self.n += 1
        self.f.write(json.dumps({"id": self.n, "method": method, "params": params or {}}).encode() + b"\n")
        self.f.flush()
        r = json.loads(self.f.readline())
        if "error" in r:
            raise RuntimeError(f"{method} {params}: {r['error']}")
        return r.get("result")

    def cmd(self, cid, **params):
        return self.call("command", {"id": cid, "params": params})
