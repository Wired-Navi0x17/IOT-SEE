#pragma once
#include <stdint.h>

enum class MatchEvent : uint8_t { None, Four, Six, Wicket };

struct Batter { char name[24]; int16_t runs; int16_t balls; };
struct Bowler { char name[24]; int16_t balls; int16_t maidens; int16_t runs; int16_t wkts; };

struct MatchState {
  char series[48];
  char format[8];          // "T20", "ODI", "TEST"
  char teamA[6], teamB[6]; // A = left, B = right; colours from ipl_teams.cpp
  uint32_t colA, colB;     // RGB888 chosen by the hub (0 = pick locally from the IPL table)
  bool battingIsA;
  uint8_t innings;         // 1 or 2
  int16_t runs, wkts, balls, totalBalls, target;   // balls = legal balls bowled
  Batter striker, nonStriker;
  Bowler bowler;
  char nextBat[24], nextBowl[24];
  char thisOver[8][4]; uint8_t nThisOver;          // ".", "1", "4", "W", "Wd"...
  char status[64];
  bool live, ended, hasPlayers;
  MatchEvent lastEvent; uint32_t eventSeq;
  uint32_t version;
};
