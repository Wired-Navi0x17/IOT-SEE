# SEEv2 Cricket Box

An IPL scoreboard box. An **Arduino UNO Q** runs everything: the hub (FastAPI + SQLite), the
match simulator and the web dashboard. A **CYD** (ESP32-2432S028R, 2.8" touch TFT) is the
screen. No PC is needed at runtime.

- **Screen 1 (live):** the live IPL match, or "No live IPL match" with the next fixture.
- **Screen 2 (simulation):** any IPL team v any other. On the dashboard you pick each XI, the
  batting order and who bowls, then set the pace (4 s / 1.2 s / 0.25 s per ball) or pause.
- **Tap the CYD** to switch screens. Long-press it to show a QR code for the dashboard.

Parts list, wiring and power-on checks: [`PARTS.md`](PARTS.md) and
[`docs/CYD_UnoQ_Wiring.docx`](docs/CYD_UnoQ_Wiring.docx). Feature spec:
[`docs/superpowers/specs/`](docs/superpowers/specs/).

## Layout

| Path | What it is |
|---|---|
| `hub/` | Python hub: REST + WebSocket API, scoring engine, simulator, CricketData poller. Serves the built dashboard from `hub/static/`. |
| `web/` | Dashboard source (React 19, Vite, Tailwind 4). `npm run build` writes into `hub/static/`. |
| `cricket_scoreboard/` | CYD firmware (Arduino, ESP32 core). |
| `uno_q_link/` | Arduino App Lab app for the UNO Q: relays the hub's `/ws/device` to the CYD over UART. |
| `tests/` | Wiring and UART probe sketches for both boards. |
| `tools/` | Font converter (`make_vlw.py`) and the Geist fonts it uses. |

## Wiring (CYD P3 connector ↔ UNO Q)

| CYD | Wire | UNO Q |
|---|---|---|
| IO35 (RX) | blue | D1 (TX) |
| IO22 (TX) | yellow | D0 (RX) |
| GND | black | GND |

UART at 115200 8N1. In the UNO Q's `arduino:zephyr` 0.52.0 core (App Lab), D0/D1 are `Serial`
and `Serial1` is the Bridge. Do not flash the UNO Q MCU from a PC with core 1.1.0, because that
breaks App Lab.

## Build and run

### Hub (on a PC for development)
```sh
cd hub
cp .env.example .env          # set HUB_PIN; CRICAPI_KEY is optional (free key at cricketdata.org)
uv sync
uv run hub                   # http://localhost:8000, admin PIN from .env
uv run pytest
```
On first start it seeds the 10 IPL franchises with placeholder squads. It never creates fake
fixtures or results.

### Dashboard
```sh
cd web && npm ci && npm run build      # dev server: npm run dev (proxies to :8000)
```

### Hub on the UNO Q (Docker, no root needed)
```sh
adb push hub /home/arduino/seev2/hub
adb shell docker run -d --name seev2-hub --network host --restart unless-stopped \
  -v /home/arduino/seev2:/home/arduino/seev2 -w /home/arduino/seev2/hub \
  -e HUB_ADVERTISE_IP=10.42.0.1 ghcr.io/arduino/app-bricks/python-apps-base:0.5.0 \
  sh -c ".venv/bin/hub"
```
The board also runs a hotspot (`10.42.0.1`), so a phone can open the dashboard at `http://10.42.0.1:8000`.

### CYD firmware
```sh
cp cricket_scoreboard/secrets.example.h cricket_scoreboard/secrets.h
# config.h: FEED_MODE FEED_UART (wired, default) or FEED_HUB (WiFi to the hub)
arduino-cli compile -b esp32:esp32:esp32:PartitionScheme=huge_app -u -p /dev/ttyUSB0 cricket_scoreboard
```
Libraries: TFT_eSPI (configured by `display_config.h`), ArduinoJson 7, WebSockets, XPT2046_Touchscreen, qrcode.

### UNO Q link app
Copy `uno_q_link/` into Arduino App Lab and run it. It connects to the hub on the board and
passes JSON lines both ways over D0/D1.

## Data
Live scores come from CricketData.org (the free plan allows 100 calls a day, and the hub counts
them). Player cards use Cricsheet ball-by-ball data (CC BY 4.0).
