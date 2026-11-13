#pragma once
// ---------------- User configuration ----------------

#define FEED_MOCK    0   // built-in simulated chase, no network
#define FEED_CRICAPI 1   // CYD calls CricketData.org itself (needs CRICAPI_KEY)
#define FEED_HUB     2   // laptop hub pushes state over WebSocket (default)
#define FEED_UART    3   // UNO Q pushes the same JSON lines over a wire (Serial2, see feed_uart.cpp)
#define FEED_MODE    FEED_UART

// UART link to the UNO Q (FEED_UART). CYD connector P3: IO35 = RX (input only), IO22 = TX.
#define UART_RX_PIN 35
#define UART_TX_PIN 22
#define UART_BAUD   115200

#define HUB_MDNS_NAME "cricket-hub"   // resolved as cricket-hub.local
#define HUB_PORT      8000
#define FW_VERSION    "1.2.1-expo"

// TEMPORARY (exhibition, 2026-11-13): a tap or long press on the CYD toggles the built-in
// demo scoreboard (simulated chase) on top of the hub feed. Any "Show on CYD" / screen change
// from the dashboard switches the demo off again. Set to 0 after the exhibition.
#define EXHIBITION_DEMO 1

// 1 or 3 = landscape. Flip if the picture is upside down.
#define SCREEN_ROTATION 1

// POSIX timezone for the clock (India = IST-5:30)
#define TZ_INFO "IST-5:30"

// Only follow matches whose name contains this text ("" = any live match)
#define TEAM_FILTER ""

// Par scores used by the 1st-innings win-probability model
#define PAR_T20 165
#define PAR_ODI 280

// CricketData.org free plan = 100 requests/day. 90 s polling ~ 2.5 h of live coverage.
#define POLL_LIVE_MS 90000UL
#define POLL_IDLE_MS 600000UL
