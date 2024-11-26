"""
_tracking_master.py
19. November 2024

Administers all tracks

Author:
Nilusink
"""
import typing as tp

from ..comms import TResData, SInfData, DataServer, TRes3Data
from ..maths import CameraResult, solve
from ..tools import debugger
from ._track import Track
from ..tools import Vec3


class TrackingMaster:
    def __init__(self, data_server: DataServer) -> None:
        self._tracks: list[Track] = []
        self._cams: dict[int, SInfData] = {}
        self._ds = data_server

    def update_cams(self, cam_update: SInfData) -> None:
        """
        update camera locations
        """
        debugger.log(f"Cam update for cam {cam_update.id}")
        self._cams[cam_update.id] = cam_update

    def update_tracks(self, track_result: TResData) -> None:
        """
        gets camera data and converts them to tracks
        """
        # tid = tp.Iterable[CameraResult]
        # add station positions to camera angles
        debugger.trace(f"matching cam angles, n: {len(track_result.cam_angles)}")
        debugger.trace(f"currently loaded cams: {self._cams}")

        angles = []
        for cam_angle in track_result.cam_angles:

            # check if camera was found
            if cam_angle.cam_id in self._cams:
                origin = Vec3.from_cartesian(*self._cams[cam_angle.cam_id].position)
                cam_direction = Vec3.from_cartesian(
                    *self._cams[cam_angle.cam_id].direction
                ).normalize()

                # convert angles to 3d Vector
                direction = Vec3.from_polar(
                    cam_direction.angle_xy + cam_angle.direction[0],
                    cam_direction.angle_xz + cam_angle.direction[1],
                    1
                )

                angles.append(CameraResult(
                    origin,
                    direction
                ))

        if len(angles) < 2:
            debugger.warning("fewer than two valid angles have been found")
            return

        # calculate 3d Position
        position = solve(*angles)

        debugger.log(
            f"calculated position for track {track_result.track_id}: {position.xyz}"
        )

        # match the position to a track
        self.match_pos_track(position, track_result.track_id)

        # update clients
        debugger.trace(f"tracker: updating clients")
        self._ds.update_clients(TRes3Data(
            track_id=track_result.track_id,
            cam_angles=track_result.cam_angles,
            position=position.xyz
        ))

    def match_pos_track(self, pos: Vec3, tid: int) -> None:
        """
        matches a position to an existing one
        """
        if len(self._tracks) == 0:
            self._tracks.append(Track(tid, pos))
            return

        self._tracks[0].update_position(pos)
