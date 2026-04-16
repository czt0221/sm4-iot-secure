from __future__ import annotations

from device.network.send import UDPSender
from device.network.udp import UDPPacket


class DeviceNetworkClient:
    def __init__(self, host: str, port: int) -> None:
        self._sender = UDPSender(host=host, port=port)

    def send_packet(self, packet: UDPPacket) -> None:
        self._sender.send(packet)

    def close(self) -> None:
        self._sender.close()
