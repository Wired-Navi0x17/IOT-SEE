"""CYD Link: makes the CYD on the UART look like a WiFi device to the cricket hub.

hub /ws/device  <-- WebSocket -->  this relay  <-- Bridge -->  MCU sketch  <-- UART -->  CYD
The hub needs no changes: it sees one device connection, exactly as when the CYD joins over WiFi.

HUB_WS: where the hub listens. Default: port 8000 on the UNO Q host (hub or adb-reverse tunnel).
"""
import asyncio
import json
import os
import threading

import websockets
from arduino.app_utils import App, Bridge

def _gateway() -> str:
    """App Lab runs this app in its own container network; the UNO Q host is the default gateway."""
    try:
        with open("/proc/net/route") as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if parts[1] == "00000000":
                    g = int(parts[2], 16)
                    return ".".join(str((g >> (8 * i)) & 255) for i in range(4))
    except OSError:
        pass
    return "127.0.0.1"


# The hub's device socket. On the UNO Q host, port 8000 is either the hub itself or an
# `adb reverse tcp:8000 tcp:8000` tunnel to the hub on the laptop.
HUB_WS = os.environ.get("HUB_WS", f"ws://{_gateway()}:8000/ws/device")
CHUNK = 200                     # Bridge payloads are capped at 256 bytes

loop = asyncio.new_event_loop()
from_cyd: asyncio.Queue = asyncio.Queue()
_partial = ""


def on_cyd_part(chunk: str):
    """Bridge callback (MCU -> Linux). Reassemble lines, keep only JSON objects."""
    global _partial
    _partial += chunk
    while "\n" in _partial:
        line, _partial = _partial.split("\n", 1)
        line = line.strip()
        if line.startswith("{"):
            loop.call_soon_threadsafe(from_cyd.put_nowait, line)
    if len(_partial) > 4096:     # garbage with no newline
        _partial = ""


def to_cyd(line: str):
    data = line.rstrip("\n") + "\n"
    for i in range(0, len(data), CHUNK):
        Bridge.call("cyd_write", data[i:i + CHUNK])


async def relay():
    while True:
        try:
            async with websockets.connect(HUB_WS, ping_interval=10) as ws:
                print("[link] hub connected", HUB_WS, flush=True)
                # ask the CYD to introduce itself so the hub learns fw/board right away
                await asyncio.to_thread(to_cyd, json.dumps({"t": "cmd", "id": 0, "name": "hello", "args": {}}))

                async def up():
                    while True:
                        await ws.send(await from_cyd.get())

                async def down():
                    async for msg in ws:
                        await asyncio.to_thread(to_cyd, msg)

                await asyncio.gather(up(), down())
        except Exception as e:  # hub restarting, network, Bridge hiccup: retry
            print("[link] hub link down:", e, flush=True)
            await asyncio.sleep(3)


Bridge.provide("cyd_part", on_cyd_part)
threading.Thread(target=lambda: loop.run_until_complete(relay()), daemon=True).start()
App.run()
