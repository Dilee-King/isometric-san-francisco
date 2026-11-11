import type {
  Clock,
  Controls,
  Point3,
  Pose,
  Projection,
  Route,
} from "./types.ts";

export const defaultControls: Controls = {
  paused: false,
  rate: 1,
  autoHour: false,
  weather: "clear",
  intensity: 0.65,
  cars: true,
  boats: true,
  planes: true,
};
export function project([x, n, z]: Point3, p: Projection) {
  const q = p.east[1] * x + p.north[1] * n;
  return {
    x: p.origin[0] + p.scale * (p.east[0] * x + p.north[0] * n),
    y: p.origin[1] + p.scale * (q * p.sinElevation - z * p.cosElevation),
    depth: q * p.cosElevation + z * p.sinElevation,
  };
}
export function measureRoute(points: Point3[]) {
  const spans: { start: number; end: number; segment: number }[] = [];
  let length = 0;
  for (let segment = 0; segment + 1 < points.length; segment++) {
    const a = points[segment], b = points[segment + 1];
    const size = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    if (size > 0) {
      spans.push({ start: length, end: length + size, segment });
      length += size;
    }
  }
  return { length, spans };
}
type RouteMeasure = ReturnType<typeof measureRoute>;

export function sampleRoute(points: Point3[], distance: number, measure = measureRoute(points)) {
  const { length, spans } = measure;
  if (!length)
    return {
      point: points[0] ?? ([0, 0, 0] as Point3),
      direction: [1, 0, 0] as Point3,
      length: 0,
      segment: -1,
    };
  const at = ((distance % length) + length) % length;
  let low = 0, high = spans.length - 1;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (spans[middle].end >= at) high = middle;
    else low = middle + 1;
  }
  const { start, end, segment } = spans[low];
  const a = points[segment], b = points[segment + 1];
  const span = end - start, t = (at - start) / span;
  return {
    point: a.map((value, axis) => value + (b[axis] - value) * t) as Point3,
    direction: a.map((value, axis) => (b[axis] - value) / span) as Point3,
    length,
    segment,
  };
}
export function advance(
  state: Clock,
  delta: number,
  controls: Controls,
  visible = true,
): Clock {
  if (!visible || controls.paused || !Number.isFinite(delta) || delta <= 0)
    return { ...state };
  const dt = Math.min(0.1, delta);
  return {
    transportTime: state.transportTime + dt * controls.rate,
    environmentTime: state.environmentTime + dt,
    hour: (state.hour + (controls.autoHour ? dt / 12 : 0)) % 24,
  };
}
export function nightAmount(hour: number) {
  const h = ((hour % 24) + 24) % 24,
    smooth = (x: number) => {
      const t = Math.max(0, Math.min(1, x));
      return t * t * (3 - 2 * t);
    };
  return h < 8 ? 1 - smooth((h - 5) / 3) : smooth((h - 17.5) / 3.5);
}

export function transportMagnification(maximum: number, pixelsPerMetre: number, adaptive?: boolean) {
  return adaptive ? Math.max(1, Math.min(maximum, 1.1 / pixelsPerMetre)) : maximum;
}

export function transportFrame(
  clock: Clock,
  routes: Route[],
  controls: Controls,
  measures?: ReadonlyMap<Route, RouteMeasure>,
): Pose[] {
  const result: Pose[] = [];
  for (const route of routes) {
    if (
      (route.kind === "car" && !controls.cars) ||
      (route.kind === "plane" && !controls.planes) ||
      (["ferry", "cargo"].includes(route.kind) && !controls.boats)
    )
      continue;
    const measure = measures?.get(route) ?? measureRoute(route.points);
    const { length } = measure;
    if (!length) continue;
    let moving = true,
      distance = 0;
    if (route.kind === "plane") {
      const t = (clock.transportTime + route.phase) % 95;
      if (t > 34) continue;
      distance = Math.min(length - 0.001, (t / 34) * length);
    } else {
      const dwell = route.dwell ?? (route.kind === "car" ? 2.8 : 0);
      const t =
        (clock.transportTime + route.phase) % (length / route.speed + dwell);
      moving = t >= dwell;
      distance = Math.max(0, t - dwell) * route.speed;
    }
    const sample = sampleRoute(route.points, distance, measure);
    if (route.hiddenSegments?.includes(sample.segment)) continue;
    result.push({
      id: route.id,
      kind: route.kind,
      point: sample.point,
      direction: sample.direction,
      speed: moving ? route.speed : 0,
      moving,
      color: route.color ?? "#e6e3d8",
    });
  }
  return result;
}
