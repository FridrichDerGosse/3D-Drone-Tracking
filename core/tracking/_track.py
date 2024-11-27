"""
_track.py
19. November 2024

A signular track

Author:
Nilusink
"""
from time import perf_counter

from ..tools import Vec3, debugger


class Track:
    def __init__(self, id: int, initial_position: Vec3) -> None:
        self._id = id
        self._position_history: list[tuple[float, Vec3]] = [
            (perf_counter(), initial_position)
        ]

        self._type = 0  # -1: degraded, 0: new, 1: valid

        debugger.info(f"new track with id {self._id} at {initial_position.xyz}")

    @property
    def id(self) -> int:
        return self._id

    @property
    def current_position(self) -> Vec3:
        return self._position_history[-1][1]

    @property
    def type(self) -> int:
        return self._type

    def update_position(self, position: Vec3) -> None:
        """
        update the tracks position
        """
        debugger.trace(f"track {self.id} was updated by {position.xyz}")
        self._position_history.append((perf_counter(), position))

        self._type = 1
