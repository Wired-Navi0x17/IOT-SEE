// Temporary UART test for the CYD (ESP32-2432S028R). Answers every line with "ACK: <line>".
// Serial = UART0 = GPIO1 (TX) / GPIO3 (RX) = CYD P1 connector, shared with the USB serial chip.
void setup() {
  Serial.begin(115200);
}

void loop() {
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    Serial.print("ACK: ");
    Serial.println(msg);
  }
}
