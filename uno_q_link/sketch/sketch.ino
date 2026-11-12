// UNO Q MCU (STM32U585): byte pipe between the Linux side (Bridge) and the CYD on the D0/D1 header.
// Which Serial object is D0/D1 depends on the board package. App Lab on the UNO Q uses arduino:zephyr 0.52.0,
// where D0/D1 (usart1) is `Serial` and `Serial1` is the Bridge's own link to Linux (never touch it).
// In 1.1.0+ the Bridge moved to its own port, `Serial` became the Bridge monitor and D0/D1 became `Serial1`.
//   Linux -> CYD : Bridge call "cyd_write"(chunk)  ->  CYD.print(chunk)
//   CYD -> Linux : CYD bytes, 200 at a time    ->  Bridge.notify("cyd_part", chunk)
// Bridge messages are capped at 256 bytes, so both directions move chunks; the Python side
// splits and reassembles at '\n'. Wiring: D1 (TX) -> CYD IO35, D0 (RX) <- CYD IO22, GND -> GND.
#include <Arduino_RouterBridge.h>

#define CYD Serial   // D0 = RX, D1 = TX (arduino:zephyr 0.52.0)

constexpr size_t CHUNK = 200;
char buf[CHUNK + 1];
size_t n = 0;
uint32_t lastByte = 0;

void cydWrite(String chunk) { CYD.print(chunk); }

void setup() {
  CYD.begin(115200);                      // D0 = RX, D1 = TX, 3.3 V logic
  Bridge.begin();
  Bridge.provide_safe("cyd_write", cydWrite);
}

void flush() {
  if (!n) return;
  buf[n] = 0;
  Bridge.notify("cyd_part", String(buf));
  n = 0;
}

void loop() {
  while (CYD.available()) {
    int b = CYD.read();
    if (b != '\n' && (b < 0x20 || b > 0x7E)) continue;   // JSON lines are plain ASCII: drop line noise and boot bytes
    char c = (char)b;
    buf[n++] = c;
    lastByte = millis();
    if (n == CHUNK || c == '\n') flush();
  }
  if (n && millis() - lastByte > 50) flush();   // partial line idle: send what we have
}
