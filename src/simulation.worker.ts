import { advance, defaultControls, transportFrame } from "./model.ts";
import type { Clock, Controls, Route } from "./types.ts";
let clock: Clock = { transportTime: 0, environmentTime: 0, hour: 14.25 },
  controls = { ...defaultControls },
  routes: Route[] = [],
  sequence = 0,
  hidden = false,
  last = performance.now();
const emit = () =>
  postMessage({
    clock,
    controls,
    poses: transportFrame(clock, routes, controls),
    sequence,
  });
self.onmessage = (
  event: MessageEvent<{
    routes?: Route[];
    clock?: Clock;
    controls?: Partial<Controls>;
    hour?: number;
    sequence?: number;
    hidden?: boolean;
  }>,
) => {
  if (event.data.routes) routes = event.data.routes;
  if (event.data.clock) clock = { ...event.data.clock };
  if (event.data.hidden !== undefined) hidden = event.data.hidden;
  if (event.data.controls) controls = { ...controls, ...event.data.controls };
  if (event.data.hour !== undefined)
    clock = { ...clock, hour: event.data.hour };
  sequence = event.data.sequence ?? sequence;
  last = performance.now();
  emit();
};
setInterval(() => {
  const now = performance.now();
  const elapsed = (now - last) / 1000;
  last = now;
  if (hidden || controls.paused) return;
  clock = advance(clock, elapsed, controls);
  emit();
}, 33);
