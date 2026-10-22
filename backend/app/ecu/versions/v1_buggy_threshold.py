"""ECU Door Controller Logic - Version 1 Buggy Threshold.

Bug:
- Speed threshold is incorrectly configured to 80.0 km/h instead of 20.0 km/h.
- For speed <= 80.0 km/h, the door remains UNLOCKED.
"""


def evaluate(speed: float, is_lost: bool = False) -> str:
    """Evaluate door lock state with buggy threshold of 80.0 km/h.

    Args:
        speed: Vehicle speed in km/h.
        is_lost: True if speed message is lost.

    Returns:
        'LOCKED' only when speed > 80.0 km/h; 'UNLOCKED' otherwise.
    """
    if speed > 80.0:
        return "LOCKED"
    return "UNLOCKED"


class DoorControllerLogic:
    """Controller implementation for v1_buggy_threshold."""

    def __init__(self, speed_threshold: float = 80.0):
        self.speed_threshold = speed_threshold

    def evaluate(self, speed: float, is_lost: bool = False) -> str:
        """Evaluate door lock command with buggy threshold."""
        return evaluate(speed, is_lost)
