# SEEv2 Cricket Box: product requirements and design

Date: 2026-11-10
Status: draft for review

## 1. What this is, in one paragraph

A self-contained IPL cricket box. An Arduino UNO Q does all of the computing: it fetches live IPL scores,
holds every IPL player's career record, runs a ball-by-ball match simulator, and serves a web dashboard.
A CYD touch display wired to it shows either the live match or a simulated one. An Android app and the web
dashboard control everything over WiFi. No PC is involved once it is set up. Its signature feature is the
**what-if replay**: load a real IPL match, change one decision, and watch the alternate history play out
next to what really happened.

## 2. Why

- It is the SEEv2 project (SOCSE, RV University). It has to work reliably in a demo room and make people
  say "that's cool", not just "that works".
- The UNO Q is powerful enough to be the whole brain. Today the hub runs on a laptop and the UNO Q only
  relays data over a USB tunnel; the goal is to remove the laptop entirely.
- The project is IPL only: 10 franchises, team colours chosen per fixture (already built).

## 3. Goals, non-goals, anti-goals

**Goals**
1. Power on the box and, with no PC, see the live IPL match (or "No live IPL match") within a minute.
2. Switch to a custom simulated match from the CYD, the app or the dashboard.
3. Simulations driven by each player's real IPL career record, shown as game-style rating cards that can be
   adjusted.
4. What-if replay of real historical IPL matches (signature feature).
5. A crowd prediction game anyone in the room can join from their phone.
6. The Android app and the web dashboard offer the same controls.

**Non-goals (decided)**
- Phone motion as bat or ball (idea #2): dropped.
- Spoken or written AI commentary (idea #4): dropped. The CYD has a speaker connector but no speaker.
- iOS app, user accounts, cloud hosting.

**Anti-goals: it fails even if it technically works when...**
- It needs the laptop at the demo.
- Simulation or what-if replay stops working because the internet is down. Only the live screen may
  depend on the internet.
- The prediction game feels like betting: no money, no stakes, no real-world rewards.
- It shows made-up players as if they were real. Player names come from real data or are clearly marked.

## 4. The hardware and how it fits together

| Part | Role |
|---|---|
| UNO Q, Linux side (QRB2210, 4 GB) | The hub: live API polling, player database, simulator, what-if engine, prediction game, web dashboard, API for the app |
| UNO Q, MCU side (STM32U585) | Relays data between the hub and the CYD over the D0/D1 UART |
| CYD (ESP32-2432S028R, 320x240 touch) | Screen 1 (live) and Screen 2 (simulation), touch to switch |
| Android phone | The app (Tauri 2) |
| Any phone or laptop browser | The web dashboard, served by the UNO Q |

Verified today: hub to UNO Q relay to CYD over UART works end to end (state, commands, acks, telemetry).
Wiring is in `PARTS.md` and `docs/CYD_UnoQ_Wiring.docx`.

## 5. Features

### F1. Screen 1: live IPL match (CYD)
- On boot the CYD shows the current live IPL match from CricketData.org: score, overs, batters, bowler,
  this over, target and required rate, and the win-probability liquid band in the two teams' colours.
- With no live IPL match it shows "No live IPL match" and the next scheduled IPL fixture if the API gives it.
- The free API plan allows 100 requests a day; polling every 90 s while live gives about 2.5 hours of
  coverage. The hub owns the API key and the request budget, and shows usage on the dashboard.
- The API key, polling interval and IPL filter are editable from the app and the dashboard ("change the
  API").

### F2. Screen 2: custom simulated match (CYD)
- Reached by tapping the CYD on Screen 1, or from the app or the dashboard. Tapping again returns to Screen 1.
- Any IPL team against any IPL team.
- In the app or dashboard, pick the playing XI, the batting order and which players bowl.
- The match plays ball by ball on the CYD with speed control (slow, normal, fast) and pause.
- Uses the existing scoring engine and win-probability model, extended with the player ratings from F3.

### F3. Player rating cards ("gamified" stats)
- Every IPL player gets a game-style card built from their real IPL career (Cricsheet ball-by-ball data,
  2008 to 2026). Example for Virat Kohli: batting average, strike rate, boundary rate, dot-ball rate, how
  often he gets out, split by phase (powerplay, middle overs, death overs); for bowlers: economy, wicket
  rate, dot-ball rate, also by phase.
- The card shows a few headline ratings (for example out of 99, like a video game) derived from those stats.
- Ratings can be adjusted with sliders before a simulation and reset to the real values. Adjusted cards are
  clearly marked as adjusted.
- The simulator uses these numbers to decide each ball's outcome.

### F4. What-if replay (signature feature)
- Pick any IPL match from history (Cricsheet). The real match loads ball by ball.
- Scrub to any ball and change one thing: swap a player in or out, change the batting order, or change who
  bowls an over.
- The UNO Q replays the rest of the match from that ball using the F3 ratings.
- The CYD's liquid band and the dashboard's win-probability chart show two lines: what really happened and
  the alternate history.
- Run the alternate many times and report the spread, for example "MI won 62 of 100 alternate replays".
- Works fully offline.

### F5. Crowd prediction game
- During a match, anyone in the room joins the game from their phone browser. No app install, no login,
  just a nickname.
- They predict what happens next; the UNO Q scores the predictions and shows a leaderboard on the dashboard.
- For simulated and what-if matches, predictions are per ball (dot, runs, boundary, wicket); the simulator
  waits a few seconds for predictions before each ball.
- For live matches, predictions are per over (runs in the over, wicket or not), because the free API only
  gives a new score every 90 s.

### F6. Android app and web dashboard, same controls
Both offer:
- Switch the CYD between Screen 1 and Screen 2.
- Set up simulations (teams, XI, order, bowlers, speed) and what-if replays.
- Browse and adjust player cards.
- API settings (key, polling, budget view).
- Device controls already built in the hub: brightness, rotation, identify, reboot, device status.
- The prediction game view and leaderboard.

The app is built with Tauri 2 for Android. The dashboard is the existing React web app, served by the UNO Q.
Both talk to the same hub API on the UNO Q over WiFi.

### F7. No PC: everything runs on the UNO Q
- Move the hub (FastAPI, SQLite, scoring engine, simulator, API poller) onto the UNO Q's Linux side and
  start it on boot.
- Serve the dashboard from the UNO Q.
- The CYD relay (`uno_q_link`, an App Lab app) talks to the hub on the same board; the laptop and the USB
  tunnel go away.
- The UNO Q joins WiFi for the live API and so the app and phones can reach it.

## 6. Constraints and known facts

- **UNO Q software:** App Lab builds sketches with board package arduino:zephyr 0.52.0. In that version the
  D0/D1 header is `Serial` and `Serial1` belongs to the Bridge (in 1.1.0 they are swapped). Flashing the
  MCU from a laptop with 1.1.0 breaks App Lab flashing until the 0.52.0 loader is restored.
- **Bridge messages are capped at 256 bytes;** the relay splits lines into chunks.
- **The UNO Q has no internet yet** (WiFi not configured). App Lab apps run in Docker containers and cannot
  download libraries offline; the base image already has Python `websockets`.
- **CYD:** 320x240 touch, IPL team colours per fixture, IO35 receive and IO22 transmit on connector P3.
  IO21 is the backlight. The CYD needs its own power today (micro-USB); powering it from the UNO Q needs a
  second 4-pin 1.25 mm pigtail on P1 (VIN and GND).
- **Live data:** CricketData.org free plan, 100 requests a day, score snapshots rather than every ball.
- **History data:** Cricsheet IPL ball-by-ball data. Attribution is required (licence believed to be
  CC BY 4.0; to be confirmed on cricsheet.org).
- **IPL 2026 squads:** not yet provided. Needed for current team lists; Cricsheet covers players' history.

## 7. Decided by the project owner

- IPL only; 10 franchises; team colours per fixture.
- All computation on the UNO Q; no PC at runtime.
- Screen 1 live (or "No live IPL match"), Screen 2 simulation, switch by CYD touch, app or dashboard.
- Player stats from full match history, as game-style adjustable cards.
- Android app built with a Rust framework like the opencode team used (Tauri), and a web dashboard with
  the same functions.
- Include the what-if replay and the crowd prediction game. Leave out phone motion control and commentary.

## 8. Calls made by the designer (please check)

- Tauri 2 for the Android app. (opencode itself moved from Tauri to Electron for their own reasons; Tauri
  still fits a phone app best.)
- Keep the hub in Python (existing code) and move it onto the UNO Q, rather than rewriting it in Rust.
- Cricsheet as the source of player history.
- Live-match predictions per over, simulated-match predictions per ball.
- Ratings shown out of 99, with sliders and a reset.
- Dashboard served by the UNO Q on port 8000.
- Controls that change things (API settings, simulations, device commands) stay behind the hub's existing
  admin PIN; joining the prediction game needs no PIN.
- Screen 2 with no simulation set up shows the last simulation, or "Set up a match in the app" if there
  has never been one.
- Android is the only app target (iOS stays a non-goal).

## 9. Open questions

1. Does the CYD stay wired to the UNO Q, or connect over WiFi? (Both are already built in the firmware.)
2. At the demo, does the UNO Q join an existing WiFi network, or create its own hotspot that phones join?
3. The IPL 2026 squad lists.

## 10. Proposed extras, not yet agreed

- The CYD shows a QR code for the crowd game, so phones can join by scanning.
- The UNO Q's built-in LED matrix flashes on fours, sixes and wickets.

## 11. Left to the builder

- Simulator internals (how ratings turn into ball outcome probabilities), within the F3 data.
- Database schema for players, matches and predictions.
- Exact screen layouts for the CYD's two screens and the app.
- How the Cricsheet data gets onto the UNO Q (copied over USB or downloaded once over WiFi).
