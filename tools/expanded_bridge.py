"""The Bay Bridge carriageways, shared by painted structures and moving traffic."""

from collections import defaultdict
from dataclasses import dataclass
import heapq
import math

import numpy as np
from shapely.geometry import LineString

from atlas_geometry import camera_point
from corridor_inputs import local_xy

UPPER = ("westbound", (-122.3042158, 37.8256152), (-122.3907307, 37.7862034))
LOWER = ("eastbound", (-122.3903709, 37.7864781), (-122.3051106, 37.8250656))
HEIGHT_PROFILE = (
    (-122.3909, 37.7860, 42), (-122.3850, 37.7915, 55),
    (-122.3780, 37.7980, 57), (-122.3710, 37.8047, 55),
    (-122.3664, 37.8090, 54), (-122.3634, 37.8118, 59),
    (-122.3577, 37.8157, 70), (-122.3514, 37.8185, 62),
    (-122.3390, 37.8208, 37), (-122.3277, 37.8222, 12),
    (-122.3160, 37.8240, 6), (-122.3040, 37.8257, 5),
)


def roadway(roads, start, end):
    graph = defaultdict(list)
    for road in roads:
        if road["kind"] != "motorway" or "I 80" not in road["ref"].split(";"):
            continue
        points = [tuple(point[:2]) for point in road["points"]]
        for a, b in zip(points, points[1:]):
            distance = math.dist(a, b)
            if distance < .05:
                continue
            if road["oneway"] != "-1":
                graph[a].append((b, distance, road["tunnel"], road["bridge"]))
            if road["oneway"] not in ("yes", "true", "1"):
                graph[b].append((a, distance, road["tunnel"], road["bridge"]))
    nodes = set(graph) | {edge[0] for edges in graph.values() for edge in edges}
    if not nodes:
        raise ValueError("The source contains no I-80 carriageways")
    a, b = (min(nodes, key=lambda node: math.dist(node, local_xy(*location))) for location in (start, end))
    queue, cost, previous = [(0., a)], {a: 0.}, {}
    while queue:
        distance, node = heapq.heappop(queue)
        if node == b:
            break
        if distance != cost[node]:
            continue
        for other, length, tunnel, bridge in graph[node]:
            total = distance + length
            if total < cost.get(other, math.inf):
                cost[other] = total
                previous[other] = node, tunnel, bridge
                heapq.heappush(queue, (total, other))
    if b not in previous or not 7700 < cost[b] < 11200:
        raise ValueError(f"Incomplete I-80 crossing: {start} to {end}, {cost.get(b)} m")
    route = [b]
    flags = []
    while route[-1] != a:
        node, tunnel, bridge = previous[route[-1]]
        flags.append((tunnel, bridge))
        route.append(node)
    return route[::-1], flags[::-1]


def ribbon(a, b, across_a, across_b, width, lift=0):
    delta = np.asarray(b[:2]) - a[:2]
    normal = np.array([-delta[1], delta[0]]) / np.linalg.norm(delta)
    aa, bb = np.asarray(a[:2]), np.asarray(b[:2])
    return [[*(aa + normal * (across_a - width / 2)), a[2] + lift],
            [*(bb + normal * (across_b - width / 2)), b[2] + lift],
            [*(bb + normal * (across_b + width / 2)), b[2] + lift],
            [*(aa + normal * (across_a + width / 2)), a[2] + lift]]


def lateral(a, b, offset):
    delta = np.asarray(b[:2]) - a[:2]
    shift = np.array([-delta[1], delta[0]]) * offset / np.linalg.norm(delta)
    return np.array([shift[0], shift[1], 0.])


@dataclass
class Carriageway:
    id: str
    points: np.ndarray
    hidden: tuple
    span: tuple

    def lane(self, across):
        shifts = [lateral(a, b, across) for a, b in zip(self.points, self.points[1:])]
        return (self.points + np.asarray([*shifts, shifts[-1]]) + [0, 0, .18]).round(3).tolist()


class BayBridge:
    def __init__(self, roads):
        self.faces, self.lamps, self.supports = [], [], []
        self.ways = []
        knots = [(float(local_xy(lon, lat)[0]), height) for lon, lat, height in HEIGHT_PROFILE]
        self.tunnel_east = float(local_xy(-122.3650, 37.8102)[0])
        self.tunnel_west = float(local_xy(-122.36635, 37.8090)[0])
        for identity, start, end in (UPPER, LOWER):
            nodes, flags = roadway(roads, start, end)
            points, hidden, span = [], [], []
            for a, b, (tunnel, on_bridge) in zip(nodes, nodes[1:], flags):
                width = math.dist(a, b)
                count = max(1, math.ceil(width / 20))
                for step in range(count):
                    x, n = np.asarray(a) + (np.asarray(b) - a) * step / count
                    points.append([x, n, self.height(x, identity, knots)])
                    span.append(on_bridge)
                    if tunnel and self.tunnel_west - 15 < x < self.tunnel_east + 15:
                        hidden.append(len(points) - 1)
            points.append([*nodes[-1], self.height(nodes[-1][0], identity, knots)])
            if not hidden:
                raise ValueError(f"Missing Yerba Buena tunnel on {identity}")
            way = Carriageway(identity, np.asarray(points), tuple(hidden), tuple(span))
            self.ways.append(way)
            self.paint_deck(way)
        self.paint_towers()

    def height(self, easting, direction, knots):
        xs, heights = zip(*knots)
        height = float(np.interp(easting, xs, heights))
        if direction == "westbound":
            height += 9.5 * np.clip((self.tunnel_east - easting) / 170, 0, 1)
        return height

    def add(self, points, color, road=False):
        coords = [list(point) for point in points]
        positions = [camera_point(point) for point in coords]
        x, y = zip(*(point[:2] for point in positions))
        self.faces.append((coords, color, road, (min(x), min(y), max(x), max(y))))

    def prism(self, center, width, length, base, top, color, direction=(1, 0)):
        e, n = center[:2]
        axis = np.asarray(direction, dtype=float)
        axis /= np.linalg.norm(axis)
        side = np.array([-axis[1], axis[0]])
        corners = [np.array([e, n]) + axis * a * length / 2 + side * b * width / 2
                   for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for index, (a, b) in enumerate(zip(corners, corners[1:] + corners[:1])):
            tone = (.78, .9, .97, .85)[index]
            self.add([[*a, base], [*b, base], [*b, top], [*a, top]], tuple(round(c * tone) for c in color))
        self.add([[*corner, top] for corner in corners], color)

    def cable(self, a, b, width, color):
        x, n, z = a
        e, t, h = b
        self.add([(x - width, n, z), (e - width, t, h), (e + width, t, h), (x + width, n, z)], color)
        self.add([(x, n - width, z), (e, t - width, h), (e, t + width, h), (x, n + width, z)], color)

    def paint_deck(self, way):
        hidden = set(way.hidden)
        for index, (a, b) in enumerate(zip(way.points, way.points[1:])):
            if index in hidden:
                continue
            half_width = 12.1
            self.add(ribbon(a, b, 0, 0, half_width * 2), (171, 174, 170), True)
            self.add(ribbon(a, b, 0, 0, 20.2, .07), (89, 101, 110), True)
            for side in (-1, 1):
                edge = side * half_width
                delta = lateral(a, b, edge)
                p, q = a + delta, b + delta
                if way.span[index]:
                    depth = 6.3 if a[0] < self.tunnel_west else 4.4
                    self.add([p - [0, 0, depth], q - [0, 0, depth], q + [0, 0, .4], p + [0, 0, .4]], (119, 133, 140))
                    self.cable(p + [0, 0, 1.1], q + [0, 0, 1.1], .34, (205, 213, 208))
                    if a[0] < self.tunnel_west:
                        self.cable(p - [0, 0, depth], q + [0, 0, .4], .43, (150, 165, 170))
            for lane in (-6, -3, 0, 3, 6):
                middle = a + (b - a) * .53
                self.add(ribbon(a, middle, lane, lane, .19, .16), (226, 222, 199), True)
            if index % 3 == 1:
                self.lamps.append((a + lateral(a, b, 11.1)).tolist())
        for index in (way.hidden[0], way.hidden[-1] + 1):
            a = way.points[index]
            b = way.points[min(index + 1, len(way.points) - 1)]
            shift = lateral(a, b, 14.5)
            p, q = a - shift, a + shift
            self.add([p, q, q + [0, 0, 12.5], p + [0, 0, 12.5]], (172, 164, 144))
            p, q = a - shift * .79, a + shift * .79
            self.add([p + [0, 0, .2], q + [0, 0, .2], q + [0, 0, 8.4], p + [0, 0, 8.4]], (36, 43, 49))

    def paint_towers(self):
        upper = self.ways[0]
        west = upper.points[upper.points[:, 0] < self.tunnel_west][::-1]
        direction = west[-1, :2] - west[0, :2]
        knots = (0., .144, .372, .50, .623, .851, 1.)
        heights = (46, 156, 156, 70, 156, 156, 64)
        steel = (183, 194, 196)
        for fraction, height in zip(knots[1:-1], heights[1:-1]):
            base = west[0] + (west[-1] - west[0]) * fraction
            self.supports.append((float(base[0]), float(base[1]), 22.))
            self.prism(base, 35, 24, 0, 18, (157, 151, 137), direction)
            if height < 100:
                self.prism(base, 30, 20, 14, height, (172, 166, 150), direction)
                continue
            shift = lateral(west[0], west[-1], 13.3)
            for p in (base - shift, base + shift):
                self.prism(p, 6.3, 8.5, 15, height, steel, direction)
            for z in (83, 114, 145):
                self.prism(base, 27, 6.3, z, z + 3.6, steel, direction)
            self.cable(base - shift + [0, 0, 91 - base[2]], base + shift + [0, 0, 133 - base[2]], 1.6, steel)
            self.cable(base + shift + [0, 0, 91 - base[2]], base - shift + [0, 0, 133 - base[2]], 1.6, steel)
        for left, right, high_a, high_b in zip(knots, knots[1:], heights, heights[1:]):
            for side in (-1, 1):
                across = lateral(west[0], west[-1], 13.1 * side)
                last = None
                for t in np.linspace(0, 1, max(7, int((right - left) * 180))):
                    f = left + (right - left) * t
                    center = west[0] + (west[-1] - west[0]) * f + across
                    sag = 72 if high_a > 100 and high_b > 100 else 24
                    cable = [center[0], center[1], max(center[2] + 1, high_a * (1 - t) + high_b * t - sag * 4 * t * (1 - t))]
                    if last is not None:
                        self.cable(last, cable, .48, steel)
                        self.cable(center, cable, .24, (152, 164, 169))
                    last = cable
        # The east span has one pale self-anchored tower and parallel roadways.
        tower_e, tower_n = map(float, local_xy(-122.35843, 37.81534))
        tower = np.array([tower_e, tower_n, 70.])
        self.supports.append((tower_e, tower_n, 30.))
        self.prism(tower, 21, 20, .1, 16, (164, 168, 161))
        for e in (-4.3, 4.3):
            for n in (-4.5, 4.5):
                self.prism(tower + [e, n, 0], 5.0, 5.9, 15, 160, (218, 223, 219))
        for z in (76, 117, 151):
            self.prism(tower, 15.0, 15.0, z, z + 3.2, (214, 219, 215))
        for way in self.ways:
            east = way.points[(way.points[:, 0] > tower_e - 260) & (way.points[:, 0] < tower_e + 390)]
            east = east[np.argsort(east[:, 0])]
            if len(east) < 5:
                continue
            previous = None
            for index, p in enumerate(east):
                t = abs(p[0] - tower_e) / (390 if p[0] > tower_e else 260)
                cable = [p[0], p[1], max(p[2] + 1.6, 159 - min(1, t) * 110)]
                if previous is not None:
                    self.cable(previous, cable, .47, (212, 220, 221))
                if index % 2 == 0:
                    self.cable(p, cable, .27, (185, 199, 203))
                previous = cable
        eastbound = self.ways[1]
        for index in range(4, len(eastbound.points) - 1, 7):
            p = eastbound.points[index]
            if p[0] < tower_e + 430 or not eastbound.span[index]:
                continue
            self.prism(p, 10.4, 11, 0, max(4.2, p[2] - 4), (167, 171, 164))
            self.supports.append((float(p[0]), float(p[1]), 13.))

    def draw(self, raster):
        frame = raster.frame
        for points, color, road, (x0, y0, x1, y1) in self.faces:
            if x1 >= frame.x and x0 < frame.right and y1 >= frame.y and y0 < frame.bottom:
                raster.face(points, color, building=not road, deck=road)

    def coverage(self):
        return [LineString([camera_point(point)[:2] for point in way.points]).buffer(255) for way in self.ways]

    def routes(self):
        routes = []
        for way in self.ways:
            length = float(np.linalg.norm(np.diff(way.points, axis=0), axis=1).sum())
            for lane, across in enumerate((-7.2, -3.6, 0, 3.6, 7.2)):
                points = way.lane(across)
                for number in range(11):
                    speed = 22.0 + lane * .4
                    routes.append({"id": f"bay-bridge-{way.id}-{lane}-{number}", "kind": "car",
                                   "points": points, "hiddenSegments": way.hidden, "speed": speed, "dwell": 0,
                                   "phase": length / speed * ((number + lane * .16) / 11),
                                   "color": ("#deddd0", "#c2b6a8", "#5f8592", "#c46a45", "#e7e5df")[number % 5]})
        return routes
