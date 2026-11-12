#include "winprob.h"
#include "config.h"
#include <math.h>
#include <string.h>

// Resource-style model: expected runs from b balls with w wickets in hand.
//   E = Z(w) * (1 - exp(-r0*b / Z(w)))
// r0 = scoring rate per ball when wickets are plentiful, Z(w) = run "capacity" of w wickets.
// Calibrated so E(120,10) ~ 165 for T20 and E(300,10) ~ 280 for ODI.
static float capacity(int w) { return w <= 0 ? 0.001f : 20.0f * powf((float)w, 1.48f); }

static float rateFor(const MatchState& s) { return s.totalBalls > 200 ? 1.25f : 1.6f; }

static float expectedRuns(const MatchState& s, int ballsLeft, int wktsInHand) {
  if (ballsLeft <= 0 || wktsInHand <= 0) return 0;
  float Z = capacity(wktsInHand);
  return Z * (1.0f - expf(-rateFor(s) * ballsLeft / Z));
}

static float logistic(float x) { return 1.0f / (1.0f + expf(-x)); }
static float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

int parScore(const MatchState& s) { return s.totalBalls > 200 ? PAR_ODI : PAR_T20; }

int projectedTotal(const MatchState& s) {
  int bl = s.totalBalls - s.balls; if (bl < 0) bl = 0;
  return (int)lroundf(s.runs + expectedRuns(s, bl, 10 - s.wkts));
}

float winProbBatting(const MatchState& s) {
  if (s.totalBalls <= 0) return 0.5f;                  // Tests: no model
  int bl  = s.totalBalls - s.balls; if (bl < 0) bl = 0;
  int wih = 10 - s.wkts;
  float sigma = 2.5f + 1.6f * sqrtf((float)bl);        // spread of remaining runs

  if (s.innings >= 2 && s.target > 0) {
    int need = s.target - s.runs;
    if (need <= 0) return 0.99f;
    if (wih <= 0 || bl == 0) return need == 1 ? 0.5f : 0.01f;
    float E = expectedRuns(s, bl, wih);
    return clampf(logistic((E - need) / (sigma / 1.8f)), 0.03f, 0.97f);
  }
  // 1st innings: projected total vs par, wider spread (2nd innings unknown)
  float proj = s.runs + expectedRuns(s, bl, wih);
  return clampf(logistic((proj - parScore(s)) / ((sigma + 18.0f) / 1.8f)), 0.03f, 0.97f);
}
