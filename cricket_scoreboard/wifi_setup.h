#pragma once
#include <stdint.h>
// Multi-network WiFi with a captive setup portal.
// Saved networks live in NVS (up to 5). If none is in range, the CYD opens its own
// access point "UCIS-CYD" with a setup page at 192.168.4.1 (QR code on screen).
#define WIFI_AP_NAME "UCIS-CYD"
#define WIFI_AP_PASS "scoreboard"
#define WIFI_MAX_SAVED 5

void wifiStart();                 // network task, once
void wifiTick();                  // network task, every loop
bool wifiInSetup();               // setup portal active
bool wifiAdd(const char* ssid, const char* pass);
bool wifiForget(const char* ssid);
int  wifiSaved(char out[][33], int max);
uint32_t wifiGeneration();        // bumps on every (re)connection, so listeners can re-bind
