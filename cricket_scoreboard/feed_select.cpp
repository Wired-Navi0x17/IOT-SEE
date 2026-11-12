#include "config.h"
#include "feed.h"
#if FEED_MODE == FEED_MOCK
uint32_t feedPoll(MatchState& s, bool& changed) { changed = true; return mockPoll(s); }
const char* feedLinkNote() { return nullptr; }
void feedSetShowing(const char*) {}
#endif
