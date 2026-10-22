"""Automotive Fault Injection Suite.

Implements standard ISO 26262 fault models:
- MessageLostFault: CAN frame dropped / signal loss
- MessageDelayedFault: Latency injection / delayed transmission
- SensorStuckFault: Sensor value frozen at fixed reading
"""

import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class Fault(BaseModel):
    """Base automotive fault specification."""

    name: str
    description: str


class MessageLostFault(Fault):
    """Simulates communication loss or frame drop on CAN bus."""

    name: str = "MESSAGE_LOST"
    description: str = "Simulates total loss or dropping of the sensor message."

    def apply(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Modify inputs to represent a lost CAN frame."""
        mutated = dict(inputs)
        mutated["is_lost"] = True
        mutated["is_valid"] = False
        return mutated


class MessageDelayedFault(Fault):
    """Simulates transmission latency exceeding nominal deadlines."""

    name: str = "MESSAGE_DELAYED"
    description: str = "Injects transmission delay exceeding deadline."
    delay_ms: float = Field(default=350.0, description="Injected delay in milliseconds")

    def apply(self, inputs: Dict[str, Any], execute_sleep: bool = False) -> Dict[str, Any]:
        """Modify inputs to reflect message delay and optionally sleep."""
        mutated = dict(inputs)
        mutated["latency_ms"] = self.delay_ms
        mutated["is_delayed"] = True
        if execute_sleep and self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000.0)
        return mutated


class SensorStuckFault(Fault):
    """Simulates sensor hardware freezing at an erroneous fixed reading."""

    name: str = "SENSOR_STUCK"
    description: str = "Sensor reading remains frozen regardless of vehicle state."
    stuck_var: str = Field(default="speed", description="Target sensor variable name")
    stuck_value: Any = Field(default=0.0, description="Frozen value output")

    def apply(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Freeze target variable to stuck value."""
        mutated = dict(inputs)
        mutated[self.stuck_var] = self.stuck_value
        mutated["is_stuck"] = True
        return mutated


class FaultInjector:
    """Manager to inject and orchestrate faults into vehicle simulation and tests."""

    @staticmethod
    def inject_lost_message(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Drop message signal flag."""
        return MessageLostFault().apply(inputs)

    @staticmethod
    def inject_delayed_message(inputs: Dict[str, Any], delay_ms: float = 300.0) -> Dict[str, Any]:
        """Inject message latency."""
        return MessageDelayedFault(delay_ms=delay_ms).apply(inputs)

    @staticmethod
    def inject_stuck_sensor(inputs: Dict[str, Any], var: str = "speed", value: Any = 0.0) -> Dict[str, Any]:
        """Freeze sensor output to stuck value."""
        return SensorStuckFault(stuck_var=var, stuck_value=value).apply(inputs)
