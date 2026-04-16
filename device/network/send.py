from __future__ import annotations

import socket

from device.network.udp import UDPPacket


class UDPSender:
    def __init__(self, host: str, port: int) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._target = (host, port)

    def send(self, packet: UDPPacket) -> None:
        self._socket.sendto(packet.to_bytes(), self._target)

    def close(self) -> None:
        self._socket.close()
