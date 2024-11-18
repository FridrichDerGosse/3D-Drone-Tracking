"""
solve.py
18. November 2024

the actual calculation

Author:
Nilusink
"""
from scipy.optimize import minimize
import numpy as np

from ._types import CameraResult
from ..tools import Vec3


def solve(*results: CameraResult) -> Vec3:
    """
    takes all camera results and calculates the closest point in a
    3-dimensional space
    """
    # convert values to numpy vector format
    lines: list[tuple[np.array, np.array]] = []
    for result in results:
        lines.append((
            np.array(result.origin.xyz),
            np.array(result.direction.xyz),
        ))

    result = minimize(objective, x0=np.array([0.0, 0.0, 0.0]), args=(lines,), method='BFGS')

    if result.success:
        return result.x

    else:
        raise ValueError("Optimization failed: " + result.message)


# helper functions
def distance_to_line(point, line_point, line_direction):
    """
    calculate the distance of one point to one line
    """
    # Vector from line_point to point
    vec_to_point = point - line_point

    # Projection of vec_to_point onto the line direction
    projection_length = np.dot(vec_to_point, line_direction) / np.linalg.norm(line_direction)**2
    projection = projection_length * line_direction

    # Distance vector
    distance_vector = vec_to_point - projection
    return np.dot(distance_vector, distance_vector)  # Squared distance


# Objective function: minimize total squared distance to all lines
def objective(point: np.array, lines: list[tuple[np.array, np.array]]) -> float:
    """
    calculate the sum of the distances to each line
    """
    return sum(distance_to_line(point, line[0], line[1]) for line in lines)