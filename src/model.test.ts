import { test } from "node:test";
import assert from "node:assert/strict";
import {
  advance,
  defaultControls,
  project,
  sampleRoute,
  transportFrame,
  nightAmount,
} from "./model.ts";
import type { Projection, Route } from "./types.ts";
const projection: Projection = {
  scale: 2,
  origin: [100, 200],
  sinElevation: 0.6,
  cosElevation: 0.8,
  east: [0.8, 0.6],
  north: [0.6, -0.8],
};
test("project uses one metre-based camera and height direction", () => {
  assert.deepEqual(project([0, 0, 0], projection), {
    x: 100,
    y: 200,
    depth: 0,
  });
  assert.deepEqual(project([0, 0, 10], projection), {
    x: 100,
    y: 184,
    depth: 6,
  });
  assert.equal(project([10, 0, 0], projection).x, 116);
});
test("route wraps positive/negative distances and skips zero-length spans", () => {
  const points: [number, number, number][] = [
    [0, 0, 0],
    [0, 0, 0],
    [10, 0, 0],
    [10, 10, 0],
  ];
  assert.deepEqual(sampleRoute(points, 25).point, [5, 0, 0]);
  assert.deepEqual(sampleRoute(points, -5).point, [10, 5, 0]);
  assert.deepEqual(sampleRoute([[3, 4, 5]], 100).point, [3, 4, 5]);
});
test("pause freezes all clocks including weather and automatic hour", () => {
  const s = { transportTime: 42, environmentTime: 21, hour: 23.9 };
  assert.deepEqual(
    advance(s, 0.05, { ...defaultControls, paused: true, autoHour: true }),
    s,
  );
});
test("background delay is bounded and negative/nonfinite deltas do not advance", () => {
  const s = { transportTime: 0, environmentTime: 0, hour: 12 };
  assert.equal(advance(s, 500, defaultControls).transportTime, 0.1);
  for (const dt of [-10, NaN, Infinity])
    assert.deepEqual(advance(s, dt, defaultControls), s);
});
test("manual hour stays fixed while transport and weather continue independently", () => {
  const c = { ...defaultControls, rate: 3, autoHour: false };
  const next = advance(
    { transportTime: 0, environmentTime: 0, hour: 15 },
    0.05,
    c,
  );
  assert.ok(Math.abs(next.transportTime - 0.15) < 1e-9);
  assert.equal(next.environmentTime, 0.05);
  assert.equal(next.hour, 15);
});
test("automatic day clock wraps without resetting transport", () => {
  const s = advance(
    { transportTime: 100, environmentTime: 20, hour: 23.999 },
    0.1,
    { ...defaultControls, autoHour: true },
  );
  assert.ok(s.hour < 0.1);
  assert.equal(s.transportTime, 100.1);
});
test("hidden-page suspension freezes all clocks without changing the user's pause choice", () => {
  const s = { transportTime: 22, environmentTime: 10, hour: 19 };
  const controls = { ...defaultControls, paused: false, autoHour: true };
  assert.deepEqual(advance(s, 0.08, controls, false), s);
  assert.equal(controls.paused, false);
  assert.ok(advance(s, 0.03, controls, true).transportTime > s.transportTime);
});
const car: Route = {
  id: "car",
  kind: "car",
  points: [
    [0, 0, 3],
    [100, 0, 3],
  ],
  speed: 10,
  phase: 0,
};
test("transport switches only hide the relevant mode and never reset routes", () => {
  const clock = { transportTime: 2, environmentTime: 3, hour: 14 };
  const before = transportFrame(clock, [car], defaultControls);
  assert.equal(
    transportFrame(clock, [car], { ...defaultControls, cars: false }).length,
    0,
  );
  assert.deepEqual(transportFrame(clock, [car], defaultControls), before);
  assert.deepEqual(clock, { transportTime: 2, environmentTime: 3, hour: 14 });
});
test("ferry docking dwell freezes position and suppresses wake motion", () => {
  const ferry: Route = { ...car, id: "ferry", kind: "ferry", dwell: 8 };
  const poses = transportFrame(
    { transportTime: 3, environmentTime: 0, hour: 12 },
    [ferry],
    defaultControls,
  );
  assert.deepEqual(poses[0].point, [0, 0, 3]);
  assert.equal(poses[0].moving, false);
});
test("night lighting remains smooth through midnight and daylight is off", () => {
  assert.equal(nightAmount(12), 0);
  assert.equal(nightAmount(23), 1);
  assert.equal(nightAmount(0), nightAmount(24));
});
