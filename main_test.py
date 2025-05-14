"""
main_test.py
18. November 2024

Converts three camera angles to one 3-dimensional point

Author:
Nilusink
"""
import matplotlib.pyplot as plt
from icecream import ic
import numpy as np
import math as m

from core.tools import CamAngle3, debugger, DebugLevel
from core.maths import solve, CameraResult
from core.tools import Vec3

ic.prefix = lambda *_: ">"
debugger.init("", True, False, debug_level=DebugLevel.log)


# s1 = CameraResult(
#     Vec3.from_polar(.3, 0, 10),
#     -Vec3.from_polar(0, -.1, 10)
# )
# s2 = CameraResult(
#     Vec3.from_polar((2*m.pi) / 3 + .005, 0, 10),
#     -Vec3.from_polar((2*m.pi) / 3.1, -.1, 10)
# )
# s3 = CameraResult(
#     Vec3.from_polar((4*m.pi) / 3 -.04, 0, 10),
#     -Vec3.from_polar((4*m.pi) / 3 + .05, -.1, 10)
# )

a1 = CamAngle3(cam_id=0, position=(10.0, 0.0, 0.0), direction=(-0.9761160908245395, -0.02929227093332195, 0.21526574297130507))
a2 = CamAngle3(cam_id=1, position=(-4.999999999999998, 8.660254037844387, 0.0), direction=(0.5689841315221609, -0.790963239543564, 0.22502046966159106))
a3 = CamAngle3(cam_id=2, position=(-5.000000000000004, -8.660254037844386, 0.0), direction=(0.424894616238502, 0.8498929878596323, 0.3116832916255907))

angles = [CameraResult(
    Vec3.from_cartesian(*a.position),
    Vec3.from_cartesian(*a.direction) * 3
) for a in [a1, a2, a3]]

target, accuracy = solve(*angles)
target = target.xyz

print(target, accuracy)

# matpotlib debugging
# Plotting in 3D
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

lines: list[tuple[np.array, np.array]] = []
for result in angles:
    lines.append((
        np.array(result.origin.xyz),
        np.array(result.direction.xyz),
    ))

# Plot the lines
t_vals = np.linspace(-5, 5, 100)
for point, direction, color, label in zip(
    [line[0] for line in lines],
    [line[1] for line in lines],
    ['red', 'blue', 'green'],
    ['Line 1', 'Line 2', 'Line 3']
):
    line_points = np.array([point + t * direction for t in t_vals])
    ax.plot(line_points[:, 0], line_points[:, 1], line_points[:, 2], color=color, label=label)

# Plot the closest point
ax.scatter(*target, color='black', s=100, label="Closest Point")

# Labels and legend
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_title("Closest Point to Three Lines")
ax.legend()

plt.show()