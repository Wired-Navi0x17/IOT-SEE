// Hub link: the laptop (stage 2: UNO Q) pushes match state over WebSocket and sends commands.
// The CYD reports hello + telemetry and acks every command once the display loop has applied it.
#include "config.h"
#if FEED_MODE == FEED_HUB
#include "feed.h"
#include "device_cmd.h"
#include "state_json.h"
#include "secrets.h"
#include "wifi_setup.h"
#include <WiFiUdp.h>
#include <Arduino.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

#ifndef HUB_HOST
#define HUB_HOST ""
#endif

namespace {
WebSocketsClient ws;
WiFiUDP beacon;
constexpr uint16_t BEACON_PORT = 47800;
IPAddress beaconIp; uint16_t beaconPort = HUB_PORT; uint32_t beaconAt = 0;
uint32_t boundGen = 0, disconnectedAt = 0;
bool started = false, connected = false, pendingState = false;
uint32_t lastSeen = 0, lastTm = 0, lastResolve = 0;
IPAddress hubIp;
MatchState incoming;
char showing[48] = "";
char note[24] = "FINDING HUB";

void sendJson(JsonDocument& d) {
  String out; serializeJson(d, out); ws.sendTXT(out);
}

void sendWifi() {
  JsonDocument d;
  d["t"] = "wifi"; d["ssid"] = WiFi.SSID(); d["ip"] = WiFi.localIP().toString(); d["rssi"] = WiFi.RSSI();
  char saved[WIFI_MAX_SAVED][33]; int n = wifiSaved(saved, WIFI_MAX_SAVED);
  JsonArray a = d["saved"].to<JsonArray>();
  for (int i = 0; i < n; i++) a.add(saved[i]);
  sendJson(d);
}

void sendHello() {
  JsonDocument d;
  d["t"] = "hello"; d["fw"] = FW_VERSION; d["board"] = "ESP32-2432S028R";
  d["mac"] = WiFi.macAddress(); d["ip"] = WiFi.localIP().toString(); d["ssid"] = WiFi.SSID();
  sendJson(d);
  sendWifi();
}

void sendTelemetry() {
  JsonDocument d;
  d["t"] = "tm"; d["fps"] = roundf(g_fps * 10) / 10; d["heap"] = ESP.getFreeHeap(); d["maxblk"] = ESP.getMaxAllocHeap();
  d["rssi"] = WiFi.RSSI(); d["uptime"] = millis() / 1000; d["brightness"] = g_brightness; d["rot"] = g_rotation;
  d["showing"] = g_demoShow ? "DEMO" : showing; d["qr"] = (bool)g_qrShow;
  sendJson(d);
}

void ack(uint32_t id, bool ok, const char* detail) {
  JsonDocument d; d["t"] = "ack"; d["id"] = id; d["ok"] = ok; if (detail && *detail) d["detail"] = detail;
  sendJson(d);
}

void onCommand(JsonObjectConst o) {
  uint32_t id = o["id"] | 0;
  const char* name = o["name"] | "";
  JsonObjectConst a = o["args"];
  DeviceCmd c{Cmd::Ping, 0, id};
  if (!strcmp(name, "demo")) { g_demoShow = a["on"] | false; ack(id, true, g_demoShow ? "demo on" : "demo off"); return; }
  if (!strcmp(name, "ping"))            { ack(id, true, "pong"); return; }
  if (!strcmp(name, "wifi_add")) {
    bool ok = wifiAdd(a["ssid"] | "", a["pass"] | "");
    ack(id, ok, ok ? "saved" : "ssid required"); sendWifi(); return;
  }
  if (!strcmp(name, "wifi_forget")) {
    bool ok = wifiForget(a["ssid"] | "");
    ack(id, ok, ok ? "forgotten" : "not saved"); sendWifi(); return;
  }
  else if (!cmdFromJson(name, a, c)) { ack(id, false, "unknown command"); return; }
  if (!cmdPush(c)) ack(id, false, "queue full");
}

void onEvent(WStype_t type, uint8_t* payload, size_t len) {
  switch (type) {
    case WStype_CONNECTED:
      connected = true; lastSeen = millis(); note[0] = 0;
      Serial.println("[hub] connected");
      sendHello(); sendTelemetry();
      break;
    case WStype_DISCONNECTED:
      if (connected) { Serial.println("[hub] disconnected"); disconnectedAt = millis(); }
      connected = false; strcpy(note, "HUB OFFLINE");
      break;
    case WStype_TEXT: {
      lastSeen = millis();
      JsonDocument d;
      if (deserializeJson(d, payload, len)) break;
      const char* t = d["t"] | "";
      if (!strcmp(t, "state")) { parseStateJson(d.as<JsonObjectConst>(), incoming); pendingState = true; }
      else if (!strcmp(t, "cmd")) onCommand(d.as<JsonObjectConst>());
      break;
    }
    default: break;
  }
}

bool resolveHub() {
  lastResolve = millis();
  if (beaconAt && millis() - beaconAt < 15000) { hubIp = beaconIp; return true; }   // hub broadcast heard
  IPAddress ip = MDNS.queryHost(HUB_MDNS_NAME, 1500);
  if (ip != IPAddress(0, 0, 0, 0)) { hubIp = ip; return true; }
  if (strlen(HUB_HOST) && hubIp.fromString(HUB_HOST)) return true;
  return false;
}

void listenBeacon() {
  int len = beacon.parsePacket();
  while (len > 0) {
    char buf[48] = {0};
    beacon.read(buf, sizeof buf - 1);
    if (!strncmp(buf, "SEEV2HUB ", 9)) {
      IPAddress from = beacon.remoteIP();
      uint16_t port = atoi(buf + 9);
      bool moved = from != beaconIp;
      beaconIp = from; beaconPort = port ? port : HUB_PORT; beaconAt = millis();
      // The laptop changed address (new network): reconnect there.
      if (started && moved && (!connected || from != hubIp)) {
        Serial.printf("[hub] beacon from %s, reconnecting\n", from.toString().c_str());
        ws.disconnect(); started = false; lastResolve = 0;
      }
    }
    len = beacon.parsePacket();
  }
}

void start() {
  if (!resolveHub()) { strcpy(note, "FINDING HUB"); return; }
  Serial.printf("[hub] connecting to %s:%d\n", hubIp.toString().c_str(), HUB_PORT);
  ws.begin(hubIp, beaconAt ? beaconPort : HUB_PORT, "/ws/device");
  ws.onEvent(onEvent);
  ws.setReconnectInterval(3000);
  ws.enableHeartbeat(10000, 4000, 2);
  started = true;
}
} // namespace

uint32_t feedPoll(MatchState& s, bool& changed) {
  changed = false;
  static bool mdnsUp = false;
  if (WiFi.status() != WL_CONNECTED) {
    strcpy(note, wifiInSetup() ? "WIFI SETUP" : "NO WIFI");
  } else {
    if (boundGen != wifiGeneration()) {               // (re)joined a network: re-bind discovery
      boundGen = wifiGeneration();
      if (mdnsUp) MDNS.end();
      mdnsUp = MDNS.begin("cyd-scoreboard");
      beacon.stop(); beacon.begin(BEACON_PORT);
      if (started) { ws.disconnect(); started = false; }
      lastResolve = 0; beaconAt = 0;
    }
    listenBeacon();
    if (!started && millis() - lastResolve > 4000) start();
    if (started) ws.loop();
    while (true) {                                    // acks from the display loop
      DeviceAck a; if (!ackPop(a)) break;
      if (connected) ack(a.id, a.ok, a.detail);
    }
    if (connected && millis() - lastTm > 5000) { lastTm = millis(); sendTelemetry(); }
    if (g_tapPending) {                               // CYD tapped: the hub switches live <-> simulation
      g_tapPending = false;
      if (connected) { JsonDocument d; d["t"] = "tap"; sendJson(d); }
    }
  }
  // TEMPORARY exhibition demo: while it is up, the built-in chase plays; the hub state is kept
  // in `incoming` and shown again the moment the demo is switched off.
  static bool wasDemo = false; static uint32_t nextMock = 0;
  if (g_demoShow) {
    if (!wasDemo) { wasDemo = true; nextMock = 0; }
    if ((int32_t)(millis() - nextMock) >= 0) { nextMock = millis() + mockPoll(s); changed = true; }
    return 5;
  }
  if (wasDemo) { wasDemo = false; pendingState = true; if (!incoming.teamA[0] && !incoming.status[0]) strcpy(incoming.status, "Waiting for the hub..."); }
  if (pendingState) {
    pendingState = false;
    uint32_t v = s.version;
    s = incoming; s.version = v;
    changed = true;
  }
  return 10;
}

const char* feedLinkNote() {
  if (WiFi.status() != WL_CONNECTED) return wifiInSetup() ? "WIFI SETUP" : "NO WIFI";
  return connected ? nullptr : note;
}

void feedSetShowing(const char* summary) { strncpy(showing, summary, sizeof showing - 1); }
#endif
