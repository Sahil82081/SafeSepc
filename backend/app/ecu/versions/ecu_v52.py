"""ECU Door Controller Logic - Version 1 Corrected Threshold and Fail-Safe.

Requirements Satisfied:
- REQ-050: When vehicle speed exceeds 20.0 km/h, lock all doors.
- Safety Requirement: When speed message is lost (is_lost=True), fail-safe to LOCKED.
"""


def evaluate(speed: float, is_lost: bool = False) -> str:
    """Evaluate door lock state with correct threshold and fail-safe logic.

    Args:
        speed: Vehicle speed in km/h.
        is_lost: True if speed message is lost.

    Returns:
        'LOCKED' if is_lost is True or speed > 20.0; 'UNLOCKED' otherwise.
    """
    if is_lost or speed > 20.0:
        return "LOCKED"
    return "UNLOCKED"


class DoorControllerLogic:
    """Controller implementation for corrected REQ-050 logic."""

    def __init__(self, speed_threshold: float = 20.0):
        self.speed_threshold = speed_threshold

    def evaluate(self, speed: float, is_lost: bool = False) -> str:
        """Evaluate door lock command with correct threshold and fail-safe."""
        return evaluate(speed, is_lost)