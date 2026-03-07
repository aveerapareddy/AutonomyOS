"""Typed robot movement actions."""

from enum import Enum


class RobotAction(str, Enum):
    """Discrete movement primitives for the simulator robot."""

    FORWARD = "forward"
    BACKWARD = "backward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    STOP = "stop"
