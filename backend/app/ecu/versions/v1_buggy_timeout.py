"""ECU Door Controller Logic - Version 1 Buggy Timeout.

Bug:
- Ignores lost speed messages / failsafe lock requirement.
- When speed signal is lost or timed out, it ignores the loss and leaves the door UNLOCKED.
"""


def evaluate(speed: float, is_lost: bool = True) -> str:
    """Evaluate door lock state with buggy timeout handling.

    Args:
        speed: Vehicle speed in km/h.
        is_lost: True if speed message is lost or unconfirmed (defaults to True for timeout bug test).

    Returns:
        'UNLOCKED' if speed message is lost or speed <= 20.0.
    """
    if is_lost:
        # Bug: fails to fail-safe to LOCKED on lost message
        return "UNLOCKED"
    if speed > 20.0:
        return "LOCKED"
    return "UNLOCKED"


class DoorControllerLogic:
    """Controller implementation for v1_buggy_timeout."""

    def __init__(self, speed_threshold: float = 20.0):
        self.speed_threshold = speed_threshold

    def evaluate(self, speed: float, is_lost: bool = True) -> str:
        """Evaluate door lock command with buggy timeout handling."""
        return evaluate(speed, is_lost)
