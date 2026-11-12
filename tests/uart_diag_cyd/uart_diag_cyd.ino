// CYD UART diagnostic using connector P3 (IO35 = RX, input only; IO22 = TX), which has no USB chip on it and leaves the IO21 backlight alone.
// USB stays plugged in: Serial (USB) prints what happens, Serial2 is the link to the UNO Q.
// CYD RGB LED (active low): BLUE blinks 1/s = running and sending "CYD ALIVE";
//   GREEN = RX pin (IO35) went LOW at all;  RED = a clean line arrived and was answered "ACK: ...".
const int LED_R = 4, LED_G = 16, LED_B = 17, RX_PIN = 35, TX_PIN = 22;
uint32_t lastTx = 0, blueUntil = 0, greenUntil = 0, redUntil = 0;

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN);
  pinMode(LED_R, OUTPUT); pinMode(LED_G, OUTPUT); pinMode(LED_B, OUTPUT);
  digitalWrite(LED_R, HIGH); digitalWrite(LED_G, HIGH); digitalWrite(LED_B, HIGH);
  Serial.println("CYD diag ready: Serial2 on IO35 (RX) / IO22 (TX)");
}

void loop() {
  uint32_t now = millis();
  if (now - lastTx >= 1000) {
    lastTx = now;
    Serial2.println("CYD ALIVE");
    blueUntil = now + 150;
  }
  if (digitalRead(RX_PIN) == LOW) greenUntil = now + 300;
  if (Serial2.available()) {
    redUntil = now + 300;
    String msg = Serial2.readStringUntil('\n');
    Serial.print("RX from UNO Q: "); Serial.println(msg);
    Serial2.print("ACK: "); Serial2.println(msg);
  }
  digitalWrite(LED_B, now < blueUntil ? LOW : HIGH);
  digitalWrite(LED_G, now < greenUntil ? LOW : HIGH);
  digitalWrite(LED_R, now < redUntil ? LOW : HIGH);
}
