// CYD Live Cricket Scoreboard: ESP32-2432S028R (2.8" ILI9341)
// Core 0: data feed task (hub / CricketData / mock). Core 1: UI + liquid animation + command apply.
#include "ipl_teams.h"
#include "config.h"
#include "secrets.h"
#include "display_config.h"
#include "match_state.h"
#include "feed.h"
#include "winprob.h"
#include "ui.h"
#include "liquid.h"
#include "fonts.h"
#include "device_cmd.h"
#include "wifi_setup.h"
#include <WiFi.h>
#include <Preferences.h>
#include <time.h>

LGFX lcd;
static MatchState g_state;
static SemaphoreHandle_t g_mtx;
static Preferences prefs;

static void netTask(void*) {
  wifiStart();
  for (;;) {
    wifiTick();
    MatchState local;
    xSemaphoreTake(g_mtx, portMAX_DELAY); local = g_state; xSemaphoreGive(g_mtx);
    bool changed = false;
    uint32_t wait = feedPoll(local, changed);
    if (changed) {
      xSemaphoreTake(g_mtx, portMAX_DELAY);
      local.version = g_state.version + 1; g_state = local;
      xSemaphoreGive(g_mtx);
    }
    vTaskDelay(pdMS_TO_TICKS(wait));
  }
}

static bool g_forceRedraw = false;
static bool g_qrDirty = false;

// Full-screen "scan to play" panel for the crowd prediction game.
static void drawQrScreen() {
  lcd.fillScreen(0x0B0A12u);
  const int side = 200, x = 8, y = (lcd.height() - side) / 2;
  lcd.fillRect(x, y, side, side, 0xFFFFFFu);
  lcd.qrcode(g_qrUrl, x + 6, y + 6, side - 12, 3);
  int tx = x + side + 10;
  lcd.setTextDatum(textdatum_t::top_left);
  lcd.setFont(&ft::label); lcd.setTextColor(0x8A86A0u); lcd.drawString("CROWD GAME", tx, y);
  lcd.setFont(&ft::name);  lcd.setTextColor(0xF2F0F7u);
  lcd.drawString("Scan to", tx, y + 22); lcd.drawString("predict", tx, y + 44); lcd.drawString("the next", tx, y + 66); lcd.drawString("ball", tx, y + 88);
  lcd.setFont(&ft::label); lcd.setTextColor(0x8A86A0u);
  lcd.drawString("WIFI", tx, y + 124);
  lcd.setTextColor(0xF2F0F7u); lcd.drawString("UCIS-Cricket", tx, y + 138);
  lcd.setTextColor(0x8A86A0u); lcd.drawString("PASS", tx, y + 158);
  lcd.setTextColor(0xF2F0F7u); lcd.drawString("cricket2026", tx, y + 172);
  lcd.setTextColor(0x8A86A0u); lcd.drawString("Tap to close", tx, y + side - 12);
}

static void setQr(bool on) {
  if (on == g_qrShow) return;
  g_qrShow = on; g_qrDirty = on;
  if (!on) { lcd.fillScreen(0x0B0A12u); g_forceRedraw = true; }
}

// Short tap: ask the hub to switch live <-> simulation (or close the QR panel).
// Long press (>= 1.2 s): toggle the QR panel locally.
static void pollTouch() {
  static bool down = false; static uint32_t since = 0; static bool longDone = false;
  int32_t tx, ty;
  bool now = lcd.getTouch(&tx, &ty) > 0;
  uint32_t t = millis();
  if (now && !down) { down = true; since = t; longDone = false; }
#if EXHIBITION_DEMO
  else if (now && down && !longDone && t - since >= 1200) { longDone = true; if (g_qrShow) setQr(false); g_demoShow = !g_demoShow; }
#else
  else if (now && down && !longDone && t - since >= 1200) { longDone = true; setQr(!g_qrShow); }
#endif
  else if (!now && down) {
    down = false;
    if (!longDone && t - since >= 40) {
#if EXHIBITION_DEMO
      if (g_qrShow) setQr(false); else g_demoShow = !g_demoShow;   // TEMPORARY: demo scoreboard
#else
      if (g_qrShow) setQr(false); else g_tapPending = true;
#endif
    }
  }
}

static void applyCommands() {
  DeviceCmd c;
  while (cmdPop(c)) {
    char detail[32] = "";
    switch (c.cmd) {
      case Cmd::Brightness: {
        int v = c.arg < 10 ? 10 : (c.arg > 255 ? 255 : c.arg);
        lcd.setBrightness(v); g_brightness = v; prefs.putUChar("bri", v);
        snprintf(detail, sizeof detail, "brightness %d", v);
        break;
      }
      case Cmd::Rotate: {
        int r = (c.arg == 1 || c.arg == 3) ? c.arg : (g_rotation == 1 ? 3 : 1);
        lcd.setRotation(r); g_rotation = r; prefs.putUChar("rot", r);
        lcd.fillScreen(0x0B0A12u); g_forceRedraw = true;
        snprintf(detail, sizeof detail, "rotation %d", r);
        break;
      }
      case Cmd::Invert: {
        bool on = c.arg < 0 ? !g_inverted : c.arg == 1;
        lcd.invertDisplay(on ^ CYD_INVERT); g_inverted = on; prefs.putBool("inv", on);
        snprintf(detail, sizeof detail, "invert %s", on ? "on" : "off");
        break;
      }
      case Cmd::Qr: {
        bool on = c.arg < 0 ? !g_qrShow : c.arg == 1;
        if (on && g_qrShow) g_qrDirty = true;          // new URL: redraw
        setQr(on);
        snprintf(detail, sizeof detail, "qr %s", on ? "on" : "off");
        break;
      }
      case Cmd::Identify:
        liquidIdentify();
        strcpy(detail, "flashing");
        break;
      case Cmd::Reboot:
        ackPush(c.id, true, "rebooting");
        delay(600);
        ESP.restart();
        break;
      default: break;
    }
    ackPush(c.id, true, detail);
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n[boot] CYD cricket scoreboard " FW_VERSION);
  prefs.begin("cyd", false);
  g_brightness = prefs.getUChar("bri", 200);
  g_rotation = prefs.getUChar("rot", SCREEN_ROTATION);
  g_inverted = prefs.getBool("inv", false);

  lcd.init();
  lcd.setRotation(g_rotation);
  if (g_inverted) lcd.invertDisplay(!CYD_INVERT);
  lcd.setBrightness(g_brightness);
  ft::begin();
  uiBegin(&lcd);
  liquidBegin(&lcd, 90);
  cmdInit();

  memset(&g_state, 0, sizeof g_state);
  strcpy(g_state.status, FEED_MODE == FEED_MOCK ? "Starting simulation..." : "Waiting for the hub...");
  g_mtx = xSemaphoreCreateMutex();

  configTzTime(TZ_INFO, "pool.ntp.org", "time.google.com");   // syncs whenever WiFi comes up
  xTaskCreatePinnedToCore(netTask, "feed", 16384, nullptr, 1, nullptr, 0);
  Serial.printf("[boot] free heap %u, largest block %u\n", ESP.getFreeHeap(), ESP.getMaxAllocHeap());
}

void loop() {
  static uint32_t lastVer = UINT32_MAX, lastSeq = 0, lastFrame = millis(), lastHdrCheck = 0, lastLog = 0, frames = 0;
  static int lastMin = -1; static bool lastWifi = false, lastLive = false, lastEnded = false;
  static const char* lastNote = nullptr;
  static MatchState s;

  applyCommands();
  pollTouch();
  if (g_qrShow) {                                   // QR panel owns the screen until closed
    if (g_qrDirty) { drawQrScreen(); g_qrDirty = false; }
    delay(30);
    return;
  }

  // WiFi setup portal runs in the background; the screen shows the link status meanwhile
  // and the header shows "WIFI SETUP". (uiDrawWifiSetup() is kept for a future
  // "show setup" command.)

  bool changed = false;
  xSemaphoreTake(g_mtx, portMAX_DELAY);
  if (g_state.version != lastVer) { s = g_state; lastVer = s.version; changed = true; }
  xSemaphoreGive(g_mtx);
  if (g_forceRedraw) { changed = true; g_forceRedraw = false; lastMin = -2; }

  if (changed) {
    float pBat = winProbBatting(s);
    liquidSetTarget(s.battingIsA ? pBat : 1.0f - pBat);
    if (s.colA && s.colB) teamColorsSet(s.colA, s.colB); else teamColorsApply(s.teamA, s.teamB);
    teamRampsSet(s.rampA, s.rampB);
    liquidSetLabels(s.teamA[0] ? s.teamA : "--", s.teamB[0] ? s.teamB : "--", s.ended ? s.status : nullptr);
    if (s.eventSeq != lastSeq) { liquidEvent(s.lastEvent, s.battingIsA); lastSeq = s.eventSeq; }
    uiDrawBody(s);
    char sum[48];
    snprintf(sum, sizeof sum, "%s %d/%d (%d.%d)", s.battingIsA ? s.teamA : s.teamB, s.runs, s.wkts, s.balls / 6, s.balls % 6);
    feedSetShowing(sum);
  }

  uint32_t now = millis();
  if (changed || now - lastHdrCheck > 1000) {
    lastHdrCheck = now;
    bool wifi = WiFi.status() == WL_CONNECTED;
    const char* note = feedLinkNote();
    struct tm tmv; int mn = getLocalTime(&tmv, 0) ? tmv.tm_min : -1;
    bool noteChanged = (note == nullptr) != (lastNote == nullptr) || (note && lastNote && strcmp(note, lastNote));
    if (changed || mn != lastMin || wifi != lastWifi || s.live != lastLive || s.ended != lastEnded || noteChanged) {
      uiDrawHeader(s, wifi, note);
      lastMin = mn; lastWifi = wifi; lastLive = s.live; lastEnded = s.ended; lastNote = note;
    }
  }

  float dt = (now - lastFrame) / 1000.0f; lastFrame = now;
  if (dt > 0.1f) dt = 0.1f;
  liquidFrame(dt);
  frames++;

  if (now - lastLog > 5000) {
    g_fps = frames * 1000.0f / (now - lastLog);
    Serial.printf("[perf] %.1f fps  heap %u  maxblk %u\n", g_fps, ESP.getFreeHeap(), ESP.getMaxAllocHeap());
    frames = 0; lastLog = now;
  }
  uint32_t spent = millis() - now;
  if (spent < 33) delay(33 - spent); else delay(1);
}
