#include "wifi_setup.h"
#include "secrets.h"
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiMulti.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>

namespace {
Preferences store;
WiFiMulti* multi = nullptr;
WebServer web(80);
DNSServer dns;
volatile bool portalUp = false;
bool webStarted = false, tryNow = false;
uint32_t lastTry = 0, failCount = 0, gen = 0, setupSince = 0;
bool wasConnected = false;
String scanHtml;

struct Net { char ssid[33]; char pass[65]; };
Net nets[WIFI_MAX_SAVED];
int nNets = 0;

void load() {
  nNets = store.getUChar("n", 0);
  if (nNets > WIFI_MAX_SAVED) nNets = 0;
  for (int i = 0; i < nNets; i++) {
    char k[4];
    snprintf(k, sizeof k, "s%d", i); store.getString(k, nets[i].ssid, sizeof nets[i].ssid);
    snprintf(k, sizeof k, "p%d", i); store.getString(k, nets[i].pass, sizeof nets[i].pass);
  }
}

void save() {
  store.putUChar("n", nNets);
  for (int i = 0; i < nNets; i++) {
    char k[4];
    snprintf(k, sizeof k, "s%d", i); store.putString(k, nets[i].ssid);
    snprintf(k, sizeof k, "p%d", i); store.putString(k, nets[i].pass);
  }
}

void rebuildMulti() {
  delete multi;                       // WiFiMulti owns strdup'd strings, so rebuild instead of copying
  multi = new WiFiMulti();
  for (int i = 0; i < nNets; i++) multi->addAP(nets[i].ssid, nets[i].pass);
}

String esc(const String& s) {
  String o; for (char c : s) { if (c == '<') o += "&lt;"; else if (c == '>') o += "&gt;"; else if (c == '"') o += "&quot;"; else if (c == '&') o += "&amp;"; else o += c; }
  return o;
}

void scan() {
  int n = WiFi.scanNetworks();
  scanHtml = "";
  for (int i = 0; i < n && i < 15; i++) {
    String s = WiFi.SSID(i);
    if (!s.length()) continue;
    scanHtml += "<option value=\"" + esc(s) + "\">" + esc(s) + " (" + String(WiFi.RSSI(i)) + " dBm)</option>";
  }
  WiFi.scanDelete();
}

const char* CSS =
  "body{background:#0E1114;color:#E3E9EE;font-family:system-ui,sans-serif;margin:0;padding:20px;max-width:460px}"
  "h1{font-size:20px;font-weight:600}p{color:#7F8D99;line-height:1.5}label{display:block;font-size:11px;font-weight:600;"
  "letter-spacing:.08em;text-transform:uppercase;color:#7F8D99;margin:16px 0 6px}input,select{width:100%;box-sizing:border-box;"
  "min-height:44px;background:#141A1F;border:1px solid #26303A;color:#E3E9EE;padding:0 10px;font-size:16px;border-radius:0}"
  "button{margin-top:20px;min-height:44px;width:100%;background:transparent;border:1px solid #4DB6C4;color:#4DB6C4;font-size:15px;border-radius:0}"
  "li{padding:6px 0;border-bottom:1px solid #26303A;list-style:none}ul{padding:0}a{color:#4DB6C4}";

void page() {
  String h = "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><title>SEEv2 CYD WiFi</title><style>";
  h += CSS; h += "</style><h1>Scoreboard WiFi</h1><p>Pick the network the laptop hub is on (your phone hotspot works). ";
  h += "The CYD remembers up to 5 and joins whichever is in range.</p><form method=post action=/save>";
  h += "<label>Network</label><select name=pick onchange=\"document.getElementById('s').value=this.value\"><option value=''>Choose a nearby network</option>";
  h += scanHtml + "</select><label>Network name (SSID)</label><input id=s name=ssid required maxlength=32 autocapitalize=off>";
  h += "<label>Password</label><input name=pass type=password maxlength=64><button>Save and connect</button></form>";
  h += "<p><a href=/rescan>Scan again</a></p><label>Saved</label><ul>";
  for (int i = 0; i < nNets; i++) h += "<li>" + esc(nets[i].ssid) + "</li>";
  if (!nNets) h += "<li>None yet</li>";
  h += "</ul>";
  web.send(200, "text/html", h);
}

void startPortal() {
  if (portalUp) return;
  Serial.println("[wifi] no known network, opening portalUp AP " WIFI_AP_NAME);
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(WIFI_AP_NAME, WIFI_AP_PASS);
  delay(100);
  dns.start(53, "*", WiFi.softAPIP());
  scan();
  if (!webStarted) {
    web.on("/", page);
    web.on("/rescan", [] { scan(); web.sendHeader("Location", "/"); web.send(302); });
    web.on("/save", HTTP_POST, [] {
      String s = web.arg("ssid"); s.trim();
      if (!s.length()) s = web.arg("pick");
      if (!s.length()) { web.send(400, "text/plain", "Network name required"); return; }
      wifiAdd(s.c_str(), web.arg("pass").c_str());
      String h = "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><style>";
      h += CSS; h += "</style><h1>Saved</h1><p>Connecting to <b>" + esc(s) + "</b>. This hotspot closes once the scoreboard joins. "
           "If the password was wrong, the portalUp network comes back in about a minute.</p>";
      web.send(200, "text/html", h);
      tryNow = true;
    });
    web.onNotFound([] {    // captive portal: send every URL to the portalUp page
      web.sendHeader("Location", String("http://") + WiFi.softAPIP().toString() + "/");
      web.send(302);
    });
    web.begin();
    webStarted = true;
  }
  portalUp = true;
  setupSince = millis();
}

void stopPortal() {
  if (!portalUp) return;
  Serial.println("[wifi] joined network, closing portalUp AP");
  dns.stop();
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_STA);
  portalUp = false;
}
} // namespace

void wifiStart() {
  store.begin("wifi", false);
  load();
  if (strlen(WIFI_SSID)) wifiAdd(WIFI_SSID, WIFI_PASS);   // optional seed from secrets.h
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setHostname("cyd-scoreboard");
  rebuildMulti();
  if (nNets == 0) startPortal();
}

void wifiTick() {
  bool up = WiFi.status() == WL_CONNECTED;
  if (up && !wasConnected) {
    gen++; failCount = 0;
    Serial.printf("[wifi] connected to %s, ip %s\n", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
    if (portalUp) { uint32_t t = millis(); while (millis() - t < 2500) { dns.processNextRequest(); web.handleClient(); delay(5); } stopPortal(); }
  }
  wasConnected = up;
  if (portalUp) { dns.processNextRequest(); web.handleClient(); }
  if (up) return;

  uint32_t gap = portalUp ? 30000 : 4000;
  if (nNets && (tryNow || millis() - lastTry > gap)) {
    tryNow = false;
    lastTry = millis();
    if (multi->run(portalUp ? 6000 : 9000) == WL_CONNECTED) return;
    failCount++;
    if (!portalUp && failCount >= 2) startPortal();
    lastTry = millis();
  }
}

bool wifiInSetup() { return portalUp; }
uint32_t wifiGeneration() { return gen; }

bool wifiAdd(const char* ssid, const char* pass) {
  if (!ssid || !*ssid) return false;
  Net n{}; strncpy(n.ssid, ssid, 32); strncpy(n.pass, pass ? pass : "", 64);
  int found = -1;
  for (int i = 0; i < nNets; i++) if (!strcmp(nets[i].ssid, ssid)) found = i;
  int from = found >= 0 ? found : (nNets < WIFI_MAX_SAVED ? nNets : WIFI_MAX_SAVED - 1);
  for (int i = from; i > 0; i--) nets[i] = nets[i - 1];        // newest first
  nets[0] = n;
  if (found < 0 && nNets < WIFI_MAX_SAVED) nNets++;
  save(); rebuildMulti();
  return true;
}

bool wifiForget(const char* ssid) {
  for (int i = 0; i < nNets; i++) if (!strcmp(nets[i].ssid, ssid)) {
    for (int j = i; j < nNets - 1; j++) nets[j] = nets[j + 1];
    nNets--; save(); rebuildMulti();
    return true;
  }
  return false;
}

int wifiSaved(char out[][33], int max) {
  int n = nNets < max ? nNets : max;
  for (int i = 0; i < n; i++) strcpy(out[i], nets[i].ssid);
  return n;
}
