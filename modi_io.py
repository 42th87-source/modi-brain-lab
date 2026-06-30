"""Input abstraction for MODI sensors and local keyboard fallback."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InputSnapshot:
    button_pressed: bool = False
    gyro_pitch: float | None = None
    gyro_roll: float | None = None
    gyro_angular_velocity: float | None = None


class ModiInput:
    """Placeholder for pymodi-plus backed input.

    The first runnable prototype uses keyboard input in `task1_reaction.py`.
    Later, this class can own the real MODI modules and expose the same
    `read()` shape.
    """

    def read(self) -> InputSnapshot:
        return InputSnapshot()
