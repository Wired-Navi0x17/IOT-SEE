// Static regions (header, score, players, footer). Each is drawn into one shared
// 320x70 canvas and pushed, so there's no flicker and only ~45 KB of RAM is used.
// Identity and active state are carried by text colour only (no marker bars).
#include "ui.h"
#include "palette.h"
#include "fonts.h"
#include "winprob.h"
#include "device_cmd.h"
#include <time.h>
#include <string.h>
#include <stdio.h>
#include <initializer_list>

namespace {
constexpr int W = 320;
constexpr int Y_HDR = 0,    H_HDR = 20;
constexpr int Y_SCORE = 20, H_SCORE = 70;
constexpr int Y_PLAY = 150, H_PLAY = 54;
constexpr int Y_FOOT = 204, H_FOOT = 36;

LGFX* L = nullptr;
LGFX_Sprite cv;
using F = const lgfx::IFont*;

void clear(int h) { cv.fillRect(0, 0, W, h, COL_BG); }
void push(int y, int h) {
  if (!cv.getBuffer()) return;
  L->startWrite();
  L->pushImage(0, y, W, h, (const lgfx::swap565_t*)cv.getBuffer());
  L->endWrite();
}
int tw(const char* s, F f) { cv.setFont(f); return cv.textWidth(s); }
void txt(const char* s, int x, int y, F f, uint32_t c, textdatum_t d = textdatum_t::top_left) {
  cv.setFont(f); cv.setTextColor(c); cv.setTextDatum(d); cv.drawString(s, x, y);
}
F fit(const char* s, int maxw, std::initializer_list<F> fonts) {
  F last = nullptr;
  for (F f : fonts) { last = f; if (tw(s, f) <= maxw) return f; }
  return last;
}
// Full name if it fits, else surname, else truncated.
void fitName(char* out, size_t n, const char* name, F f, int maxw) {
  strncpy(out, name, n - 1); out[n - 1] = 0;
  if (tw(out, f) <= maxw) return;
  const char* sp = strrchr(name, ' ');
  if (sp) { strncpy(out, sp + 1, n - 1); out[n - 1] = 0; }
  size_t len = strlen(out);
  while (len > 1 && tw(out, f) > maxw) out[--len] = 0;
}
void truncate(char* out, size_t n, const char* s, F f, int maxw) {
  strncpy(out, s, n - 1); out[n - 1] = 0;
  size_t len = strlen(out);
  while (len > 1 && tw(out, f) > maxw) out[--len] = 0;
}
void wrap(const char* s, int x, int y, int maxw, F f, uint32_t c, int lineH, int maxLines) {
  char line[64] = "", word[32];
  int lines = 0;
  while (*s && lines < maxLines) {
    int n = 0; while (*s == ' ') s++;
    while (*s && *s != ' ' && n < 31) word[n++] = *s++;
    word[n] = 0; if (!n) break;
    char trial[96]; snprintf(trial, sizeof trial, "%s%s%s", line, line[0] ? " " : "", word);
    if (tw(trial, f) > maxw && line[0]) {
      txt(line, x, y + lines * lineH, f, c); lines++;
      strncpy(line, word, sizeof line - 1);
    } else strncpy(line, trial, sizeof line - 1);
  }
  if (line[0] && lines < maxLines) txt(line, x, y + lines * lineH, f, c);
}
uint32_t batCol(const MatchState& s)  { return s.battingIsA ? COL_A : COL_B; }
void oversStr(char* b, size_t n, int balls) { snprintf(b, n, "%d.%d", balls / 6, balls % 6); }

void wifiIcon(int cx, int cy, bool ok) {
  uint32_t c = ok ? COL_TXT : 0x4A4658;
  cv.fillCircle(cx, cy, 1, c);
  for (int r = 4; r <= 10; r += 3) cv.drawArc(cx, cy, r, r - 1, 225, 315, c);
  if (!ok) cv.drawLine(cx - 6, cy - 10, cx + 6, cy, COL_LIVE);
}

void drawScore(const MatchState& s) {
  clear(H_SCORE);
  if (!s.teamA[0]) {                                   // no data yet
    wrap(s.status[0] ? s.status : "Waiting for match data...", 12, 22, 296, &ft::name, COL_DIM, 20, 2);
    push(Y_SCORE, H_SCORE); return;
  }
  // team row: names in team colour; the batting side is full colour, the other dimmed
  txt(s.teamA, 10, 4, &ft::name, COL_A);
  cv.drawFastHLine(60, 11, 34, COL_LINE); txt("vs", 107, 11, &ft::body, COL_DIM, textdatum_t::middle_center);
  cv.drawFastHLine(120, 11, 34, COL_LINE);
  txt(s.teamB, 204, 4, &ft::name, COL_B, textdatum_t::top_right);

  // big score
  char b[16]; int x = 10;
  snprintf(b, sizeof b, "%d", s.runs);  txt(b, x, 20, &ft::score, COL_TXT); x += tw(b, &ft::score) + 1;
  txt("/", x, 20, &ft::score, batCol(s)); x += tw("/", &ft::score) + 1;
  snprintf(b, sizeof b, "%d", s.wkts);  txt(b, x, 20, &ft::score, COL_TXT);

  // overs + target
  oversStr(b, sizeof b, s.balls);
  txt(b, 10, 53, &ft::numM, batCol(s));
  txt("OV", 10 + tw(b, &ft::numM) + 4, 57, &ft::label, COL_DIM);
  if (s.innings >= 2 && s.target > 0) {
    snprintf(b, sizeof b, "%d", s.target);
    int vw = tw(b, &ft::numM);
    txt(b, 204, 53, &ft::numM, COL_TXT, textdatum_t::top_right);
    txt("TARGET", 204 - vw - 6, 57, &ft::label, COL_DIM, textdatum_t::top_right);
  } else {
    txt("1ST INNINGS", 204, 57, &ft::label, COL_DIM, textdatum_t::top_right);
  }

  // right column
  cv.drawFastVLine(214, 4, 62, COL_LINE);
  cv.drawFastVLine(268, 8, 30, COL_LINE);
  const int c1 = 241, c2 = 294;
  int bl = s.totalBalls - s.balls; if (bl < 0) bl = 0;
  char l1[8], l2[8], v1[8], v2[8], s1[16], s2[16];
  float crr = s.balls ? s.runs * 6.0f / s.balls : 0;
  bool chase = s.innings >= 2 && s.target > 0;
  if (chase) {
    int need = s.target - s.runs; if (need < 0) need = 0;
    strcpy(l1, "NEED"); strcpy(l2, "OFF");
    snprintf(v1, sizeof v1, "%d", need);
    if (s.totalBalls) snprintf(v2, sizeof v2, "%d", bl); else strcpy(v2, "--");
    if (bl) snprintf(s1, sizeof s1, "%.2f", need * 6.0f / bl); else strcpy(s1, "--");
    snprintf(s2, sizeof s2, "%.2f", crr);
  } else {
    strcpy(l1, "PROJ"); strcpy(l2, "PAR");
    snprintf(v1, sizeof v1, "%d", projectedTotal(s));
    snprintf(v2, sizeof v2, "%d", parScore(s));
    snprintf(s1, sizeof s1, "%.2f", crr);
    snprintf(s2, sizeof s2, "%.2f", s.totalBalls ? parScore(s) * 6.0f / s.totalBalls : 0.0f);
  }
  txt(l1, c1, 4, &ft::label, COL_DIM, textdatum_t::top_center);
  txt(l2, c2, 4, &ft::label, COL_DIM, textdatum_t::top_center);
  txt(v1, c1, 28, fit(v1, 50, {&ft::numL, &ft::numM}), COL_TXT, textdatum_t::middle_center);
  txt(v2, c2, 28, fit(v2, 50, {&ft::numL, &ft::numM}), COL_TXT, textdatum_t::middle_center);
  // rate row: small label + mono value
  const char* rl1 = chase ? "RRR" : "CRR";
  const char* rl2 = chase ? "CRR" : "PAR";
  txt(rl1, c1, 46, &ft::label, COL_DIM, textdatum_t::top_center);
  txt(rl2, c2, 46, &ft::label, COL_DIM, textdatum_t::top_center);
  txt(s1, c1, 57, &ft::numS, COL_TXT, textdatum_t::top_center);
  txt(s2, c2, 57, &ft::numS, COL_TXT, textdatum_t::top_center);
  push(Y_SCORE, H_SCORE);
}

void batterRow(const Batter& b, int y, bool strike) {
  txt(strike ? "ON STRIKE" : "NON-STRIKER", 10, y + 2, &ft::label, strike ? COL_TXT : COL_DIM);
  char r[8], bb[10], nm[28], nm2[28];
  snprintf(r, sizeof r, "%d", b.runs); snprintf(bb, sizeof bb, "(%d)", b.balls);
  int wbb = tw(bb, &ft::numS);
  int wr = tw(r, &ft::numM);
  uint32_t c = strike ? COL_TXT : COL_DIM;
  txt(bb, 154, y + 13, &ft::numS, COL_DIM, textdatum_t::top_right);
  txt(r, 154 - wbb - 4, y + 11, &ft::numM, c, textdatum_t::top_right);
  snprintf(nm2, sizeof nm2, "%s%s", b.name[0] ? b.name : "-", strike ? "*" : "");
  fitName(nm, sizeof nm, nm2, &ft::name, 154 - wbb - wr - 10 - 10);
  txt(nm, 10, y + 12, &ft::name, c);
}

void drawPlayers(const MatchState& s) {
  clear(H_PLAY);
  if (!s.hasPlayers) {
    if (s.teamA[0]) wrap(s.status, 10, 8, 300, &ft::name, COL_TXT, 20, 2);
    push(Y_PLAY, H_PLAY); return;
  }
  cv.drawFastVLine(160, 4, 46, COL_LINE);
  batterRow(s.striker, 0, true);
  cv.drawFastHLine(10, 27, 144, COL_LINE);
  batterRow(s.nonStriker, 27, false);

  // bowler: label in bowling team colour
  txt("BOWLING", 168, 2, &ft::label, s.battingIsA ? COL_B : COL_A);
  char fig[24], nm[28];
  snprintf(fig, sizeof fig, "%d.%d-%d-%d-%d", s.bowler.balls / 6, s.bowler.balls % 6, s.bowler.maidens, s.bowler.runs, s.bowler.wkts);
  int wf = tw(fig, &ft::numS);
  txt(fig, 314, 13, &ft::numS, COL_TXT, textdatum_t::top_right);
  fitName(nm, sizeof nm, s.bowler.name[0] ? s.bowler.name : "-", &ft::name, 314 - wf - 6 - 168);
  txt(nm, 168, 12, &ft::name, COL_TXT);
  cv.drawFastHLine(168, 27, 146, COL_LINE);

  // next batter / bowler
  txt("NEXT BAT", 168, 29, &ft::label, COL_DIM);
  fitName(nm, sizeof nm, s.nextBat[0] ? s.nextBat : "-", &ft::body, 70);
  txt(nm, 168, 40, &ft::body, COL_TXT);
  cv.drawFastVLine(242, 31, 20, COL_LINE);
  txt("NEXT BOWL", 248, 29, &ft::label, COL_DIM);
  fitName(nm, sizeof nm, s.nextBowl[0] ? s.nextBowl : "-", &ft::body, 68);
  txt(nm, 248, 40, &ft::body, COL_TXT);
  push(Y_PLAY, H_PLAY);
}

void drawFooter(const MatchState& s) {
  clear(H_FOOT);
  cv.drawFastHLine(0, 0, W, COL_LINE);
  char b[12];
  int bl = s.totalBalls - s.balls; if (bl < 0) bl = 0;
  bool have = s.totalBalls && s.teamA[0];
  txt("BALLS LEFT", 10, 4, &ft::label, COL_DIM);
  if (have) snprintf(b, sizeof b, "%d", bl); else strcpy(b, "--");
  txt(b, 10, 16, &ft::numL, COL_TXT);
  cv.drawFastVLine(78, 6, 26, COL_LINE);
  txt("OVERS LEFT", 86, 4, &ft::label, COL_DIM);
  if (have) oversStr(b, sizeof b, bl); else strcpy(b, "--");
  txt(b, 86, 16, &ft::numL, COL_TXT);
  cv.drawFastVLine(156, 6, 26, COL_LINE);

  txt("THIS OVER", 164, 4, &ft::label, COL_DIM);
  int first = s.nThisOver > 6 ? s.nThisOver - 6 : 0;
  int x = 164;
  if (s.nThisOver == 0) txt("-", x + 2, 17, &ft::numS, COL_DIM);
  for (int i = first; i < s.nThisOver; i++, x += 25) {
    const char* c = s.thisOver[i];
    uint32_t fill = COL_CHIP, border = COL_CHIPB, tc = COL_TXT;
    if (!strcmp(c, "4") || !strcmp(c, "6")) { fill = border = batCol(s); tc = COL_BG; }
    else if (c[0] == 'W' && c[1] == 0) fill = border = COL_WKT;
    cv.fillRect(x, 16, 22, 17, fill);              // square chips, no rounding
    cv.drawRect(x, 16, 22, 17, border);
    cv.setTextColor(tc);
    if (!strcmp(c, ".")) cv.fillRect(x + 10, 23, 2, 2, COL_TXT);
    else { cv.setFont(&ft::numS); cv.setTextDatum(textdatum_t::middle_center); cv.drawString(c, x + 11, 25); }
  }
  push(Y_FOOT, H_FOOT);
}
} // namespace

void uiBegin(LGFX* lcd) {
  L = lcd;
  cv.setColorDepth(16);
  if (!cv.createSprite(W, H_SCORE)) Serial.println("[ui] canvas alloc FAILED");
  L->fillScreen(COL_BG);
}

void uiDrawHeader(const MatchState& s, bool wifiOk, const char* linkNote) {
  clear(H_HDR);
  cv.fillCircle(8, 10, 3, (s.live && !s.sim && !g_demoShow) ? COL_LIVE : COL_DIM);
  const char* tag = g_demoShow ? "DEMO" : s.sim ? (s.ended ? "RESULT" : "SIM") : s.live ? "LIVE" : (s.ended ? "RESULT" : "IDLE");
  txt(tag, 16, 10, &ft::name, COL_TXT, textdatum_t::middle_left);
  int x = 16 + tw(tag, &ft::name) + 10;
  char ser[48];
  if (linkNote) {
    txt(linkNote, x, 10, &ft::label, COL_LIVE, textdatum_t::middle_left);
  } else {
    if (s.format[0]) {
      txt(s.format, x, 10, &ft::label, COL_DIM, textdatum_t::middle_left);
      x += tw(s.format, &ft::label) + 6; cv.fillRect(x - 1, 9, 2, 2, COL_DIM); x += 6;
    }
    truncate(ser, sizeof ser, s.series, &ft::label, 258 - x);
    txt(ser, x, 10, &ft::label, COL_DIM, textdatum_t::middle_left);
  }
  struct tm tmv; char clk[8] = "--:--";
  if (getLocalTime(&tmv, 0)) strftime(clk, sizeof clk, "%H:%M", &tmv);
  txt(clk, 296, 10, &ft::numS, COL_TXT, textdatum_t::middle_right);
  wifiIcon(310, 15, wifiOk);
  cv.drawFastHLine(6, 19, 308, COL_LINE);
  push(Y_HDR, H_HDR);
}

void uiDrawBody(const MatchState& s) {
  drawScore(s);
  drawPlayers(s);
  drawFooter(s);
}

void uiDrawWifiSetup(const char* apName, const char* apPass, int savedCount) {
  L->startWrite();
  L->fillScreen(COL_BG);
  // QR joins the setup network directly (Android camera / iOS camera)
  char qr[96];
  snprintf(qr, sizeof qr, "WIFI:T:WPA;S:%s;P:%s;;", apName, apPass);
  L->fillRect(196, 44, 112, 112, COL_TXT);
  L->qrcode(qr, 200, 48, 104, 3);
  L->setTextColor(COL_TXT); L->setTextDatum(textdatum_t::top_left);
  L->setFont(&ft::name);  L->drawString("WiFi setup", 12, 12);
  L->setFont(&ft::label); L->setTextColor(COL_DIM);
  L->drawString("NO SAVED NETWORK IN RANGE", 12, 32);
  L->drawFastHLine(12, 48, 172, COL_LINE);
  L->setFont(&ft::label); L->drawString("1  JOIN THIS WIFI", 12, 58);
  L->setFont(&ft::name);  L->setTextColor(COL_B); L->drawString(apName, 12, 72);
  L->setFont(&ft::numS);  L->setTextColor(COL_DIM); L->drawString("pass", 12, 92);
  L->setTextColor(COL_TXT); L->drawString(apPass, 48, 92);
  L->setFont(&ft::label); L->setTextColor(COL_DIM); L->drawString("2  OPEN", 12, 116);
  L->setFont(&ft::name);  L->setTextColor(COL_B); L->drawString("192.168.4.1", 12, 130);
  L->setFont(&ft::body);  L->setTextColor(COL_DIM);
  L->drawString("Pick your hotspot or home WiFi,", 12, 160);
  L->drawString("enter the password, save.", 12, 176);
  L->drawFastHLine(12, 200, 296, COL_LINE);
  char line[64];
  snprintf(line, sizeof line, "%d saved network%s, retrying every 30 s", savedCount, savedCount == 1 ? "" : "s");
  L->setFont(&ft::label); L->drawString(line, 12, 210);
  L->setTextDatum(textdatum_t::top_center); L->drawString("SCAN TO JOIN", 252, 162);
  L->endWrite();
}
