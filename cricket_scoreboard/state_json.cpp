// JSON line format shared by the WiFi hub feed and the UART feed (same keys as hub service.to_device).
#include "state_json.h"
#include <string.h>
#include <stdlib.h>

void copyStr(char* dst, size_t n, JsonVariantConst v) {
  const char* s = v | "";
  strncpy(dst, s, n - 1); dst[n - 1] = 0;
}

static MatchEvent evFrom(const char* e) {
  if (!strcmp(e, "four")) return MatchEvent::Four;
  if (!strcmp(e, "six")) return MatchEvent::Six;
  if (!strcmp(e, "wicket")) return MatchEvent::Wicket;
  return MatchEvent::None;
}

void parseStateJson(JsonObjectConst o, MatchState& out) {
  MatchState n{};
  copyStr(n.series, sizeof n.series, o["series"]);
  copyStr(n.format, sizeof n.format, o["format"]);
  copyStr(n.teamA, sizeof n.teamA, o["a"]);
  copyStr(n.teamB, sizeof n.teamB, o["b"]);
  n.colA = strtoul(o["ca"] | "0", nullptr, 16); n.colB = strtoul(o["cb"] | "0", nullptr, 16);
  n.battingIsA = o["batA"] | true;
  n.innings = o["inn"] | 1;
  n.runs = o["r"] | 0; n.wkts = o["w"] | 0; n.balls = o["bl"] | 0;
  n.totalBalls = o["tb"] | 120; n.target = o["tgt"] | 0;
  copyStr(n.striker.name, sizeof n.striker.name, o["st"]["n"]);
  n.striker.runs = o["st"]["r"] | 0; n.striker.balls = o["st"]["b"] | 0;
  copyStr(n.nonStriker.name, sizeof n.nonStriker.name, o["ns"]["n"]);
  n.nonStriker.runs = o["ns"]["r"] | 0; n.nonStriker.balls = o["ns"]["b"] | 0;
  copyStr(n.bowler.name, sizeof n.bowler.name, o["bw"]["n"]);
  n.bowler.balls = o["bw"]["b"] | 0; n.bowler.maidens = o["bw"]["m"] | 0;
  n.bowler.runs = o["bw"]["r"] | 0; n.bowler.wkts = o["bw"]["w"] | 0;
  copyStr(n.nextBat, sizeof n.nextBat, o["nb"]);
  copyStr(n.nextBowl, sizeof n.nextBowl, o["nw"]);
  n.nThisOver = 0;
  for (JsonVariantConst c : o["ov"].as<JsonArrayConst>()) {
    if (n.nThisOver >= 8) break;
    copyStr(n.thisOver[n.nThisOver++], 4, c);
  }
  copyStr(n.status, sizeof n.status, o["status"]);
  n.live = o["live"] | false; n.ended = o["ended"] | false; n.hasPlayers = o["hp"] | false;
  n.lastEvent = evFrom(o["ev"] | "none"); n.eventSeq = o["es"] | 0;
  out = n;
}

bool cmdFromJson(const char* name, JsonObjectConst a, DeviceCmd& c) {
  if      (!strcmp(name, "brightness")) { c.cmd = Cmd::Brightness; c.arg = a["value"] | 200; }
  else if (!strcmp(name, "rotate"))     { c.cmd = Cmd::Rotate; c.arg = a["value"] | -1; }
  else if (!strcmp(name, "invert"))     { c.cmd = Cmd::Invert; c.arg = a["on"].is<bool>() ? (a["on"].as<bool>() ? 1 : 0) : -1; }
  else if (!strcmp(name, "identify"))   { c.cmd = Cmd::Identify; }
  else if (!strcmp(name, "reboot"))     { c.cmd = Cmd::Reboot; }
  else if (!strcmp(name, "qr")) {
    c.cmd = Cmd::Qr; c.arg = a["on"].is<bool>() ? (a["on"].as<bool>() ? 1 : 0) : -1;
    const char* url = a["url"] | "";
    if (*url) { strncpy(g_qrUrl, url, sizeof g_qrUrl - 1); g_qrUrl[sizeof g_qrUrl - 1] = 0; }
  }
  else return false;
  return true;
}
