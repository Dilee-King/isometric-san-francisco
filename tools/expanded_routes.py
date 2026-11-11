"""Source road loops and shoreline-cleared approaches to the inner Bay terminals."""

import heapq
import math

import numpy as np
from shapely import intersects_xy, prepare
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from atlas_geometry import camera_point
from corridor_inputs import local_xy
from expanded_render import LEGACY_FRAMES, block_frame, crossing_road, geometry
from golden_gate_routes import west_cars

FERRY_BUILDING = (-122.392021, 37.796435)
FERRIES = (
    (7, "oakland-ferry", (-122.2801910, 37.7945115), FERRY_BUILDING),
    (7, "alameda-main-ferry", (-122.2944960, 37.7911224), (-122.391235, 37.795304)),
    (7, "alameda-seaplane-ferry", (-122.2992270, 37.7771558), FERRY_BUILDING),
    (8, "sausalito-ferry", (-122.47675, 37.85662), FERRY_BUILDING),
)


def channel(obstacles, start, end, radius):
    """Plan through water cells and then verify every simplified segment."""
    safe = obstacles.buffer(radius + 2.5)
    prepare(safe)
    a, b = np.asarray(local_xy(*start)), np.asarray(local_xy(*end))
    step = 26.
    lo = np.minimum(a, b) - 1000
    hi = np.maximum(a, b) + 1000
    x = np.arange(lo[0], hi[0] + step, step)
    y = np.arange(lo[1], hi[1] + step, step)
    water = ~intersects_xy(safe, x[None, :], y[:, None])

    def nearest(point):
        delta = (x[None, :] - point[0]) ** 2 + (y[:, None] - point[1]) ** 2
        delta[~water] = np.inf
        index = tuple(int(value) for value in np.unravel_index(np.argmin(delta), delta.shape))
        if delta[index] > 170 ** 2:
            raise ValueError(f"No hull-clear berth near {point.tolist()}")
        return index

    def coordinate(index):
        return x[index[1]], y[index[0]]

    origin, goal = nearest(a), nearest(b)
    costs, before = {origin: 0.}, {}
    queue = [(math.dist(origin, goal), 0., origin)]
    offsets = [(i, j, math.hypot(i, j)) for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j]
    while queue:
        _, distance, current = heapq.heappop(queue)
        if current == goal:
            break
        if distance != costs[current]:
            continue
        for dy, dx, travel in offsets:
            row, column = current[0] + dy, current[1] + dx
            if not (0 <= row < len(y) and 0 <= column < len(x) and water[row, column]):
                continue
            if dy and dx and not (water[row, current[1]] and water[current[0], column]):
                continue
            target = (row, column)
            total = distance + travel
            if total < costs.get(target, math.inf):
                costs[target], before[target] = total, current
                heapq.heappush(queue, (total + math.dist(target, goal), total, target))
    if goal not in before:
        raise ValueError(f"No continuous water approach from {start} to {end}")
    points = [goal]
    while points[-1] != origin:
        points.append(before[points[-1]])
    points = [coordinate(index) for index in reversed(points)]
    # Smooth across the grid while retaining the exact buffered water clearance.
    simplified = [points[0]]
    at = 0
    while at < len(points) - 1:
        for candidate in range(len(points) - 1, at, -1):
            if not safe.intersects(LineString((points[at], points[candidate]))):
                break
        else:
            raise ValueError("A grid path crossed the buffered shoreline")
        simplified.append(points[candidate])
        at = candidate
    clearance = LineString(simplified).distance(obstacles)
    if clearance < radius:
        raise ValueError(f"Vessel clearance {clearance:.2f} is below radius {radius:.2f}")
    return [[round(e, 2), round(n, 2), .7] for e, n in simplified], clearance


def vessels(data, bridge):
    land = geometry(data["land"])
    obstacles = unary_union([land, *(Point(e, n).buffer(radius) for e, n, radius in bridge.supports)])
    routes = {6: [], 7: [], 8: []}
    audit = {}
    for version, identity, berth, terminal in FERRIES:
        path, clearance = channel(obstacles, berth, terminal, math.hypot(15.5, 4.5))
        audit[identity] = {"minClearanceMetres": round(clearance, 3), "approachPoints": len(path),
                           "routeMetres": round(LineString([point[:2] for point in path]).length)}
        for direction, points in enumerate((path, path[::-1])):
            routes[version].append({"id": f"{identity}-{direction}", "kind": "ferry",
                                    "points": points + points[-2::-1], "speed": 11.5,
                                    "phase": 11.6 + direction * 8, "dwell": 12,
                                    "color": "#ece6d3"})
    path, clearance = channel(obstacles, (-122.3300, 37.8035), (-122.3650, 37.7770), math.hypot(32.5, 7.5))
    audit["oakland-cargo"] = {"minClearanceMetres": round(clearance, 3), "approachPoints": len(path),
                              "routeMetres": round(LineString([point[:2] for point in path]).length)}
    routes[7].append({"id": "oakland-cargo", "kind": "cargo", "points": path + path[-2::-1],
                      "speed": 7.3, "phase": 8.2, "dwell": 8, "color": "#d7c7af"})
    return routes, audit


def build_routes(data, bridge, active):
    boats, audit = vessels(data, bridge)
    source = {**data, "roads": [road for road in data["roads"] if not crossing_road(road)]}
    routes = {}
    for version in (6, 7, 8):
        frames = [block_frame(*map(int, key.split("_"))) for key, (release, name) in active.items() if release == version]
        cars, loops = west_cars(source, frames=frames, prefix=f"district-v{version}")
        retained = []
        for car in cars:
            sample = car["points"][::max(1, len(car["points"]) // 5)]
            existing = sum(any(frame.contains(*camera_point(point)[:2]) for frame in LEGACY_FRAMES) for point in sample)
            if existing < len(sample) * .65:
                retained.append(car)
        routes[version] = retained + boats[version]
        audit[f"v{version}"] = {"districtCars": len(retained), "loopBlocks": sum(value > 0 for value in loops.values())}
    routes[6].extend(bridge.routes())
    routes[6].append({"id": "citywide-overflight", "kind": "plane",
                      "points": [[*map(float, local_xy(lon, lat)), z]
                                 for lon, lat, z in ((-122.518, 37.755, 540), (-122.367, 37.786, 650))],
                      "speed": 70, "phase": 7.8, "color": "#e6e9e0"})
    return routes, audit
