"""
_tracking_master.py
19. November 2024

Administers all tracks

Author:
Nilusink
"""
import typing as tp

from ..maths import CameraResult, solve
from ._track import Track
from ..tools import Vec3


class TrackingMaster:
    def __init__(self) -> None:
        self._tracks: list[Track] = []

    def update_tracks(self, angles: tp.Iterable[CameraResult]) -> None:
        """
        gets camera data and converts them to tracks
        """
        # calculate 3d Position
        position = solve(*angles)

        # match the position to a track
        self.match_pos_track(position)

    def match_pos_track(self, pos: Vec3) -> None:
        """
        matches a position to an existing one
        """
        if len(self._tracks) == 0:
            self._tracks.append(Track())

        self._tracks[0].update_position(pos)
