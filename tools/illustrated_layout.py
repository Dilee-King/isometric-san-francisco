"""Plan continuous artwork coverage on the original map grid."""

import json
import math

from shapely.affinity import affine_transform
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from atlas_geometry import CE, SCALE, SE, camera_point
from corridor_inputs import ROOT
from expanded_geometry import WORLD, places
from expanded_source import load
from illustrated_guides import APPROVED, reference_scene

ART = ROOT / "assets/illustrated-expansion"
LAYOUT = ART / "layout.json"
PILOTS = {
    "civic-center-link": (6, [-5900, -1160, 3072, 2048], "Civic Center from Union Square"),
    "fort-baker-link": (8, [-7050, -10060, 3072, 2048], "Golden Gate north landing and Fort Baker"),
}
DETAIL_FOCUS = {"bay-bridge-east": (7228, 212), "middle-harbor": (10147, 3478),
                "sausalito-marinas": (-4412, -13018)}
TERMINAL_PLATES = {"alameda-main": (12570, 6540), "alameda-seaplane": (10242, 7705)}


def map_geometry(rings):
    ground = unary_union([Polygon(ring[0], ring[1:]).buffer(0) for ring in rings])
    return affine_transform(ground, [.8 * SCALE, .6 * SCALE, .6 * SCALE * SE, -.8 * SCALE * SE,
                                     0, -2.6 * CE * SCALE])


def bridge_area(scene):
    routes = {}
    for route in scene["routes"]:
        if route["id"].startswith("bay-bridge-"):
            direction = route["id"].rsplit("-", 2)[0]
            routes.setdefault(direction, route)
    lines = []
    for route in routes.values():
        points = [camera_point(point)[:2] for point in route["points"]]
        lines.append(LineString(points))
    return unary_union(lines).buffer(380)


def coverage(data, scene):
    regions = {int(stage): map_geometry(rings) for stage, rings in data["coverage"].items()}
    # The East Bay and Marin art follows the named shore corridors.
    regions[7] = regions[7].intersection(unary_union([box(7380, 1150, 16850, 5090),
                                                       box(9680, 4410, 17900, 9410)]))
    regions[8] = regions[8].intersection(box(-7950, -15000, -2500, -8070))
    regions[6] = regions[6].union(bridge_area(scene))
    world = box(WORLD.x + 24, WORLD.y + 24, WORLD.right - 24, WORLD.bottom - 24)
    return {stage: region.buffer(65).intersection(world) for stage, region in regions.items()}


def rectangle(frame, inset=0):
    x, y, width, height = frame
    return box(x + inset, y + inset, x + width - inset, y + height - inset)


def make_layout():
    scene = reference_scene(8)
    regions = coverage(load(), scene)
    original = unary_union([box(f.x + 120, f.y + 120, f.right - 120, f.bottom - 120) for f in APPROVED])
    frames = []
    for key, (stage, frame, label) in PILOTS.items():
        frames.append({"id": key, "stage": stage, "frame": frame, "label": label, "kind": "area", "wave": 0})
    landmarks = [(point["name"], *camera_point(point["p"])[:2]) for point in places(8)]
    span = bridge_area(scene)
    width, height = 3072, 2048
    stride_x, stride_y = 2688, 1728
    for stage, region in regions.items():
        used = original.union(unary_union([rectangle(row["frame"], 154)
                                           for row in frames if row["stage"] <= stage]))
        wanted = region.difference(used)
        west, top, east, bottom = wanted.bounds
        for row in range(math.floor(top / stride_y), math.ceil(bottom / stride_y)):
            for col in range(math.floor(west / stride_x), math.ceil(east / stride_x)):
                x, y = col * stride_x - (width - stride_x) // 2, row * stride_y - (height - stride_y) // 2
                x = min(max(WORLD.x, x), WORLD.right - width)
                y = min(max(WORLD.y, y), WORLD.bottom - height)
                frame = [x, y, width, height]
                inner = rectangle(frame, 124)
                if inner.intersection(wanted).area < 1:
                    continue
                cx, cy = inner.intersection(wanted).representative_point().coords[0]
                label = min(landmarks, key=lambda mark: math.hypot(mark[1] - cx, mark[2] - cy))[0]
                if stage == 6 and span.intersection(inner).area > 130_000 and inner.intersection(original).area < 650_000:
                    label = "Bay Bridge crossing near " + label
                key = f"v{stage}-area-{col + 16:02d}-{row + 16:02d}"
                frames.append({"id": key, "stage": stage, "frame": frame, "label": label, "kind": "area"})
    detail = places(8)
    for point in detail:
        stage = next(release for release in (6, 7, 8)
                     if point["id"] in {entry["id"] for entry in places(release)})
        x, y, _ = camera_point(point["p"])
        x, y = DETAIL_FOCUS.get(point["id"], TERMINAL_PLATES.get(point["id"], (x, y)))
        x = min(max(WORLD.x, round(x) - 768), WORLD.right - 1536)
        y = min(max(WORLD.y, round(y) - 512), WORLD.bottom - 1024)
        frames.append({"id": point["id"], "stage": stage, "frame": [x, y, 1536, 1024],
                       "label": point["name"], "kind": "detail"})
    pending = [row for row in frames if "wave" not in row and row["kind"] == "area"]
    painted = [(0, original)] + [(row["stage"], rectangle(row["frame"])) for row in frames if "wave" in row]
    wave = 1
    while pending:
        batch = [row for row in pending if any(stage <= row["stage"]
                 and area.intersection(rectangle(row["frame"])).area > 20_000 for stage, area in painted)]
        if not batch:
            batch = [min(pending, key=lambda row: min(area.distance(rectangle(row["frame"]))
                     for stage, area in painted if stage <= row["stage"]))]
        for row in batch:
            row["wave"] = wave
            pending.remove(row)
            painted.append((row["stage"], rectangle(row["frame"])))
        wave += 1
    for row in frames:
        if row["kind"] == "detail":
            row["wave"] = wave
        elif row["id"] == "v6-area-07-18":
            # The southernmost coastal corner follows the finished Lake Merced edge.
            row["wave"] = 7
    return {"camera": WORLD.projection(), "world": [WORLD.x, WORLD.y, WORLD.width, WORLD.height],
            "frames": sorted(frames, key=lambda row: (row["wave"], row["stage"], row["id"]))}


if __name__ == "__main__":
    ART.mkdir(parents=True, exist_ok=True)
    layout = make_layout()
    LAYOUT.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8", newline="\n")
    for stage in (6, 7, 8):
        for kind in ("area", "detail"):
            print(stage, kind, sum(row["stage"] == stage and row["kind"] == kind for row in layout["frames"]))
    for wave in sorted({row["wave"] for row in layout["frames"]}):
        print("wave", wave, sum(row["wave"] == wave for row in layout["frames"]))
