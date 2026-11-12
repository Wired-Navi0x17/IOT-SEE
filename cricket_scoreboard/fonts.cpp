#include "fonts.h"
#include "fonts_smooth.h"

namespace ft {
lgfx::VLWfont label, body, name, numS, numM, numL, score;
static lgfx::PointerWrapper wLabel, wBody, wName, wNumS, wNumM, wNumL, wScore;

static void load(lgfx::VLWfont& f, lgfx::PointerWrapper& w, const uint8_t* data) {
  w.set(data);
  if (!f.loadFont(&w)) Serial.println("[fonts] load failed");
}

void begin() {
  load(label, wLabel, F_LABEL);
  load(body,  wBody,  F_BODY);
  load(name,  wName,  F_NAME);
  load(numS,  wNumS,  F_NUM_S);
  load(numM,  wNumM,  F_NUM_M);
  load(numL,  wNumL,  F_NUM_L);
  load(score, wScore, F_SCORE);
}
}
