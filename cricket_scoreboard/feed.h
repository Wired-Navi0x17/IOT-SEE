#pragma once
#include "match_state.h"
// Updates s in place; sets changed when s should be redrawn. Returns ms to wait before the next call.
uint32_t feedPoll(MatchState& s, bool& changed);
// Header note while the link is not healthy (nullptr when fine).
const char* feedLinkNote();
// Telemetry hook: what the screen shows, for the hub.
void feedSetShowing(const char* summary);

uint32_t mockPoll(MatchState& s);   // always available (demo mode)
