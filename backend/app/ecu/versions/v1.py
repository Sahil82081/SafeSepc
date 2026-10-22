"""ECU Door Controller Logic - Version 1 (Correct Baseline).

Requirements:
- When speed > 20.0 km/h: Door must be LOCKED.
- When speed <= 20.0 km/h: Door is UNLOCKED.
- Fail-safe: If speed message is lost (timeout), door must be LOCKED.
"""


def evaluate(speed: float, is_lost: bool = False) -> str:
    """Evaluate door lock state.

    Args:
        speed: Vehicle speed in km/h.
        is_lost: True if speed message is lost or timed out.

    Returns:
        'LOCKED' if moving or signal lost; 'UNLOCKED' otherwise.
    """
    if is_lost or speed > 20.0:
        return "LOCKED"
    return "UNLOCKED"


class DoorControllerLogic:
    """Controller implementation for v1."""

    def __init__(self, speed_threshold: float = 20.0):
        self.speed_threshold = speed_threshold

    def evaluate(self, speed: float, is_lost: bool = False) -> str:
        """Evaluate door lock command."""
        return evaluate(speed, is_lost)
