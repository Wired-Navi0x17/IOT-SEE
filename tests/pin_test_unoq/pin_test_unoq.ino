// UNO Q pin test: drive D1 (PB6) as a plain GPIO, 0.5 s high / 0.5 s low, no UART involved.
// With the CYD diagnostic sketch running, the CYD's GREEN LED should flash every second if D1 reaches CYD RX.
// LED3 blue = D1 is HIGH, off = D1 is LOW (so you can see the sketch running).
void setup() {
  pinMode(D1, OUTPUT);
  pinMode(LED3_R, OUTPUT); pinMode(LED3_G, OUTPUT); pinMode(LED3_B, OUTPUT);
  digitalWrite(LED3_R, HIGH); digitalWrite(LED3_G, HIGH); digitalWrite(LED3_B, HIGH);
}

void loop() {
  digitalWrite(D1, HIGH);
  digitalWrite(LED3_B, LOW);
  delay(500);
  digitalWrite(D1, LOW);
  digitalWrite(LED3_B, HIGH);
  delay(500);
}
