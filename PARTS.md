# UCIS Parts and Wiring

## Parts on hand
| Part | Detail | Used for |
|---|---|---|
| Arduino UNO Q | QRB2210 (Debian Linux, 4 GB LPDDR4, 32 GB eMMC) + STM32U585 MCU | runs the hub; MCU drives the UART to the CYD |
| CYD ESP32-2432S028R | Probots 2.8 in ILI9341 touch display, ESP32 | scoreboard + liquid win-% band |
| USB-C cable + 5 V 3 A supply | | powers the UNO Q, and the CYD through the UNO Q's 5V pin |
| micro-USB data cable | must be data, not charge-only | flashing the CYD |
| 1.25 mm 4-pin JST pigtails to male Dupont | not included with the CYD | P1 / P3 connectors |
| Multimeter | continuity beep | checking every wire before power-on |
| Laptop | Arduino App Lab or arduino-cli | building and flashing |
| Tape or marker | | tagging TX / RX wires |

No level shifter, resistors or breadboard: both sides are 3.3 V logic.

## UNO Q to CYD wiring (verified working, 2026-11-10)
CYD connector **P3** ("Extended IO", top left of the board), pins in order from GND:

| Wire | CYD P3 pin | UNO Q pin | Note |
|---|---|---|---|
| Black | GND | any GND | connect first |
| Blue | IO35 | D1 = TX1 (PB6, USART1_TX) | CYD receive; IO35 is input only |
| Yellow | IO22 | D0 = RX1 (PB7, USART1_RX) | CYD transmit |
| Red | IO21 | not connected | display backlight pin, leave loose |

### Powering the CYD from the UNO Q (optional, replaces the CYD's micro-USB)
Use a second pigtail on CYD connector **P1** (VIN, TX, RX, GND). Only VIN and GND go anywhere:

| Wire | CYD P1 pin | UNO Q pin | Note |
|---|---|---|---|
| Red | VIN | 5V header pin | CYD regulates it down to 3.3 V itself |
| Black | GND | any GND | |
| - | TX, RX | not connected | shared with the CYD's USB chip; tape them off |

- Never feed VIN while the CYD's micro-USB is plugged in: both are on the same 5 V rail and would fight.
  To flash the CYD, pull the red VIN wire first, flash over micro-USB, unplug micro-USB, then reconnect VIN.
- Never use the UNO Q 3.3V pin for this. The CYD draws about 100–300 mA (backlight + WiFi bursts).
- The UNO Q needs a supply that covers both boards (5 V 3 A on USB-C is enough). When it moves to battery,
  check that the battery path still delivers 5 V on the header at ~0.5 A extra.

UART: 115200 baud, 8N1, newline-terminated JSON lines. Transmit goes to receive, never TX to TX or RX to RX.
Do not use the P1 connector for signals (its TX/RX are shared with the USB chip). A faulty blue wire wasted a lot of time:
if one signal never arrives on any connector, swap that wire first.

## Checks before power-on
1. Multimeter on beep: each wire beeps end to end.
2. D0, D1 and GND must not beep against each other.
3. Unplug the UNO Q signal wires before flashing the CYD if the plug is ever on P1.

## Software
- CYD: `cricket_scoreboard/config.h` -> `#define FEED_MODE FEED_UART`, flash with micro-USB.
- UNO Q: open `uno_q_link/` in Arduino App Lab and run it (relays the hub's `/ws/device` to the wire).
- The UNO Q prints Zephyr boot text on D0/D1 at reset; the CYD ignores lines not starting with `{`.
- Loopback test sketches live in `tests/` (`uart_diag_cyd`, `uart_ping_unoq`). On the UNO Q, LED3 green = CYD answered ACK.
