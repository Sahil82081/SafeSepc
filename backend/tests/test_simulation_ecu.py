"""Pytest suite for Simulation & Virtual ECU (CAN Bus, Sensors, Actuators, and Version Swapping).

Requirements tested:
1. VirtualCanBus transmission and reception using python-can virtual interface.
2. SpeedSensor and BrakePedalSensor frame encoding and broadcasting.
3. DoorLockActuator and BrakeActuator response.
4. Dynamic ECU version loading from ecu/versions/:
   - v1.py: correct logic (speed > 20 -> LOCKED)
   - v1_buggy_threshold.py: bug (threshold 80 -> UNLOCKED at speed 50)
   - v1_buggy_timeout.py: bug (ignores lost speed message -> UNLOCKED at speed 50)
5. Core Done Criteria:
   - speed=50 gives LOCKED on v1
   - speed=50 gives UNLOCKED on v1_buggy_threshold
   - speed=50 gives UNLOCKED on v1_buggy_timeout
"""

import pytest
import can

from backend.app.simulation import (
    VirtualCanBus,
    SpeedSensor,
    BrakePedalSensor,
    DoorLockActuator,
    BrakeActuator,
    encode_speed_frame,
    decode_speed_frame,
)
from backend.app.ecu import (
    VirtualECU,
    DoorController,
    BrakeController,
)


def test_core_speed_50_version_criterion():
    """Core Done Criteria:

    speed=50 gives LOCKED on v1 and UNLOCKED on both buggy versions.
    """
    ecu = VirtualECU(initial_version="v1")

    # 1. Version v1: speed=50 must give LOCKED (> 20 threshold)
    ecu.load_version("v1")
    state_v1 = ecu.handle_speed(50.0)
    assert state_v1 == "LOCKED", f"v1 expected LOCKED at speed=50, got {state_v1}"
    assert ecu.door_actuator.get_state() == "LOCKED"

    # 2. Version v1_buggy_threshold: speed=50 must give UNLOCKED (threshold is 80)
    ecu.load_version("v1_buggy_threshold")
    state_buggy_thr = ecu.handle_speed(50.0)
    assert state_buggy_thr == "UNLOCKED", f"v1_buggy_threshold expected UNLOCKED at speed=50, got {state_buggy_thr}"
    assert ecu.door_actuator.get_state() == "UNLOCKED"

    # 3. Version v1_buggy_timeout: speed=50 must give UNLOCKED (ignores lost speed message fail-safe)
    ecu.load_version("v1_buggy_timeout")
    state_buggy_to = ecu.handle_speed(50.0)
    assert state_buggy_to == "UNLOCKED", f"v1_buggy_timeout expected UNLOCKED at speed=50, got {state_buggy_to}"
    assert ecu.door_actuator.get_state() == "UNLOCKED"


def test_can_bus_message_transfer():
    """Test VirtualCanBus message encoding, transmission, and reception."""
    with VirtualCanBus(channel="test_sim_can_channel") as bus:
        bus.flush()

        # Send speed frame
        speed_sensor = SpeedSensor(initial_speed=65.5, is_valid=True)
        assert speed_sensor.broadcast(bus) is True

        # Receive speed frame
        rx_msg = bus.recv(timeout=1.0)
        assert rx_msg is not None
        assert rx_msg.arbitration_id == 0x1F0

        decoded_speed, is_valid = decode_speed_frame(rx_msg)
        assert abs(decoded_speed - 65.5) < 0.1
        assert is_valid is True


def test_virtual_ecu_can_integration():
    """Test VirtualECU reading CAN frames from VirtualCanBus and driving actuators."""
    with VirtualCanBus(channel="test_ecu_can_channel") as bus:
        bus.flush()
        ecu = VirtualECU(bus=bus, initial_version="v1")
        sensor = SpeedSensor(bus=bus)

        # 1. Drive at 50 km/h on v1 -> Door must lock
        sensor.set_speed(50.0, is_valid=True)
        sensor.broadcast(bus)
        step_res = ecu.step(timeout=0.5)

        assert step_res is not None
        assert step_res["type"] == "SPEED"
        assert ecu.door_actuator.is_locked is True

        # 2. Swap to v1_buggy_threshold at runtime -> Send 50 km/h -> Door unlocks (50 < 80)
        ecu.load_version("v1_buggy_threshold")
        sensor.set_speed(50.0, is_valid=True)
        sensor.broadcast(bus)
        step_res_thr = ecu.step(timeout=0.5)

        assert step_res_thr is not None
        assert ecu.door_actuator.is_locked is False
        assert ecu.door_actuator.get_state() == "UNLOCKED"

        # 3. Swap to v1_buggy_timeout at runtime -> Send speed with lost/timeout status -> Door remains UNLOCKED
        ecu.load_version("v1_buggy_timeout")
        sensor.set_speed(50.0, is_valid=False)  # Simulates lost speed signal / timeout
        sensor.broadcast(bus)
        step_res_to = ecu.step(timeout=0.5)

        assert step_res_to is not None
        assert ecu.door_actuator.is_locked is False
        assert ecu.door_actuator.get_state() == "UNLOCKED"

        # But on v1, a lost speed message at 50 km/h MUST fail-safe lock the door!
        ecu.load_version("v1")
        sensor.broadcast(bus)
        ecu.step(timeout=0.5)
        assert ecu.door_actuator.is_locked is True


def test_brake_controller_and_actuator():
    """Test BrakePedalSensor, BrakeController, and BrakeActuator line pressure."""
    with VirtualCanBus(channel="test_brake_can_channel") as bus:
        bus.flush()
        ecu = VirtualECU(bus=bus)
        brake_sensor = BrakePedalSensor()

        # 50% brake pedal depression
        brake_sensor.set_brake(50.0, switch_active=True)
        brake_sensor.broadcast(bus)

        step_res = ecu.step(timeout=0.5)
        assert step_res is not None
        assert step_res["type"] == "BRAKE"
        assert step_res["pressure_bar"] > 0
        assert abs(step_res["pressure_bar"] - 60.0) < 1.0  # 50% of 120 bar
        assert ecu.brake_actuator.is_engaged is True
        assert abs(ecu.brake_actuator.get_pressure() - 60.0) < 1.0

        # Release brake
        brake_sensor.set_brake(0.0, switch_active=False)
        brake_sensor.broadcast(bus)
        ecu.step(timeout=0.5)
        assert ecu.brake_actuator.get_pressure() == 0.0
        assert ecu.brake_actuator.is_engaged is False
