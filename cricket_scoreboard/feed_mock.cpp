// Simulated T20 chase so the UI can be developed without spending API calls.
#include "config.h"
#include "feed.h"
#include <Arduino.h>
#include <string.h>

namespace {
struct Bat  { const char* name; int runs, balls; };
struct Bowl { const char* name; int balls, maidens, runs, wkts; };
constexpr int TARGET = 181, TOTAL = 120, NBAT = 9, NBOWL = 5;

Bat bats[NBAT]; Bowl bowls[NBOWL];
int striker, nonStriker, nextIn, curBowler;
int runs, wkts, balls, overRuns;
char over[8][4]; int nOver; bool clearOnNext;
bool ended; uint32_t endedAt;
MatchEvent ev; uint32_t seq;
char status[64];
bool inited = false;

void reset() {
  const Bat b0[NBAT] = {{"T. HEAD",45,27},{"G. MAXWELL",8,7},{"T. DAVID",0,0},{"M. STOINIS",0,0},
                        {"P. CUMMINS",0,0},{"M. STARC",0,0},{"A. ZAMPA",0,0},{"N. ELLIS",0,0},{"J. HAZLEWOOD",0,0}};
  const Bowl w0[NBOWL] = {{"J. BUMRAH",12,0,14,1},{"M. SIRAJ",18,0,28,1},{"A. SINGH",18,0,27,0},
                          {"K. YADAV",12,0,18,1},{"H. PANDYA",12,0,11,0}};
  memcpy(bats, b0, sizeof b0); memcpy(bowls, w0, sizeof w0);
  striker = 0; nonStriker = 1; nextIn = 2; curBowler = 0;
  runs = 98; wkts = 3; balls = 72; overRuns = 0;
  nOver = 0; clearOnNext = false; ended = false; ev = MatchEvent::None;
}

int pickNextBowler(int cur) {
  for (int k = 1; k < NBOWL; k++) { int i = (cur + k) % NBOWL; if (bowls[i].balls < 24) return i; }
  return (cur + 1) % NBOWL;
}

void pushChip(const char* c) {
  if (nOver >= 8) { memmove(over[0], over[1], sizeof(over[0]) * 7); nOver = 7; }
  strncpy(over[nOver++], c, 3); over[nOver - 1][3] = 0;
}

void checkEnd() {
  if (runs >= TARGET) {
    snprintf(status, sizeof status, "AUS WON BY %d WKTS", 10 - wkts); ended = true;
  } else if (wkts >= 10 || balls >= TOTAL) {
    if (runs == TARGET - 1) snprintf(status, sizeof status, "MATCH TIED");
    else snprintf(status, sizeof status, "IND WON BY %d RUNS", TARGET - 1 - runs);
    ended = true;
  } else {
    snprintf(status, sizeof status, "AUS need %d runs off %d balls", TARGET - runs, TOTAL - balls);
  }
  if (ended) endedAt = millis();
}

void bowlBall() {
  if (clearOnNext) { nOver = 0; overRuns = 0; clearOnNext = false; }
  ev = MatchEvent::None;
  Bowl& bw = bowls[curBowler];
  if (random(1000) < 30) {                      // wide
    runs++; bw.runs++; overRuns++; pushChip("Wd"); checkEnd(); return;
  }
  balls++; bw.balls++; bats[striker].balls++;
  int r = random(1000), res;
  if      (r < 320) res = 0;
  else if (r < 640) res = 1;
  else if (r < 745) res = 2;
  else if (r < 760) res = 3;
  else if (r < 880) res = 4;
  else if (r < 945) res = 6;
  else              res = -1;                   // wicket

  if (res < 0) {
    wkts++; bw.wkts++; pushChip("W"); ev = MatchEvent::Wicket; seq++;
    if (wkts < 10 && nextIn < NBAT) striker = nextIn++;
  } else {
    runs += res; overRuns += res; bats[striker].runs += res; bw.runs += res;
    char c[4]; if (res == 0) strcpy(c, "."); else snprintf(c, sizeof c, "%d", res);
    pushChip(c);
    if (res == 4) { ev = MatchEvent::Four; seq++; }
    if (res == 6) { ev = MatchEvent::Six;  seq++; }
    if (res & 1) { int t = striker; striker = nonStriker; nonStriker = t; }
  }
  if (balls % 6 == 0) {                         // end of over
    if (overRuns == 0) bw.maidens++;
    int t = striker; striker = nonStriker; nonStriker = t;
    curBowler = pickNextBowler(curBowler);
    clearOnNext = true;
  }
  checkEnd();
}

void copyName(char* dst, const char* src) { strncpy(dst, src, 23); dst[23] = 0; }

void fill(MatchState& s) {
  strcpy(s.series, "IPL 2026"); strcpy(s.format, "T20");   // demo chase; player names wait for the 2026 squads
  strcpy(s.teamA, "SRH"); strcpy(s.teamB, "MI");
  s.battingIsA = true; s.innings = 2;
  s.runs = runs; s.wkts = wkts; s.balls = balls; s.totalBalls = TOTAL; s.target = TARGET;
  copyName(s.striker.name, bats[striker].name);     s.striker.runs = bats[striker].runs;     s.striker.balls = bats[striker].balls;
  copyName(s.nonStriker.name, bats[nonStriker].name); s.nonStriker.runs = bats[nonStriker].runs; s.nonStriker.balls = bats[nonStriker].balls;
  const Bowl& b = bowls[curBowler];
  copyName(s.bowler.name, b.name);
  s.bowler.balls = b.balls; s.bowler.maidens = b.maidens; s.bowler.runs = b.runs; s.bowler.wkts = b.wkts;
  copyName(s.nextBat, nextIn < NBAT ? bats[nextIn].name : "");
  copyName(s.nextBowl, bowls[pickNextBowler(curBowler)].name);
  memcpy(s.thisOver, over, sizeof over); s.nThisOver = nOver;
  strncpy(s.status, status, sizeof s.status - 1);
  s.live = !ended; s.ended = ended; s.hasPlayers = true;
  s.lastEvent = ev; s.eventSeq = seq;
}
} // namespace

uint32_t mockPoll(MatchState& s) {
  if (!inited) { randomSeed(esp_random()); reset(); checkEnd(); inited = true; }
  else if (ended) { if (millis() - endedAt > 15000) { reset(); checkEnd(); } }
  else bowlBall();
  fill(s);
  return ended ? 2000 : 3000 + random(1500);
}
