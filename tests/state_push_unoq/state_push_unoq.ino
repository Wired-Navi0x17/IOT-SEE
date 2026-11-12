// UNO Q test: push a sample match-state line to the CYD over Serial1 (D1 -> CYD IO35) every 2 s,
// in the same JSON format the hub sends (hub service.to_device). The CYD scoreboard (FEED_UART) should show it.
// Runs adds one ball each push so the screen visibly updates. LED3 green flashes when the CYD sends anything back.
int balls = 96, runs = 151;

void setup() {
  Serial1.begin(115200);
  pinMode(LED3_G, OUTPUT); digitalWrite(LED3_G, HIGH);
}

void loop() {
  balls = balls >= 119 ? 96 : balls + 1;
  runs += (balls % 3 == 0) ? 4 : 1;
  if (balls == 96) runs = 151;
  char line[512];
  snprintf(line, sizeof line,
    "{\"t\":\"state\",\"series\":\"IPL 2026\",\"format\":\"T20\",\"a\":\"CSK\",\"b\":\"MI\",\"ca\":\"F9CD05\",\"cb\":\"1F7FE8\","
    "\"batA\":false,\"inn\":2,\"r\":%d,\"w\":4,\"bl\":%d,\"tb\":120,\"tgt\":183,"
    "\"st\":{\"n\":\"S. YADAV\",\"r\":48,\"b\":29},\"ns\":{\"n\":\"H. PANDYA\",\"r\":22,\"b\":14},"
    "\"bw\":{\"n\":\"M. PATHIRANA\",\"b\":%d,\"m\":0,\"r\":31,\"w\":2},\"nb\":\"T. DAVID\",\"nw\":\"R. JADEJA\","
    "\"ov\":[\"1\",\"4\",\".\"],\"status\":\"MI need %d runs\",\"live\":true,\"ended\":false,\"hp\":true,\"ev\":\"none\",\"es\":0}",
    runs, balls, balls % 24, 183 - runs);
  Serial1.println(line);

  uint32_t t = millis();
  bool heard = false;
  while (millis() - t < 2000) {
    while (Serial1.available()) { Serial1.read(); heard = true; }
    digitalWrite(LED3_G, heard ? LOW : HIGH);
  }
}
