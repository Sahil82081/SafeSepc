"""Vehicle Sensor Simulators broadcasting telemetry over Virtual CAN Bus."""

from typing import Optional
import can

from backend.app.simulation.can_bus import (
    VirtualCanBus,
    encode_speed_frame,
    encode_brake_frame,
)


class SpeedSensor:
    """Simulates wheel speed telemetry sensor."""

    def __init__(
        self,
        initial_speed: float = 0.0,
        is_valid: bool = True,
        bus: Optional[VirtualCanBus] = None,
    ):
        self.speed: float = initial_speed
        self.is_valid: bool = is_valid
        self.bus: Optional[VirtualCanBus] = bus

    def set_speed(self, speed: float, is_valid: bool = True) -> None:
        """Update simulated speed and validity flag."""
        self.speed = max(0.0, float(speed))
        self.is_valid = is_valid

    def create_frame(self) -> can.Message:
        """Create CAN message representation."""
        return encode_speed_frame(self.speed, self.is_valid)

    def broadcast(self, bus: Optional[VirtualCanBus] = None) -> bool:
        """Transmit current speed frame onto the virtual CAN bus."""
        target_bus = bus if bus is not None else self.bus
        if target_bus is None:
            raise ValueError("No CAN bus instance provided for broadcast.")
        return target_bus.send(self.create_frame())


class BrakePedalSensor:
    """Simulates brake pedal position and depression switch."""

    def __init__(
        self,
        initial_position: float = 0.0,
        switch_active: bool = False,
        bus: Optional[VirtualCanBus] = None,
    ):
        self.pedal_position: float = initial_position
        self.switch_active: bool = switch_active
        self.bus: Optional[VirtualCanBus] = bus

    def set_brake(self, pedal_position: float, switch_active: Optional[bool] = None) -> None:
        """Update brake pedal position (0-100%) and switch."""
        self.pedal_position = max(0.0, min(100.0, float(pedal_position)))
        if switch_active is not None:
            self.switch_active = switch_active
        else:
            self.switch_active = (self.pedal_position > 5.0)

    def create_frame(self) -> can.Message:
        """Create CAN message representation."""
        return encode_brake_frame(self.pedal_position, self.switch_active)

    def broadcast(self, bus: Optional[VirtualCanBus] = None) -> bool:
        """Transmit brake frame onto the virtual CAN bus."""
        target_bus = bus if bus is not None else self.bus
        if target_bus is None:
            raise ValueError("No CAN bus instance provided for broadcast.")
        return target_bus.send(self.create_frame())
