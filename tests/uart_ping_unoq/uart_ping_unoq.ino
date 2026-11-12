// Temporary UART test for the UNO Q MCU. Sends a line to the CYD every second and checks its reply.
// Serial1 = D0 (RX) / D1 (TX), 3.3 V logic. No Bridge and no Serial here: Bridge.begin() can block the sketch.
// LED3 on the board: GREEN = the CYD answered "ACK", BLUE = bytes arrived but no "ACK", RED = silence.
void led(bool r, bool g, bool b) {      // LEDs are active low
  digitalWrite(LED3_R, r ? LOW : HIGH);
  digitalWrite(LED3_G, g ? LOW : HIGH);
  digitalWrite(LED3_B, b ? LOW : HIGH);
}

void setup() {
  Serial1.begin(115200);
  pinMode(LED3_R, OUTPUT);
  pinMode(LED3_G, OUTPUT);
  pinMode(LED3_B, OUTPUT);
  led(false, false, false);
}

void loop() {
  while (Serial1.available()) Serial1.read();     // drop anything old (CYD boot text etc.)
  Serial1.println("HELLO FROM UNO Q");
  delay(400);                                     // give the CYD time to answer

  String got = "";
  while (Serial1.available() && got.length() < 80) got += (char)Serial1.read();
  if (got.indexOf("ACK") >= 0)      led(false, true, false);   // green
  else if (got.length() > 0)        led(false, false, true);   // blue
  else                              led(true, false, false);   // red

  delay(1000);
}
