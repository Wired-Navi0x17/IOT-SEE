#pragma once
#include "display_config.h"
#include "match_state.h"
void liquidBegin(LGFX* lcd, int y);
void liquidSetTarget(float pA);                       // Team A share 0..1
void liquidSetLabels(const char* a, const char* b, const char* overrideText);
void liquidEvent(MatchEvent e, bool battingIsA);
void liquidFrame(float dt);
void liquidIdentify();                                // three seam flashes so you can spot the unit
