import { test } from "node:test";
import assert from "node:assert/strict";
import { vehicleFaces, worldOffset } from "./VehicleGeometry.ts";
import { project } from "./model.ts";
import type { Pose, Projection } from "./types.ts";
const pose: Pose = {
  id: "car-0",
  kind: "car",
  point: [10, 20, 2],
  direction: [1, 0, 0],
  speed: 5,
  moving: true,
  color: "#c3b491",
};
const camera: Projection = {
  scale: 2,
  origin: [100, 200],
  sinElevation: 0.6,
  cosElevation: 0.8,
  east: [0.8, 0.6],
  north: [0.6, -0.8],
};
test("local forward/side/up positions rotate in world ENU, not in screen space", () => {
  assert.deepEqual(worldOffset(pose, 2, 3, 4), [12, 23, 6]);
  assert.deepEqual(
    worldOffset({ ...pose, direction: [0, 1, 0] }, 2, 3, 4),
    [7, 22, 6],
  );
});
test("projected forward and side axes keep camera foreshortening and are generally not perpendicular", () => {
  const o = project(pose.point, camera),
    f = project(worldOffset(pose, 1, 0, 0), camera),
    s = project(worldOffset(pose, 0, 1, 0), camera);
  assert.ok(
    Math.abs((f.x - o.x) * (s.x - o.x) + (f.y - o.y) * (s.y - o.y)) > 0.1,
  );
  assert.ok(
    Math.abs(
      Math.hypot(f.x - o.x, f.y - o.y) - Math.hypot(s.x - o.x, s.y - o.y),
    ) > 0.1,
  );
});
test("sedan geometry has a physical body and raised cabin", () => {
  const points = vehicleFaces(pose)
    .filter((f) => (f.alpha ?? 1) === 1)
    .flatMap((f) => f.points);
  const min = (i: number) => Math.min(...points.map((p) => p[i])),
    max = (i: number) => Math.max(...points.map((p) => p[i]));
  assert.ok(Math.abs(max(0) - min(0) - 4.5) < 0.01);
  assert.ok(Math.abs(max(1) - min(1) - 1.8) < 0.01);
  assert.ok(max(2) > pose.point[2] + 1.3);
});
test("vessels have metric hulls and elevated superstructure", () => {
  for (const [kind, length] of [
    ["ferry", 31],
    ["cargo", 65],
  ] as const) {
    const p = vehicleFaces({ ...pose, kind })
      .filter((f) => (f.alpha ?? 1) === 1)
      .flatMap((f) => f.points);
    assert.ok(
      Math.abs(
        Math.max(...p.map((x) => x[0])) -
          Math.min(...p.map((x) => x[0])) -
          length,
      ) < 0.01,
    );
    assert.ok(Math.max(...p.map((x) => x[2])) > pose.point[2] + 4);
  }
});
test("aircraft has fuselage volume, swept wings and a raised tail", () => {
  const p = vehicleFaces({ ...pose, kind: "plane" }).flatMap((f) => f.points);
  assert.ok(
    Math.max(...p.map((x) => x[1])) - Math.min(...p.map((x) => x[1])) >= 28,
  );
  assert.ok(
    Math.max(...p.map((x) => x[2])) - Math.min(...p.map((x) => x[2])) > 4,
  );
});
test("all headings produce finite surface vertices", () => {
  for (const kind of ["car", "ferry", "cargo", "plane"] as const) {
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
      const p = {
        ...pose,
        kind,
        direction: [Math.cos(a), Math.sin(a), 0] as [number, number, number],
      };
      const faces = vehicleFaces(p);
      assert.ok(faces.length > 6);
      assert.ok(
        faces.every((f) => f.points.every((v) => v.every(Number.isFinite))),
      );
    }
  }
});
