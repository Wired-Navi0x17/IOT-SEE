// Live feed from CricketData.org (api.cricapi.com) "currentMatches" endpoint (free plan: 100 hits/day).
// The free endpoint gives team scores + status text, not batters/bowlers, so hasPlayers = false
// and the players panel shows the match status instead.
#include "config.h"
#if FEED_MODE == FEED_CRICAPI
#include "feed.h"
#include "secrets.h"
#include "ipl_teams.h"
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ctype.h>

namespace {
String   s_matchId;
bool     s_havePrev = false;
MatchState s_prev;
uint32_t s_seq = 0;

void upcopy(char* dst, size_t n, const char* src) {
  size_t i = 0;
  for (; src && src[i] && i < n - 1; i++) dst[i] = toupper((unsigned char)src[i]);
  dst[i] = 0;
}

void setStatus(MatchState& s, const char* msg) {
  strncpy(s.status, msg, sizeof s.status - 1); s.status[sizeof s.status - 1] = 0;
}

int oversToBalls(float o) {
  int whole = (int)o;
  return whole * 6 + (int)lroundf((o - whole) * 10.0f);
}

const char* shortFor(JsonArrayConst teamInfo, const char* name, char* buf) {
  if (const char* c = iplCode(name)) { strcpy(buf, c); return buf; }
  for (JsonObjectConst ti : teamInfo)
    if (strcmp(ti["name"] | "", name) == 0 && ti["shortname"].is<const char*>()) {
      upcopy(buf, 6, ti["shortname"]); return buf;
    }
  upcopy(buf, 4, name); return buf;
}

int scoreMatch(JsonObjectConst m) {
  if (!(m["matchStarted"] | false)) return -1;
  JsonArrayConst sc = m["score"];
  if (sc.size() == 0) return -1;
  if (!iplCode(m["teams"][0] | "") || !iplCode(m["teams"][1] | "")) return -1;   // IPL only
  int v = 0;
  if (!(m["matchEnded"] | false)) v += 1000;
  if (strlen(TEAM_FILTER) && strstr(m["name"] | "", TEAM_FILTER)) v += 500;
  const char* mt = m["matchType"] | "";
  if (!strcmp(mt, "t20")) v += 20; else if (!strcmp(mt, "odi")) v += 10;
  if (s_matchId.length() && s_matchId == (m["id"] | "")) v += 5;   // stickiness
  return v;
}
} // namespace

static uint32_t cricapiPoll(MatchState& s) {
  if (!strlen(CRICAPI_KEY)) { setStatus(s, "Set CRICAPI_KEY in secrets.h"); s.version++; return 60000; }
  if (WiFi.status() != WL_CONNECTED) { setStatus(s, "Connecting to WiFi..."); return 5000; }

  WiFiClientSecure client; client.setInsecure();   // no cert pinning (keeps it simple)
  HTTPClient http; http.useHTTP10(true); http.setTimeout(15000);
  String url = String("https://api.cricapi.com/v1/currentMatches?apikey=") + CRICAPI_KEY + "&offset=0";
  if (!http.begin(client, url)) { setStatus(s, "HTTP begin failed"); return 30000; }
  int code = http.GET();
  if (code != 200) {
    Serial.printf("[cricapi] HTTP %d\n", code);
    char m[48]; snprintf(m, sizeof m, "API error HTTP %d", code); setStatus(s, m);
    http.end(); return 60000;
  }

  JsonDocument filter;
  filter["status"] = true; filter["reason"] = true;
  filter["info"]["hitsToday"] = true; filter["info"]["hitsLimit"] = true;
  JsonObject f = filter["data"][0].to<JsonObject>();
  for (const char* k : {"id", "name", "matchType", "status", "teams", "score", "matchStarted", "matchEnded"}) f[k] = true;
  f["teamInfo"][0]["name"] = true; f["teamInfo"][0]["shortname"] = true;

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, http.getStream(), DeserializationOption::Filter(filter));
  http.end();
  if (err) { Serial.printf("[cricapi] JSON %s\n", err.c_str()); setStatus(s, "Bad JSON from API"); return 60000; }

  int hits = doc["info"]["hitsToday"] | 0, limit = doc["info"]["hitsLimit"] | 100;
  Serial.printf("[cricapi] status=%s hits %d/%d free heap %u\n", doc["status"] | "?", hits, limit, ESP.getFreeHeap());
  if (strcmp(doc["status"] | "", "success") != 0) {
    setStatus(s, doc["reason"] | "API failure"); s.version++; return 30 * 60000UL;
  }

  JsonObjectConst best; int bestScore = -1;
  for (JsonObjectConst m : doc["data"].as<JsonArrayConst>()) {
    int v = scoreMatch(m); if (v > bestScore) { bestScore = v; best = m; }
  }
  if (bestScore < 0) {
    s.live = false; s.ended = false; setStatus(s, "No live IPL match right now");
    return POLL_IDLE_MS;
  }

  MatchState n{};
  n.version = s.version;
  JsonArrayConst teams = best["teams"], info = best["teamInfo"], score = best["score"];
  const char* t0 = teams[0] | "Team A"; const char* t1 = teams[1] | "Team B";
  char buf[8];
  strcpy(n.teamA, shortFor(info, t0, buf)); strcpy(n.teamB, shortFor(info, t1, buf));

  const char* mt = best["matchType"] | "t20";
  if (!strcmp(mt, "odi")) { strcpy(n.format, "ODI"); n.totalBalls = 300; }
  else if (!strcmp(mt, "test")) { strcpy(n.format, "TEST"); n.totalBalls = 0; }
  else { strcpy(n.format, "T20"); n.totalBalls = 120; }

  // Series = name after the 2nd comma: "A vs B, 3rd T20I, India tour of Australia, 2026"
  const char* name = best["name"] | "";
  const char* p = strchr(name, ','); if (p) p = strchr(p + 1, ',');
  upcopy(n.series, sizeof n.series, p ? p + 2 : name);
  char* c = strrchr(n.series, ','); if (c) *c = 0;          // drop trailing ", 2026"

  JsonObjectConst last = score[score.size() - 1];
  const char* inning = last["inning"] | "";
  n.battingIsA = strncmp(inning, t0, strlen(t0)) == 0;
  n.innings = score.size() >= 2 ? 2 : 1;
  n.runs = last["r"] | 0; n.wkts = last["w"] | 0;
  n.balls = oversToBalls(last["o"] | 0.0f);
  n.target = score.size() >= 2 ? (int)(score[score.size() - 2]["r"] | 0) + 1 : 0;
  if (n.totalBalls == 0) n.target = 0;
  setStatus(n, best["status"] | "");
  n.live = !(best["matchEnded"] | false); n.ended = !n.live;
  n.hasPlayers = false;

  // Derive "this over" chips + liquid events from deltas between polls
  String id = best["id"] | "";
  bool same = s_havePrev && id == s_matchId && n.innings == s_prev.innings && n.battingIsA == s_prev.battingIsA;
  n.eventSeq = s_seq; n.lastEvent = MatchEvent::None;
  if (same) {
    memcpy(n.thisOver, s_prev.thisOver, sizeof n.thisOver); n.nThisOver = s_prev.nThisOver;
    int db = n.balls - s_prev.balls, dr = n.runs - s_prev.runs, dw = n.wkts - s_prev.wkts;
    if (n.balls > 0 && (n.balls - 1) / 6 != (s_prev.balls > 0 ? (s_prev.balls - 1) / 6 : -1)) n.nThisOver = 0;
    if (db == 1 && n.nThisOver < 8) {
      if (dw > 0) strcpy(n.thisOver[n.nThisOver++], "W");
      else if (dr == 0) strcpy(n.thisOver[n.nThisOver++], ".");
      else snprintf(n.thisOver[n.nThisOver++], 4, "%d", dr);
    }
    if (dw > 0) { n.lastEvent = MatchEvent::Wicket; n.eventSeq = ++s_seq; }
    else if (db == 1 && (dr == 4 || dr == 6)) { n.lastEvent = dr == 4 ? MatchEvent::Four : MatchEvent::Six; n.eventSeq = ++s_seq; }
  }
  s_matchId = id; s_prev = n; s_havePrev = true;
  s = n;
  Serial.printf("[cricapi] %s %s %d/%d (%d balls) tgt %d : %s\n", n.teamA, n.teamB, n.runs, n.wkts, n.balls, n.target, n.status);

  if (hits >= limit - 1) return 60 * 60000UL;                  // out of budget: back off
  return n.live ? POLL_LIVE_MS : POLL_IDLE_MS;
}

uint32_t feedPoll(MatchState& s, bool& changed) { changed = true; return cricapiPoll(s); }
const char* feedLinkNote() { return nullptr; }
void feedSetShowing(const char*) {}
#endif
