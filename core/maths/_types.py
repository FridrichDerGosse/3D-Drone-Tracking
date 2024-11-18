"""
_types.py
18. November 2024

Types specific to the angle calculation

Author:
Nilusink
"""
from dataclasses import dataclass

from ..tools import Vec3


@dataclass
class CameraResult:
    origin: Vec3
    direction: Vec3
