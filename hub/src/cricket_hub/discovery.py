"""LAN discovery: the hub broadcasts 'SEEV2HUB <port>' every 2 s so the CYD finds it on any network
(home WiFi, phone hotspot) without knowing the laptop's IP. mDNS (cricket-hub.local) is the backup."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
import subprocess

log = logging.getLogger("discovery")
BEACON_PORT = 47800


def broadcast_targets() -> set[str]:
    targets = {"255.255.255.255"}
    try:
        out = subprocess.run(["ip", "-o", "-4", "addr", "show", "scope", "global"], capture_output=True, text=True, timeout=2).stdout
        for line in out.splitlines():
            parts = line.split()
            if "inet" in parts:
                net = ipaddress.ip_interface(parts[parts.index("inet") + 1]).network
                targets.add(str(net.broadcast_address))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    adv = os.environ.get("HUB_ADVERTISE_IP")
    if adv:                                  # e.g. the UNO Q hotspot 10.42.0.1 -> 10.42.0.255
        try:
            targets.add(str(ipaddress.ip_interface(f"{adv}/24").network.broadcast_address))
        except ValueError:
            pass
    return targets


async def beacon(port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    msg = f"SEEV2HUB {port}".encode()
    targets, refreshed = broadcast_targets(), 0
    while True:
        refreshed += 1
        if refreshed % 15 == 0:            # networks change (hotspot <-> home): re-read every 30 s
            targets = broadcast_targets()
        for t in targets:
            try:
                sock.sendto(msg, (t, BEACON_PORT))
            except OSError:
                pass                          # no route right now (WiFi switching)
        await asyncio.sleep(2)
