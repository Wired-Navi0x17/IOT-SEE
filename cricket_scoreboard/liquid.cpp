// Animated "two liquids" momentum band. Team A flows in from the left, Team B from the right,
// each in its IPL colour (ipl_teams.cpp); the seam sits at Team A's win share.
#include "liquid.h"
#include "palette.h"
#include "fonts.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

namespace {
constexpr int W = 320, H = 60;
constexpr int NR = 2;           // one stream per team: soft body + bright core on the same path
constexpr float Y0 = 38.0f;     // ribbon centreline (pill sits above it)
constexpr float BLEND = 16.0f;  // seam crossfade width (px)

LGFX* g_lcd = nullptr; int g_y = 0;
LGFX_Sprite band;

float sinT[1024];
inline float fs(float x) { return sinT[((int)(x * 162.974661f)) & 1023]; }

uint8_t glow[64];
uint8_t lutA[3][256], lutB[3][256];
float haze[H], vfade[H], seamV[H], seamX[H];

struct Rib { float amp, f1, s1, ph1, amp2, f2, s2, ph2, k, gain; };
// k = glow-table steps per pixel of distance (bigger = thinner ribbon)
Rib ribA[NR] = {
  {11, 0.020f, 1.1f, 0.0f, 4, 0.047f, 0.7f, 1.0f, 1.3f, 0.50f},   // body
  {11, 0.020f, 1.1f, 0.0f, 4, 0.047f, 0.7f, 1.0f, 4.5f, 0.60f},   // core
};
Rib ribB[NR] = {
  {11, 0.019f, 1.0f, 3.3f, 4, 0.044f, 0.8f, 0.4f, 1.3f, 0.50f},
  {11, 0.019f, 1.0f, 3.3f, 4, 0.044f, 0.8f, 0.4f, 4.5f, 0.60f},
};

float t = 0, phA = 0, phB = 0;
float pTarget = 0.5f, pDisp = 0.5f;
float eA = 0, eB = 0, flash = 0;
int identifyLeft = 0; float identifyT = 0;
char labA[6] = "A", labB[6] = "B", overrideTxt[64] = "";

uint8_t bgR, bgG, bgB;

void buildLut(uint8_t lut[3][256], uint32_t deep, uint32_t bright, uint32_t hot) {
  float d[3] = {float((deep >> 16) & 255), float((deep >> 8) & 255), float(deep & 255)};
  float b[3] = {float((bright >> 16) & 255), float((bright >> 8) & 255), float(bright & 255)};
  float h[3] = {float((hot >> 16) & 255), float((hot >> 8) & 255), float(hot & 255)};
  for (int i = 0; i < 256; i++) {
    float v = i / 255.0f;
    for (int c = 0; c < 3; c++) {
      float out;
      if (v < 0.45f)      out = d[c] * (v / 0.45f);
      else if (v < 0.82f) out = d[c] + (b[c] - d[c]) * ((v - 0.45f) / 0.37f);
      else                out = b[c] + (h[c] - b[c]) * ((v - 0.82f) / 0.18f);
      lut[c][i] = (uint8_t)(out > 255 ? 255 : out);
    }
  }
}

inline float clamp01(float v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }
inline float smooth(float a, float b, float x) { float u = clamp01((x - a) / (b - a)); return u * u * (3 - 2 * u); }

uint32_t scaleCol(uint32_t c, float k, float toWhite) {
  uint32_t o = 0;
  for (int sh = 16; sh >= 0; sh -= 8) {
    float v = (c >> sh) & 255; v = v * k + (255 - v * k) * toWhite;
    o |= (uint32_t)(v > 255 ? 255 : v) << sh;
  }
  return o;
}

// deep / bright / hot ramps from the current team colours
void rebuildLuts() {
  auto ramp = [](uint8_t lut[3][256], uint32_t col, const uint32_t k[3]) {
    if (k[0] | k[1] | k[2]) buildLut(lut, k[0], k[1], k[2]);          // multi-colour jersey ramp from the hub
    else buildLut(lut, scaleCol(col, 0.45f, 0), col, scaleCol(col, 1, 0.85f));
  };
  ramp(lutA, COL_A, RAMP_A);
  ramp(lutB, COL_B, RAMP_B);
}

void drawPill(int bx) {
  band.setFont(&ft::numS);
  band.setTextDatum(textdatum_t::middle_left);
  const int h = 18, py = 1;
  char pa[8], pb[8];
  int pct = (int)lroundf(pDisp * 100.0f);
  snprintf(pa, sizeof pa, "%d%%", pct); snprintf(pb, sizeof pb, "%d%%", 100 - pct);

  int w;
  if (overrideTxt[0]) w = band.textWidth(overrideTxt) + 18;
  else w = band.textWidth(labA) + band.textWidth(pa) + band.textWidth(labB) + band.textWidth(pb) + 4 + 4 + 18 + 16;
  int px = bx - w / 2;
  if (px < 2) px = 2;
  if (px + w > W - 2) px = W - 2 - w;

  band.fillRoundRect(px, py, w, h, 6, COL_PILL);
  band.setClipRect(px, py, w / 2, h);           band.drawRoundRect(px, py, w, h, 6, COL_A);
  band.setClipRect(px + w / 2, py, w - w / 2, h); band.drawRoundRect(px, py, w, h, 6, COL_B);
  band.clearClipRect();

  int x = px + 8, y = py + h / 2;
  auto put = [&](const char* s, uint32_t c) { band.setTextColor(c); band.drawString(s, x, y); x += band.textWidth(s); };
  if (overrideTxt[0]) { put(overrideTxt, COL_TXT); }
  else {
    put(labA, COL_A); x += 4; put(pa, COL_TXT);
    x += 8; band.drawFastVLine(x, py + 4, h - 8, COL_DIM); x += 10;
    put(labB, COL_B); x += 4; put(pb, COL_TXT);
  }
  int mx = bx < px + 8 ? px + 8 : (bx > px + w - 8 ? px + w - 8 : bx);
  band.fillTriangle(mx - 5, py + h, mx + 5, py + h, mx, py + h + 6, COL_A);
}
} // namespace

void liquidBegin(LGFX* lcd, int y) {
  g_lcd = lcd; g_y = y;
  for (int i = 0; i < 1024; i++) sinT[i] = sinf(i * 2.0f * (float)M_PI / 1024.0f);
  for (int k = 0; k < 64; k++) {
    float v = 0.72f * expf(-(k / 6.0f) * (k / 6.0f) * 0.7f) + 0.28f * expf(-k / 14.0f) - 0.28f * expf(-63 / 14.0f);
    glow[k] = (uint8_t)(255.0f * (v < 0 ? 0 : v));
  }
  rebuildLuts();
  bgR = (COL_BG >> 16) & 255; bgG = (COL_BG >> 8) & 255; bgB = COL_BG & 255;
  for (int y2 = 0; y2 < H; y2++) {
    float d = (y2 - Y0) / 13.0f;
    haze[y2]  = 38.0f * expf(-d * d);
    vfade[y2] = smooth(8, 24, y2) * smooth(H, H - 5, y2);
    float e = (y2 - Y0) / 10.0f;
    seamV[y2] = expf(-e * e) * smooth(20, 26, y2);
  }
  band.setColorDepth(16);
  if (!band.createSprite(W, H)) Serial.println("[liquid] sprite alloc FAILED");
}

void liquidSetTarget(float pA) { pTarget = pA; }

void liquidSetLabels(const char* a, const char* b, const char* ov) {
  strncpy(labA, a, 5); labA[5] = 0; strncpy(labB, b, 5); labB[5] = 0;
  strncpy(overrideTxt, ov ? ov : "", 63); overrideTxt[63] = 0;
  if (teamColorsTake()) rebuildLuts();
}

void liquidEvent(MatchEvent e, bool battingIsA) {
  if (e == MatchEvent::Four || e == MatchEvent::Six) {
    float amt = e == MatchEvent::Six ? 1.0f : 0.7f;
    if (battingIsA) eA = amt; else eB = amt;
  } else if (e == MatchEvent::Wicket) {
    if (battingIsA) eB = 1.0f; else eA = 1.0f;     // bowling side surges
    flash = 1.0f;
  }
}

void liquidIdentify() { identifyLeft = 3; identifyT = 0; }

void liquidFrame(float dt) {
  if (!band.getBuffer()) return;
  t += dt;
  if (identifyLeft > 0) {
    identifyT -= dt;
    if (identifyT <= 0) { flash = 1.6f; eA = eB = 1.0f; identifyLeft--; identifyT = 0.45f; }
  }
  phA += dt * (1.0f + 1.6f * eA);
  phB += dt * (1.0f + 1.6f * eB);
  pDisp += (pTarget - pDisp) * (1.0f - expf(-dt * 1.2f));
  float dk = expf(-dt * 1.4f); eA *= dk; eB *= dk; flash *= expf(-dt * 3.0f);

  const float bx = pDisp * W;
  for (int y = 0; y < H; y++)
    seamX[y] = bx + 3.0f * fs(y * 0.17f + t * 2.1f) + 2.0f * fs(y * 0.06f - t * 1.3f);

  const float ampA = 1.0f + 0.9f * eA, ampB = 1.0f + 0.9f * eB;
  uint16_t* buf = (uint16_t*)band.getBuffer();
  float ycA[NR], ycB[NR];

  for (int x = 0; x < W; x++) {
    float dx = fabsf(x - bx);
    float pinch = fminf(1.0f, dx / 80.0f) * 0.85f + 0.15f;   // waves narrow where liquids meet
    float edge = fminf(1.0f, fminf(x, W - 1 - x) / 18.0f + 0.25f);
    for (int i = 0; i < NR; i++) {
      const Rib& a = ribA[i];   // A travels right (towards B)
      ycA[i] = Y0 + pinch * ampA * (a.amp * fs(a.f1 * x - a.s1 * phA + a.ph1) + a.amp2 * fs(a.f2 * x + a.s2 * phA * 0.6f + a.ph2));
      const Rib& b = ribB[i];   // B travels left (towards A)
      ycB[i] = Y0 + pinch * ampB * (b.amp * fs(b.f1 * x + b.s1 * phB + b.ph1) + b.amp2 * fs(b.f2 * x - b.s2 * phB * 0.6f + b.ph2));
    }
    for (int y = 0; y < H; y++) {
      float sx = seamX[y];
      float wa = clamp01((sx - x) / BLEND + 0.5f);
      float vf = vfade[y] * edge;
      int iA = 0, iB = 0;
      if (wa > 0.01f) {
        float acc = haze[y];
        for (int i = 0; i < NR; i++) { int k = (int)(fabsf(y - ycA[i]) * ribA[i].k); if (k < 64) acc += glow[k] * ribA[i].gain; }
        iA = (int)(acc * wa * vf); if (iA > 255) iA = 255;
      }
      if (wa < 0.99f) {
        float acc = haze[y];
        for (int i = 0; i < NR; i++) { int k = (int)(fabsf(y - ycB[i]) * ribB[i].k); if (k < 64) acc += glow[k] * ribB[i].gain; }
        iB = (int)(acc * (1.0f - wa) * vf); if (iB > 255) iB = 255;
      }
      int wh = 0;
      float ds = fabsf(x - sx);
      if (ds < 2.5f) wh = (int)((2.5f - ds) * 0.4f * seamV[y] * (150.0f + 105.0f * flash));
      int r = bgR + lutA[0][iA] + lutB[0][iB] + wh; if (r > 255) r = 255;
      int g = bgG + lutA[1][iA] + lutB[1][iB] + wh; if (g > 255) g = 255;
      int b = bgB + lutA[2][iA] + lutB[2][iB] + wh; if (b > 255) b = 255;
      uint16_t c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
      buf[y * W + x] = (c >> 8) | (c << 8);                   // sprite stores byte-swapped RGB565
    }
  }
  drawPill((int)bx);
  g_lcd->startWrite();
  band.pushSprite(g_lcd, 0, g_y);
  g_lcd->endWrite();
}
