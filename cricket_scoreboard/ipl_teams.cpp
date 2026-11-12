// The 10 IPL franchises and their match colours.
// Keep identical to hub/src/cricket_hub/ipl.py and web/src/lib/teams.ts.
#include "ipl_teams.h"
#include <ctype.h>
#include <math.h>
#include <string.h>

uint32_t COL_A = 0xB061F0;   // fallback Team A purple (red-shifted: ILI9341 renders pure violet as blue)
uint32_t COL_B = 0x2EE6D6;   // fallback Team B turquoise

namespace {
struct Team { const char* code; const char* name; const char* alias; uint32_t primary, alt; };
const Team TEAMS[] = {
  {"CSK",  "chennaisuperkings",          "",                         0xF9CD05, 0x3E6FD9},
  {"DC",   "delhicapitals",              "delhidaredevils",          0x2F6FE0, 0xE5323B},
  {"GT",   "gujarattitans",              "",                         0x6F8FD4, 0xD9B65C},
  {"KKR",  "kolkataknightriders",        "",                         0x9B5CF0, 0xE0B23A},
  {"LSG",  "lucknowsupergiants",         "",                         0x2EA8E6, 0xF28B30},
  {"MI",   "mumbaiindians",              "",                         0x1F7FE8, 0xD9AE3E},
  {"PBKS", "punjabkings",                "kingsxipunjab",            0xE5323B, 0xC3CAD1},
  {"RR",   "rajasthanroyals",            "",                         0xEA1A85, 0x3D6BE0},
  {"RCB",  "royalchallengersbengaluru",  "royalchallengersbangalore",0xD9262C, 0xD4AF37},
  {"SRH",  "sunrisershyderabad",         "",                         0xF7752A, 0xB8BEC4},
};
constexpr uint32_t FALL_A = 0xB061F0, FALL_B = 0x2EE6D6;
constexpr float CLASH = 150.0f;
bool dirty = true;

const Team* find(const char* s) {
  if (!s) return nullptr;
  char k[40]; size_t n = 0;
  for (; *s && n < sizeof k - 1; s++) if (isalpha((unsigned char)*s)) k[n++] = tolower((unsigned char)*s);
  k[n] = 0;
  for (const Team& t : TEAMS) {
    char c[6]; size_t i = 0;
    for (; t.code[i]; i++) c[i] = tolower((unsigned char)t.code[i]);
    c[i] = 0;
    if (!strcmp(k, c) || !strcmp(k, t.name) || (t.alias[0] && !strcmp(k, t.alias))) return &t;
  }
  if (!strcmp(k, "kxip")) return &TEAMS[6];
  return nullptr;
}

float dist(uint32_t c1, uint32_t c2) {
  int r1 = c1 >> 16 & 255, g1 = c1 >> 8 & 255, b1 = c1 & 255, r2 = c2 >> 16 & 255, g2 = c2 >> 8 & 255, b2 = c2 & 255;
  float rm = (r1 + r2) / 2.0f, dr = r1 - r2, dg = g1 - g2, db = b1 - b2;
  return sqrtf((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db);
}
} // namespace

const char* iplCode(const char* s) { const Team* t = find(s); return t ? t->code : nullptr; }

void teamColorsSet(uint32_t a, uint32_t b) {
  if (a != COL_A || b != COL_B) { COL_A = a; COL_B = b; dirty = true; }
}

bool teamColorsApply(const char* a, const char* b) {
  const Team* ta = find(a); const Team* tb = find(b);
  uint32_t ca = ta ? ta->primary : FALL_A, cb;
  if (!tb) cb = dist(ca, FALL_B) >= CLASH ? FALL_B : FALL_A;
  else if (dist(ca, tb->primary) >= CLASH) cb = tb->primary;
  else cb = dist(ca, tb->alt) >= dist(ca, tb->primary) ? tb->alt : tb->primary;
  bool ch = ca != COL_A || cb != COL_B;
  teamColorsSet(ca, cb);
  return ch;
}

bool teamColorsTake() { bool d = dirty; dirty = false; return d; }
