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
export function sampleRoute(points: Point3[], distance: number) {
  const spans = points
    .slice(1)
    .map((p, i) => Math.hypot(...p.map((v, j) => v - points[i][j])));
  const length = spans.reduce((a, b) => a + b, 0);
  if (!length)
    return {
      point: points[0] ?? ([0, 0, 0] as Point3),
      direction: [1, 0, 0] as Point3,
      length: 0,
    };
  let at = ((distance % length) + length) % length;
  for (let i = 0; i < spans.length; i++) {
    if (!spans[i]) continue;
    if (at <= spans[i] || i === spans.length - 1) {
      const a = points[i],
        b = points[i + 1],
        t = at / spans[i];
      return {
        point: a.map((v, j) => v + (b[j] - v) * t) as Point3,
        direction: a.map((v, j) => (b[j] - v) / spans[i]) as Point3,
        length,
      };
    }
    at -= spans[i];
  }
  return { point: points[0], direction: [1, 0, 0] as Point3, length };
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
export function transportFrame(
  clock: Clock,
  routes: Route[],
  controls: Controls,
): Pose[] {
  const result: Pose[] = [];
  for (const route of routes) {
    if (
      (route.kind === "car" && !controls.cars) ||
      (route.kind === "plane" && !controls.planes) ||
      (["ferry", "cargo"].includes(route.kind) && !controls.boats)
    )
      continue;
    const length = sampleRoute(route.points, 0).length;
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
    const sample = sampleRoute(route.points, distance);
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
