#include "device_cmd.h"
#include <Arduino.h>
#include <string.h>

static QueueHandle_t qCmd, qAck;
volatile float g_fps = 0;
volatile int   g_brightness = 200;
volatile int   g_rotation = 1;
volatile bool  g_inverted = false;
volatile bool  g_qrShow = false;
char           g_qrUrl[96] = "http://10.42.0.1:8000/play";
volatile bool  g_tapPending = false;

void cmdInit() {
  qCmd = xQueueCreate(8, sizeof(DeviceCmd));
  qAck = xQueueCreate(8, sizeof(DeviceAck));
}
bool cmdPush(const DeviceCmd& c) { return xQueueSend(qCmd, &c, 0) == pdTRUE; }
bool cmdPop(DeviceCmd& c) { return xQueueReceive(qCmd, &c, 0) == pdTRUE; }
void ackPush(uint32_t id, bool ok, const char* detail) {
  DeviceAck a{id, ok, {0}};
  if (detail) strncpy(a.detail, detail, sizeof a.detail - 1);
  xQueueSend(qAck, &a, 0);
}
bool ackPop(DeviceAck& a) { return xQueueReceive(qAck, &a, 0) == pdTRUE; }
