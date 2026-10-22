"""Virtual Electronic Control Unit (ECU) runtime.

Features:
- Connects to VirtualCanBus to read incoming telemetry.
- Loads control logic dynamically from versioned files in ecu/versions/ at runtime.
- Drives DoorLockActuator and BrakeActuator.
- Provides runtime version swapping between v1, v1_buggy_threshold, and v1_buggy_timeout.
"""

from typing import Optional, Dict, Any, Callable
from pathlib import Path
import importlib.util
import inspect
import can

from backend.app.simulation.can_bus import (
    VirtualCanBus,
    CAN_ID_SPEED,
    CAN_ID_BRAKE,
    decode_speed_frame,
    decode_brake_frame,
    encode_door_cmd,
)
from backend.app.simulation.actuators import DoorLockActuator, BrakeActuator
from backend.app.ecu.door_controller import DoorController
from backend.app.ecu.brake_controller import BrakeController


class VirtualECU:
    """Virtual ECU driving actuators from CAN bus telemetry with runtime version swapping."""

    def __init__(
        self,
        bus: Optional[VirtualCanBus] = None,
        initial_version: str = "v1",
        version: Optional[str] = None,
        versions_dir: Optional[Path] = None,
    ):
        selected_version = version if version is not None else initial_version
        self.bus = bus
        self.versions_dir = (
            versions_dir
            if versions_dir is not None
            else Path(__file__).resolve().parent / "versions"
        )

        # Actuators
        self.door_actuator = DoorLockActuator()
        self.brake_actuator = BrakeActuator()

        # Controllers
        self.door_controller = DoorController()
        self.brake_controller = BrakeController()

        # Version state
        self.current_version: str = ""
        self._evaluate_func: Optional[Callable] = None
        self.load_version(selected_version)

    def load_version(self, version_name: str) -> None:
        """Dynamically load control logic from ecu/versions/{version_name}.py at runtime.

        Supports:
        - v1 (correct baseline: locked when speed > 20)
        - v1_buggy_threshold (buggy 80 km/h threshold)
        - v1_buggy_timeout (ignores lost speed message)
        """
        clean_name = version_name.replace(".py", "")
        file_path = self.versions_dir / f"{clean_name}.py"

        if not file_path.exists():
            # Check with 'ecu_' prefix
            alt_path = self.versions_dir / f"ecu_{clean_name}.py"
            if alt_path.exists():
                file_path = alt_path
            elif clean_name.startswith("ecu_"):
                alt_path2 = self.versions_dir / f"{clean_name[4:]}.py"
                if alt_path2.exists():
                    file_path = alt_path2
                else:
                    raise FileNotFoundError(f"ECU version file not found: {file_path}")
            else:
                raise FileNotFoundError(f"ECU version file not found: {file_path}")

        # Dynamic import from file location
        spec = importlib.util.spec_from_file_location(f"ecu_version_{clean_name}", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module spec for {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "evaluate"):
            raise AttributeError(f"ECU version {clean_name} missing 'evaluate' function.")

        self._evaluate_func = module.evaluate
        self.door_controller.set_logic(self._evaluate_func)
        self.current_version = clean_name

    def handle_speed(self, speed: float, is_lost: Optional[bool] = None) -> str:
        """Directly process speed input and update the physical door actuator.

        Args:
            speed: Vehicle speed in km/h.
            is_lost: True if speed message is lost. If None, uses version default.

        Returns:
            New commanded door state ('LOCKED' or 'UNLOCKED').
        """
        if self._evaluate_func is None:
            state = "UNLOCKED"
        else:
            sig = inspect.signature(self._evaluate_func)
            if is_lost is not None:
                state = self._evaluate_func(speed, is_lost)
            else:
                # Call with signature default
                if len(sig.parameters) >= 2:
                    default_lost = sig.parameters["is_lost"].default
                    if default_lost != inspect.Parameter.empty:
                        state = self._evaluate_func(speed, default_lost)
                    else:
                        state = self._evaluate_func(speed, False)
                else:
                    state = self._evaluate_func(speed)

        # Drive physical actuator
        if state == "LOCKED":
            self.door_actuator.lock()
        else:
            self.door_actuator.unlock()

        # Broadcast door status if bus is attached
        if self.bus is not None:
            self.bus.send(encode_door_cmd(state))

        return state

    def process_can_message(self, msg: can.Message) -> Dict[str, Any]:
        """Parse CAN message and update corresponding controller & actuator."""
        result: Dict[str, Any] = {"id": hex(msg.arbitration_id)}

        if msg.arbitration_id == CAN_ID_SPEED:
            speed, is_valid = decode_speed_frame(msg)
            is_lost = not is_valid

            # For v1_buggy_timeout, lost messages or unconfirmed frames trigger the bug
            state = self.handle_speed(speed, is_lost=is_lost)
            result.update({
                "type": "SPEED",
                "speed": speed,
                "is_valid": is_valid,
                "door_state": state,
            })

        elif msg.arbitration_id == CAN_ID_BRAKE:
            pedal_pct, switch_active = decode_brake_frame(msg)
            pressure = self.brake_controller.evaluate(pedal_pct, switch_active)
            self.brake_actuator.apply(pressure)
            result.update({
                "type": "BRAKE",
                "pedal_pct": pedal_pct,
                "switch_active": switch_active,
                "pressure_bar": pressure,
            })

        return result

    def step(self, timeout: float = 0.05) -> Optional[Dict[str, Any]]:
        """Read and process next pending sensor CAN frame from the virtual bus."""
        if self.bus is None:
            return None

        while True:
            msg = self.bus.recv(timeout=timeout)
            if msg is None:
                return None
            if msg.arbitration_id in (CAN_ID_SPEED, CAN_ID_BRAKE):
                return self.process_can_message(msg)
