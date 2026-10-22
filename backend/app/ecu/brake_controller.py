"""ECU Brake Controller logic."""


class BrakeController:
    """Brake Controller calculating hydraulic brake pressure from sensor inputs."""

    def __init__(self, max_pressure_bar: float = 120.0):
        self.max_pressure_bar = max_pressure_bar

    def evaluate(self, pedal_pct: float, switch_active: bool = True) -> float:
        """Compute commanded brake pressure in bar.

        Args:
            pedal_pct: Pedal depression percentage (0.0 - 100.0).
            switch_active: Brake pedal switch state.

        Returns:
            Commanded hydraulic line pressure in bar.
        """
        if not switch_active or pedal_pct <= 0.0:
            return 0.0

        clamped_pct = max(0.0, min(100.0, float(pedal_pct)))
        return (clamped_pct / 100.0) * self.max_pressure_bar
