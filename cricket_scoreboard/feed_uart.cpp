// UART link: the hub on the UNO Q (via its MCU sketch, uno_q_link) sends one JSON object per line,
// exactly the WebSocket messages: {"t":"state",...} and {"t":"cmd",...}.
// The CYD answers on the same wire with hello / tm / ack lines.
// Wiring (3.3 V both sides): UNO Q D1 (TX) -> CYD P3 IO35, CYD P3 IO22 -> UNO Q D0 (RX), GND -> GND.
#include "config.h"
#if FEED_MODE == FEED_UART
#include "feed.h"
#include "state_json.h"
#include <Arduino.h>
#include <WiFi.h>

namespace {
HardwareSerial& uno = Serial2;
char line[1536]; size_t len = 0; bool overflow = false;
MatchState incoming;
bool pending = false, begun = false;
uint32_t lastSeen = 0, lastTm = 0;
char showing[48] = "";

void sendJson(JsonDocument& d) { serializeJson(d, uno); uno.print('\n'); }

void ack(uint32_t id, bool ok, const char* detail) {
  JsonDocument d; d["t"] = "ack"; d["id"] = id; d["ok"] = ok; if (detail && *detail) d["detail"] = detail;
  sendJson(d);
}

void sendHello() {
  JsonDocument d;
  d["t"] = "hello"; d["fw"] = FW_VERSION; d["board"] = "ESP32-2432S028R"; d["uno"] = "uart";
  d["mac"] = WiFi.macAddress();
  sendJson(d);
}

void sendTelemetry() {
  JsonDocument d;
  d["t"] = "tm"; d["fps"] = roundf(g_fps * 10) / 10; d["heap"] = ESP.getFreeHeap(); d["maxblk"] = ESP.getMaxAllocHeap();
  d["uptime"] = millis() / 1000; d["brightness"] = g_brightness; d["rot"] = g_rotation;
  d["showing"] = showing;
  sendJson(d);
}

void onLine(const char* s, size_t n) {
  if (n == 0 || s[0] != '{') return;               // UNO Q boot console text etc.
  JsonDocument d;
  if (deserializeJson(d, s, n)) { Serial.println("[uart] bad JSON line"); return; }
  lastSeen = millis();
  const char* t = d["t"] | "";
  if (!strcmp(t, "state")) { parseStateJson(d.as<JsonObjectConst>(), incoming); pending = true; return; }
  if (strcmp(t, "cmd")) return;
  uint32_t id = d["id"] | 0;
  const char* name = d["name"] | "";
  JsonObjectConst a = d["args"];
  if (!strcmp(name, "ping")) { ack(id, true, "pong"); return; }
  if (!strcmp(name, "hello")) { sendHello(); ack(id, true, "hello"); return; }
  if (!strcmp(name, "demo")) { ack(id, true, "no demo: hub data only"); return; }   // legacy command
  DeviceCmd c{Cmd::Ping, 0, id};
  if (!cmdFromJson(name, a, c)) { ack(id, false, "unknown command"); return; }
  if (!cmdPush(c)) ack(id, false, "queue full");
}

void pump() {
  while (uno.available()) {
    char ch = (char)uno.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      if (!overflow) onLine(line, len);
      len = 0; overflow = false;
    } else if (len < sizeof line - 1) line[len++] = ch;
    else overflow = true;                           // drop the whole oversized line
  }
}
} // namespace

uint32_t feedPoll(MatchState& s, bool& changed) {
  changed = false;
  if (!begun) {
    uno.setRxBufferSize(4096);
    uno.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
    begun = true;
    sendHello();
  }
  pump();
  while (true) { DeviceAck a; if (!ackPop(a)) break; ack(a.id, a.ok, a.detail); }
  if (millis() - lastTm > 5000) { lastTm = millis(); sendTelemetry(); }

  if (g_tapPending) {                               // CYD tapped: the hub switches Screen 1 <-> Screen 2
    g_tapPending = false;
    JsonDocument d; d["t"] = "tap"; sendJson(d);
  }
  if (pending) {
    pending = false;
    uint32_t v = s.version; s = incoming; s.version = v;
    changed = true;
  }
  return 5;
}

const char* feedLinkNote() {
  if (!lastSeen) return "WAITING UNO Q";
  return millis() - lastSeen > 15000 ? "UNO Q SILENT" : nullptr;
}

void feedSetShowing(const char* summary) { strncpy(showing, summary, sizeof showing - 1); }
#endif
