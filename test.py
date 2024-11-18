import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import math as m

from core import CameraResult, Vec3

s1 = CameraResult(
    Vec3.from_polar(.3, 0, 10),
    -Vec3.from_polar(0, -.1, 10)
)
s2 = CameraResult(
    Vec3.from_polar((2*m.pi) / 3 + .005, 0, 10),
    -Vec3.from_polar((2*m.pi) / 2, -.9, 10)
)
s3 = CameraResult(
    Vec3.from_polar((4*m.pi) / 3 -.04, 0, 10),
    -Vec3.from_polar((4*m.pi) / 3 + .05, -.1, 10)
)
# Define the distance from a point to a line
def distance_to_line(point, line_point, line_direction):
    # Vector from line_point to point
    vec_to_point = point - line_point
    # Projection of vec_to_point onto the line direction
    projection_length = np.dot(vec_to_point, line_direction) / np.linalg.norm(line_direction)**2
    projection = projection_length * line_direction
    # Distance vector
    distance_vector = vec_to_point - projection
    return np.dot(distance_vector, distance_vector)  # Squared distance

# Objective function: minimize total squared distance to all lines
def objective(point, lines):
    return sum(distance_to_line(point, line[0], line[1]) for line in lines)

# Define the lines with points and directions
# line_1 = [np.array([1, 0, 0]), np.array([1, 1, 1])]
# line_2 = [np.array([0, 1, 0]), np.array([-1, 1, 1])]
# line_3 = [np.array([0, 0, 1]), np.array([1, -1, 1])]
#
# lines = [line_1, line_2, line_3]

lines: list[tuple[np.array, np.array]] = []
for result in [s1, s2, s3]:
    lines.append((
        np.array(result.origin.xyz),
        np.array(result.direction.xyz),
    ))
# Perform the optimization
result = minimize(objective, x0=np.array([0.0, 0.0, 0.0]), args=(lines,), method='BFGS')

# Check optimization success
if result.success:
    closest_point = result.x
    print("Closest point:", closest_point)
else:
    raise ValueError("Optimization failed: " + result.message)

# Plotting in 3D
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

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
ax.scatter(*closest_point, color='black', s=100, label="Closest Point")

# Labels and legend
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_title("Closest Point to Multiple Lines")
ax.legend()

plt.show()
