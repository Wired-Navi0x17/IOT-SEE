#pragma once
#include <stdint.h>
// Live team colours for the current match (RGB888). Start as the purple/turquoise fallback.
extern uint32_t COL_A, COL_B;
// Pick colours for Team A / Team B by IPL short code or full name ("MI", "Mumbai Indians").
// Team A keeps its primary; Team B swaps to its alternate when the two are too alike.
// Returns true when the colours changed.
bool teamColorsApply(const char* a, const char* b);
// Hub override: colours already chosen by the hub ("ca"/"cb" hex). 0 = not given.
void teamColorsSet(uint32_t a, uint32_t b);
// Hub override of the beam ramps (deep/bright/hot per team); pass nullptr or a zero ramp to derive from COL_A/COL_B.
void teamRampsSet(const uint32_t a[3], const uint32_t b[3]);
extern uint32_t RAMP_A[3], RAMP_B[3];
bool teamColorsTake();   // true once after any change (the liquid band rebuilds its ramps)
// "Mumbai Indians" / "MI" -> "MI"; nullptr when the side is not an IPL franchise.
const char* iplCode(const char* nameOrShort);
