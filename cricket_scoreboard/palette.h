#pragma once
#include <stdint.h>
// RGB888 colours (LovyanGFX treats uint32_t as RGB888)
constexpr uint32_t COL_BG    = 0x0B0A12;
constexpr uint32_t COL_LINE  = 0x211E2A;
constexpr uint32_t COL_DIM   = 0x8A86A0;
constexpr uint32_t COL_TXT   = 0xF2F0F7;
#include "ipl_teams.h"                       // COL_A / COL_B: live per-match team colours
constexpr uint32_t COL_WKT   = 0xB8336A;
constexpr uint32_t COL_CHIP  = 0x1A1726;
constexpr uint32_t COL_CHIPB = 0x3A3550;
constexpr uint32_t COL_LIVE  = 0xFF4D6D;
constexpr uint32_t COL_PILL  = 0x120F1E;
