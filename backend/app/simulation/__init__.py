"""Vehicle Simulation Package.

Exports:
- VirtualCanBus, CAN IDs, frame encode/decode
- SpeedSensor, BrakePedalSensor
- DoorLockActuator, BrakeActuator
"""

from backend.app.simulation.can_bus import (
    VirtualCanBus,
    CAN_ID_SPEED,
    CAN_ID_BRAKE,
    CAN_ID_DOOR_CMD,
    encode_speed_frame,
    decode_speed_frame,
    encode_brake_frame,
    decode_brake_frame,
    encode_door_cmd,
    decode_door_cmd,
)
from backend.app.simulation.sensors import SpeedSensor, BrakePedalSensor
from backend.app.simulation.actuators import DoorLockActuator, BrakeActuator

__all__ = [
    "VirtualCanBus",
    "CAN_ID_SPEED",
    "CAN_ID_BRAKE",
    "CAN_ID_DOOR_CMD",
    "encode_speed_frame",
    "decode_speed_frame",
    "encode_brake_frame",
    "decode_brake_frame",
    "encode_door_cmd",
    "decode_door_cmd",
    "SpeedSensor",
    "BrakePedalSensor",
    "DoorLockActuator",
    "BrakeActuator",
]
