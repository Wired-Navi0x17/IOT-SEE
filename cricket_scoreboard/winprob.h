#pragma once
#include "match_state.h"
float winProbBatting(const MatchState& s);  // 0..1, chance the batting side wins
int   projectedTotal(const MatchState& s);
int   parScore(const MatchState& s);
