import assert from "node:assert/strict";
import { test } from "node:test";
import { decodeSourceDepth, maskIndex, sceneTransfer } from "./atlas.ts";
import { defaultControls } from "./model.ts";
import type { Frame } from "./types.ts";

test("scene transfer preserves pause, hour and independent simulation clocks", () => {
  const frame: Frame = {
    clock: { transportTime: 55, environmentTime: 21, hour: 22.25 },
    controls: {
      ...defaultControls,
      paused: true,
      autoHour: true,
      weather: "rain",
      boats: false,
      rate: 4,
    },
    poses: [
      {
        id: "ferry",
        kind: "ferry",
        point: [200, 50, 0.7],
        direction: [1, 0, 0],
        moving: true,
        speed: 5,
        color: "#ffffff",
      },
    ],
    sequence: 12,
  };
  const transferred = sceneTransfer(frame);
  assert.deepEqual(transferred.clock, frame.clock);
  assert.deepEqual(transferred.controls, frame.controls);
  assert.equal(transferred.poses.length, 0);
  assert.equal(transferred.sequence, 0);
  assert.notEqual(transferred.clock, frame.clock);
});

test("mask coordinates use texture dimensions rather than artwork dimensions", () => {
  assert.equal(maskIndex(600, 300, 2400, 1200, 600, 300), (75 * 600 + 150) * 4);
  assert.equal(
    maskIndex(2399.9, 1199.9, 2400, 1200, 600, 300),
    (600 * 300 - 1) * 4,
  );
  assert.equal(maskIndex(2400, 0, 2400, 1200, 600, 300), -1);
  assert.equal(maskIndex(-0.05, 0, 2400, 1200, 600, 300), -1);
});

test("expanded depth encoding does not saturate the southern waterfront", () => {
  const { offset, range } = { offset: 8000, range: 16000 };
  const depth = 3110,
    packed = Math.round(((depth + offset) / range) * 65535);
  assert.ok(
    Math.abs(
      decodeSourceDepth(packed >> 8, packed & 255, { offset, range }) - depth,
    ) < 0.13,
  );
});
