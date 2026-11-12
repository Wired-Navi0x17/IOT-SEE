#pragma once
#include <stdint.h>
// Commands from the hub are queued by the network task and applied by the display loop.
enum class Cmd : uint8_t { Brightness, Rotate, Invert, Identify, Reboot, Ping, Qr };
struct DeviceCmd { Cmd cmd; int32_t arg; uint32_t id; };
struct DeviceAck { uint32_t id; bool ok; char detail[32]; };

void cmdInit();
bool cmdPush(const DeviceCmd& c);          // network task
bool cmdPop(DeviceCmd& c);                 // display loop
void ackPush(uint32_t id, bool ok, const char* detail);   // display loop
bool ackPop(DeviceAck& a);                 // network task

// Live values the display loop publishes for telemetry
extern volatile float g_fps;
extern volatile int   g_brightness;
extern volatile int   g_rotation;
extern volatile bool  g_inverted;
extern volatile bool  g_qrShow;        // QR join screen is up
extern char           g_qrUrl[96];     // what the QR encodes (set by the hub, default below)
extern volatile bool  g_tapPending;    // display loop -> network task: a short tap happened
