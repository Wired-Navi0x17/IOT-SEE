// CYD pin probe: report level and edge count of IO35 and IO22 (both on P3) over USB serial.
// Used with the UNO Q pin_test sketch driving D1 as a 1 Hz square wave: a pin that is connected to D1 shows ~2 edges/s.
const int PINS[2] = {35, 22};
volatile uint32_t edges[2] = {0, 0};
void IRAM_ATTR on35() { edges[0]++; }
void IRAM_ATTR on22() { edges[1]++; }

void setup() {
  Serial.begin(115200);
  pinMode(35, INPUT); pinMode(22, INPUT);
  attachInterrupt(35, on35, CHANGE);
  attachInterrupt(22, on22, CHANGE);
  Serial.println("pin probe ready: watching IO35 and IO22");
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last >= 1000) {
    last = millis();
    noInterrupts(); uint32_t a = edges[0], b = edges[1]; edges[0] = edges[1] = 0; interrupts();
    Serial.printf("IO35 lvl=%d edges=%u | IO22 lvl=%d edges=%u\n", digitalRead(35), a, digitalRead(22), b);
  }
}
