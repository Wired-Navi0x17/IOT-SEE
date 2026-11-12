#pragma once
#include <ArduinoJson.h>
#include "match_state.h"
#include "device_cmd.h"
void copyStr(char* dst, size_t n, JsonVariantConst v);
// {"t":"state",...} -> MatchState (keys from hub service.to_device)
void parseStateJson(JsonObjectConst o, MatchState& out);
// display commands shared by every feed; false = not a display command
bool cmdFromJson(const char* name, JsonObjectConst args, DeviceCmd& c);
