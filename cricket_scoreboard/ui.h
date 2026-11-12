#pragma once
#include "display_config.h"
#include "match_state.h"
void uiBegin(LGFX* lcd);
// linkNote: shown in the header in place of the series when non-null (e.g. "HUB OFFLINE")
void uiDrawHeader(const MatchState& s, bool wifiOk, const char* linkNote);
void uiDrawBody(const MatchState& s);   // score, players, footer
// Full-screen WiFi setup instructions with a join QR code.
void uiDrawWifiSetup(const char* apName, const char* apPass, int savedCount);
