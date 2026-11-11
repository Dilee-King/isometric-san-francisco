"""Registered native detail and coverage frames for the v0.5 city core."""

from atlas_geometry import PixelFrame, camera_point

CORE_ART = (
    PixelFrame("north-beach-link", -2340, -2590, 1536, 1024),
    PixelFrame("north-beach", -2140, -1900, 1536, 1024),
    PixelFrame("telegraph-hill", -1340, -2040, 1536, 1024),
    PixelFrame("financial-core", -1490, -1120, 1536, 1024),
    PixelFrame("chinatown", -2490, -1060, 1536, 1024),
    PixelFrame("union-square", -3370, -520, 1536, 1024),
    PixelFrame("market-corridor", -2240, -330, 1536, 1024),
)
CORE_CONTEXT = (
    PixelFrame("upper-core-context", -3840, -2730, 3072, 2048),
    PixelFrame("downtown-context", -3830, -1240, 3072, 2048),
)
CORE_FRAMES = (*CORE_ART, *CORE_CONTEXT)
LANDMARKS = (
    ("financial-district", "Financial District", -122.40210, 37.79270, 30),
    ("transamerica", "Transamerica Pyramid", -122.40280, 37.79520, 112),
    ("chinatown", "Chinatown", -122.40635, 37.79532, 21),
    ("portsmouth-square", "Portsmouth Square", -122.40565, 37.79468, 16),
    ("dragon-gate", "Dragon Gate", -122.40572, 37.79066, 13),
    ("north-beach", "North Beach", -122.41022, 37.80088, 19),
    ("columbus-avenue", "Columbus Avenue", -122.40643, 37.79783, 17),
    ("telegraph-hill", "Telegraph Hill / Coit Tower", -122.40583, 37.80240, 119),
    ("union-square", "Union Square", -122.40748, 37.78805, 28),
)


def jump_points():
    from corridor_inputs import local_xy

    return [
        {"id": identity, "name": name, "p": [*map(float, local_xy(lon, lat)), z],
         "lonLat": [lon, lat]}
        for identity, name, lon, lat, z in LANDMARKS
    ]


def in_core(point, margin=0):
    x, y, _ = camera_point(point)
    return any(
        frame.x - margin <= x < frame.right + margin
        and frame.y - margin <= y < frame.bottom + margin
        for frame in CORE_FRAMES
    )
