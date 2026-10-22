"""ECU Door Controller logic wrapper."""

from typing import Optional, Callable


class DoorController:
    """Door Controller handling vehicle speed inputs and actuator commanding."""

    def __init__(self, logic_func: Optional[Callable[[float, bool], str]] = None):
        self._logic_func = logic_func

    def set_logic(self, logic_func: Callable[[float, bool], str]) -> None:
        """Swap underlying control logic implementation."""
        self._logic_func = logic_func

    def evaluate(self, speed: float, is_lost: bool = False) -> str:
        """Evaluate door locking state using active logic.

        Args:
            speed: Vehicle speed in km/h.
            is_lost: True if speed signal timed out or message is lost.

        Returns:
            'LOCKED' or 'UNLOCKED'.
        """
        if self._logic_func is not None:
            import inspect
            sig = inspect.signature(self._logic_func)
            if len(sig.parameters) == 1:
                return self._logic_func(speed)
            return self._logic_func(speed, is_lost)

        # Baseline fallback (> 20 km/h locked)
        if is_lost or speed > 20.0:
            return "LOCKED"
        return "UNLOCKED"
