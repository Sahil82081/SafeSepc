"""Automotive Actuator Simulators driven by ECU commands."""

from typing import Literal


class DoorLockActuator:
    """Simulates physical automotive central door locking solenoid."""

    def __init__(self, initial_state: Literal["LOCKED", "UNLOCKED"] = "UNLOCKED"):
        self._state: str = initial_state

    def lock(self) -> None:
        """Command actuator to locked position."""
        self._state = "LOCKED"

    def unlock(self) -> None:
        """Command actuator to unlocked position."""
        self._state = "UNLOCKED"

    def set_state(self, state: str) -> None:
        """Set actuator state directly."""
        clean_state = state.strip().upper()
        if clean_state in ("LOCKED", "UNLOCKED"):
            self._state = clean_state
        else:
            raise ValueError(f"Invalid door actuator state: {state}")

    def get_state(self) -> str:
        """Return current physical actuator state ('LOCKED' or 'UNLOCKED')."""
        return self._state

    @property
    def is_locked(self) -> bool:
        """Check if door is currently locked."""
        return self._state == "LOCKED"


class BrakeActuator:
    """Simulates electro-hydraulic braking caliper and master cylinder pressure."""

    def __init__(self, initial_pressure_bar: float = 0.0):
        self.pressure_bar: float = initial_pressure_bar

    def apply(self, pressure_bar: float) -> None:
        """Apply hydraulic brake line pressure in bar."""
        self.pressure_bar = max(0.0, float(pressure_bar))

    def release(self) -> None:
        """Release hydraulic brake pressure."""
        self.pressure_bar = 0.0

    def get_pressure(self) -> float:
        """Return current hydraulic brake pressure."""
        return self.pressure_bar

    @property
    def is_engaged(self) -> bool:
        """True if brake pressure is active."""
        return self.pressure_bar > 0.5
