"""Virtual CAN Bus implementation using python-can.

Provides:
- Standard automotive arbitration IDs:
  - CAN_ID_SPEED: 0x1F0
  - CAN_ID_BRAKE: 0x200
  - CAN_ID_DOOR_CMD: 0x3A0
- Binary frame encoding and decoding.
- VirtualCanBus manager supporting broadcast and message receipt.
"""

from typing import Optional, Tuple
import struct
import can

CAN_ID_SPEED: int = 0x1F0
CAN_ID_BRAKE: int = 0x200
CAN_ID_DOOR_CMD: int = 0x3A0


def encode_speed_frame(speed: float, is_valid: bool = True) -> can.Message:
    """Encode vehicle speed telemetry into a standard 8-byte CAN frame.

    Payload format:
    - Byte 0-1: Scaled speed (speed * 100 as uint16, little-endian)
    - Byte 2: Status flag (0x00 = valid, 0x01 = lost/timed-out/invalid)
    - Byte 3-7: Padding zeros
    """
    speed_scaled = max(0, min(65535, int(speed * 100)))
    status = 0x00 if is_valid else 0x01
    data = struct.pack("<HB5x", speed_scaled, status)
    return can.Message(
        arbitration_id=CAN_ID_SPEED,
        data=data,
        is_extended_id=False,
    )


def decode_speed_frame(msg: can.Message) -> Tuple[float, bool]:
    """Decode speed and validity status from a CAN frame."""
    if msg.arbitration_id != CAN_ID_SPEED or len(msg.data) < 3:
        return 0.0, False
    speed_scaled, status = struct.unpack("<HB", msg.data[:3])
    speed = float(speed_scaled) / 100.0
    is_valid = (status == 0x00)
    return speed, is_valid


def encode_brake_frame(pedal_position: float, switch_active: bool = True) -> can.Message:
    """Encode brake sensor frame into CAN payload (0-100% position + switch status)."""
    pedal_byte = max(0, min(255, int(pedal_position * 2.55)))
    switch_byte = 0x01 if switch_active else 0x00
    data = bytes([pedal_byte, switch_byte, 0, 0, 0, 0, 0, 0])
    return can.Message(
        arbitration_id=CAN_ID_BRAKE,
        data=data,
        is_extended_id=False,
    )


def decode_brake_frame(msg: can.Message) -> Tuple[float, bool]:
    """Decode brake pedal position and switch status from CAN frame."""
    if msg.arbitration_id != CAN_ID_BRAKE or len(msg.data) < 2:
        return 0.0, False
    pedal_pct = float(msg.data[0]) / 2.55
    switch_active = bool(msg.data[1] == 0x01)
    return pedal_pct, switch_active


def encode_door_cmd(state: str) -> can.Message:
    """Encode door actuator command: 0x01 = LOCKED, 0x00 = UNLOCKED."""
    cmd_byte = 0x01 if state.upper() == "LOCKED" else 0x00
    data = bytes([cmd_byte, 0, 0, 0, 0, 0, 0, 0])
    return can.Message(
        arbitration_id=CAN_ID_DOOR_CMD,
        data=data,
        is_extended_id=False,
    )


def decode_door_cmd(msg: can.Message) -> str:
    """Decode door actuator command from CAN frame."""
    if msg.arbitration_id != CAN_ID_DOOR_CMD or not msg.data:
        return "UNLOCKED"
    return "LOCKED" if msg.data[0] == 0x01 else "UNLOCKED"


class VirtualCanBus:
    """Virtual CAN Bus wrapper for testing and simulation using python-can."""

    def __init__(self, channel: str = "safespec_virtual_bus"):
        self.channel = channel
        self.bus = can.Bus(
            interface="virtual",
            channel=self.channel,
            receive_own_messages=True,
        )

    def send(self, msg: can.Message) -> bool:
        """Transmit a CAN message onto the virtual bus."""
        try:
            self.bus.send(msg)
            return True
        except can.CanError:
            return False

    def recv(self, timeout: float = 0.1) -> Optional[can.Message]:
        """Receive a CAN frame from the virtual bus with timeout."""
        try:
            return self.bus.recv(timeout=timeout)
        except can.CanError:
            return None

    def flush(self) -> None:
        """Discard unread frames in the buffer."""
        while self.recv(timeout=0.01) is not None:
            pass

    def shutdown(self) -> None:
        """Cleanly shut down virtual bus channel."""
        try:
            self.bus.shutdown()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
