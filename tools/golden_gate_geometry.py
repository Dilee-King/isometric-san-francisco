"""Native-scale pixel frames and one metric deck for the Golden Gate Bridge."""

from dataclasses import dataclass
import math

from atlas_geometry import ART_FRAMES, PixelFrame, camera_point

ATLAS = PixelFrame('waterfront', -10900, -10160, 12722, 14408)
WEST_ART = (
    PixelFrame('aquatic-park', -3490, -3730, 1536, 1024),
    PixelFrame('fort-mason', -4310, -4060, 1536, 1024),
    PixelFrame('marina-green', -5320, -4430, 1536, 1024),
    PixelFrame('palace-of-fine-arts', -6430, -4790, 1536, 1024),
    PixelFrame('crissy-east', -7210, -5220, 1536, 1024),
    PixelFrame('tunnel-tops', -7650, -4920, 1536, 1024),
    PixelFrame('crissy-field', -8310, -5770, 1536, 1024),
    PixelFrame('west-bluff', -9160, -6420, 1536, 1024),
    PixelFrame('fort-point', -9780, -7180, 1536, 1024),
    PixelFrame('marin-landing', -7900, -9900, 1536, 1024),
)
WEST_CONTEXT = (
    PixelFrame('marina-context', -6540, -5280, 4608, 3072),
    PixelFrame('presidio-east-context', -8300, -5680, 3072, 2048),
    PixelFrame('presidio-west-context', -10760, -7560, 4608, 3072),
    PixelFrame('headlands-context', -9780, -10160, 4608, 3072),
)
DETAIL_FRAMES = (*WEST_ART, *ART_FRAMES)
BRIDGE_FRAME = PixelFrame('golden-gate-bridge', -9850, -9550, 3500, 3700)

LANDMARKS = (
    ('golden-gate-bridge','Golden Gate Bridge',-122.47853,37.81962,98,3000),
    ('fort-point','Fort Point',-122.47701,37.81057,14,1080),
    ('west-bluff','Crissy Field West Bluff',-122.46966,37.80815,5,1080),
    ('crissy-field','Crissy Field',-122.46122,37.80636,4,1080),
    ('tunnel-tops','Presidio Tunnel Tops',-122.45547,37.80137,20,1080),
    ('crissy-east','Crissy Field East Beach',-122.45252,37.80602,3,1080),
    ('palace-of-fine-arts','Palace of Fine Arts',-122.44889,37.80292,13,1080),
    ('marina-green','Marina Green',-122.43934,37.80595,3,1080),
    ('fort-mason','Fort Mason',-122.43250,37.80608,10,1080),
    ('aquatic-park','Aquatic Park',-122.42360,37.80705,3,1080),
)


@dataclass(frozen=True)
class BridgeProfile:
    """Illustrative roadway, towers and cables on a single straight metric axis.

    Official main/side spans, tower height and width set the proportions.
    The crown, approaches and structure depths are display approximations.
    """
    center: tuple = (-122.47853,37.81962)
    center_metres: tuple = (-7430.67901291023,2631.399171174038)
    heading: float = math.radians(-5.65)
    start: int = -735
    end: int = 2002
    lanes: tuple = (-7.5,-4.5,-1.5,1.5,4.5,7.5)

    @property
    def approach_start(self):
        return self.start-83

    @property
    def approach_end(self):
        return self.end+60

    def point(self, station, across=0., z=None):
        e,n = self.center_metres
        s,c = math.sin(self.heading),math.cos(self.heading)
        if station < self.start or station > self.end:
            if station < self.start:
                a=self.start
                goal=(-7201.,1193.)
                t=min(1.,(a-station)/(a-self.approach_start))
            else:
                a=self.end
                goal=(-7637.17,4039.21)
                t=min(1.,(station-a)/(self.approach_end-a))
            b=self.point(a,across)
            return (b[0]*(1-t)+(goal[0]+across*c)*t,
                    b[1]*(1-t)+(goal[1]-across*s)*t,self.deck(station) if z is None else z)
        # Taper into the mapped land approaches outside the straight suspension.
        if station < -343:
            across += 61.*min(1.,((-343-station)/(-343-self.start))**2)
        if station > 1623:
            across -= 58.*min(1.,((station-1623)/(self.end-1623))**2)
        return (e+(station-640)*s+across*c,
                n+(station-640)*c-across*s, self.deck(station) if z is None else z)

    def deck(self, station):
        if station < self.start:
            return 68.-12.*min(1.,(self.start-station)/(self.start-self.approach_start))
        if station > self.end:
            return 68.+2.1*min(1.,(station-self.end)/(self.approach_end-self.end))
        if station < 0:
            return 75. + 7.*max(self.start,station)/-self.start
        if station > 1280:
            return 75. - 7.*min(self.end-1280,station-1280)/(self.end-1280)
        return 82. - 7.*((station-640)/640)**2

    def cable(self, station):
        if station < 0:
            return 95.+132.*((station+343.)/343.)**1.25
        if station > 1280:
            return 95.+132.*((1623.-station)/343.)**1.25
        return 92.+135.*((station-640)/640.)**2


def jump_points():
    from corridor_inputs import local_xy
    return [{'id':key,'name':name,'p':[*map(float,local_xy(lon,lat)),z],
             'lonLat':[lon,lat],'viewHeight':view,
             **({'viewWidth':3150} if key=='golden-gate-bridge' else {})}
            for key,name,lon,lat,z,view in LANDMARKS]


def coverage_frames():
    return (*DETAIL_FRAMES, BRIDGE_FRAME)


def detail_contains(p):
    x,y,_ = camera_point(p)
    return any(f.contains(x,y) for f in coverage_frames())
