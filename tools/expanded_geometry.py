"""One native-pixel coordinate system for the San Francisco and inner Bay atlas."""

from atlas_geometry import PixelFrame, camera_point
from corridor_inputs import local_xy

WORLD = PixelFrame("inner-bay", -27648, -15360, 55296, 30720)
BLOCK = 3072
HALO = 480
MASK_DIVISOR = 12
DEPTH_ENCODING = {"offset": 22000, "range": 44000}
SOURCE_EXTENT = (-14600, -12300, 16500, 12200)
SF_EXTENT = (-12500, -10600, 4100, 3200)
OSM_EXTENTS = {
    "sf-west": (-13000, -10800, -3600, 3200),
    "sf-east": (-4700, -10800, 5100, 4000),
    "islands": (-3500, -500, 7400, 5400),
    "east-bay": (6500, -3800, 15100, 6300),
    "marin": (-11000, 3200, -4300, 9900),
}

# A place is focused at a projected height on the same camera as the map.
PLACES = {
    6: (
        ("lands-end", "Lands End", -122.5060, 37.7817, 57, 1250),
        ("ocean-beach", "Ocean Beach", -122.5106, 37.7599, 8, 1400),
        ("richmond", "Richmond District", -122.4787, 37.7802, 44, 1500),
        ("golden-gate-park", "Golden Gate Park", -122.4686, 37.7694, 71, 1300),
        ("sunset", "Sunset District", -122.4803, 37.7536, 75, 1450),
        ("alamo-square", "Alamo Square / Painted Ladies", -122.4332, 37.7762, 75, 1080),
        ("civic-center", "Civic Center", -122.4189, 37.7793, 24, 1180),
        ("haight", "Haight-Ashbury", -122.4466, 37.7693, 81, 1180),
        ("castro", "The Castro", -122.4351, 37.7607, 37, 1130),
        ("mission-dolores", "Mission Dolores Park", -122.4268, 37.7595, 38, 1120),
        ("mission", "Mission District", -122.4188, 37.7530, 16, 1180),
        ("twin-peaks", "Twin Peaks", -122.4477, 37.7546, 273, 1550),
        ("noe-valley", "Noe Valley", -122.4337, 37.7513, 59, 1240),
        ("glen-park", "Glen Park", -122.4348, 37.7346, 78, 1300),
        ("lake-merced", "Lake Merced", -122.4940, 37.7226, 12, 1700),
        ("excelsior", "Excelsior", -122.4295, 37.7252, 88, 1500),
        ("bayview", "Bayview", -122.3908, 37.7315, 16, 1400),
        ("hunters-point", "Hunters Point", -122.3705, 37.7297, 20, 1700),
        ("alcatraz", "Alcatraz Island", -122.4230, 37.8267, 21, 1100),
        ("bay-bridge-west", "Bay Bridge / West Span", -122.3750, 37.8028, 75, 2200),
        ("yerba-buena", "Yerba Buena Island", -122.3666, 37.8097, 52, 1550),
        ("treasure-island", "Treasure Island", -122.3710, 37.8244, 12, 1550),
        ("bay-bridge-east", "Bay Bridge / East Span", -122.3497, 37.8175, 60, 2100),
        ("oakland-touchdown", "Oakland Bridge Landing", -122.3099, 37.8243, 16, 1550),
    ),
    7: (
        ("oakland-port", "Port of Oakland", -122.3309, 37.8091, 19, 1600),
        ("middle-harbor", "Middle Harbor Shoreline Park", -122.3341, 37.7978, 12, 1350),
        ("jack-london", "Jack London Square", -122.2782, 37.7942, 12, 1150),
        ("alameda-main", "Alameda Main Street Ferry", -122.2907, 37.7902, 8, 1200),
        ("alameda-seaplane", "Alameda Seaplane Lagoon", -122.2924, 37.7749, 9, 1350),
    ),
    8: (
        ("fort-baker", "Fort Baker / Horseshoe Cove", -122.4759, 37.8338, 18, 1420),
        ("sausalito-shore", "Sausalito / Bridgeway", -122.4798, 37.8470, 18, 1280),
        ("sausalito", "Sausalito Ferry Landing", -122.4780, 37.8561, 12, 1240),
        ("sausalito-marinas", "Sausalito Marinas", -122.4891, 37.8700, 9, 1650),
    ),
}

# The art targets are cropped from the source render at native density.
ART_LOCATIONS = (
    "golden-gate-park", "ocean-beach", "alamo-square", "mission-dolores",
    "twin-peaks", "bayview", "oakland-port", "jack-london", "alameda-main",
    "fort-baker", "sausalito",
)


def places(release):
    result = []
    for version, locations in PLACES.items():
        if version > release:
            continue
        for identity, name, lon, lat, z, view_height in locations:
            result.append({"id": identity, "name": name,
                           "p": [*map(float, local_xy(lon, lat)), z],
                           "lonLat": [lon, lat], "viewHeight": view_height})
    return result


def art_frames():
    return tuple(
        PixelFrame(place["id"], round(x) - 768, round(y) - 512, 1536, 1024)
        for place in places(8) if place["id"] in ART_LOCATIONS
        for x, y, _ in [camera_point(place["p"])]
    )
