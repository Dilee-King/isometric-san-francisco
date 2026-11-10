# Roadmap

## Repository setup

- [x] Record chosen geographic scope and reference-based technical direction.
- [x] Separate planned coverage from completed coverage.
- [x] Define transport, lighting, weather and accessibility acceptance criteria.
- [x] Add visual contract, source audit, credits and contribution templates.

## 1 — Calibrated illustration sample

- [x] Use reviewed open geometry sources and built-in imagegen; record provenance.
- [x] Freeze a camera, coordinate transform and pixel density.
- [x] Produce a continuous 1536 × 1024 sample, six native-detail tiles per appearance.
- [x] Inspect roofs, roads, piers, shoreline, vegetation and deterministic tile seams.
- [x] Retain source-registered depth/water/light proxies; document local AI-art deviations and approximate occlusion.

## 2 — Navigable map

- [x] Build a React/TypeScript/Vite/OpenSeadragon viewer and DZI export flow.
- [x] Add compact controls, credits, coverage state and 390 px layout.
- [x] Verify pan/zoom and world-to-image registration in a real browser.

## 3 — Transport

- [x] Cars: directions, lanes, turning, waits and occlusion.
- [x] Boats: water routes, docking dwell and clipped wakes.
- [x] Aircraft: occasional registered overflights and navigation lights.
- [x] Independent toggles, simulation worker, global pause and reduced motion.

## 4 — Environment

- [x] Registered day/night art, blended twilight appearance and local light layers.
- [x] Clear, cloudy, coastal fog and rain, independent of hour.
- [x] Freeze weather/transport/time together and verify zoom registration.
- [x] Record authored appearance versus any genuinely relightable shadows.

## 5 — Expand and release

- [ ] Expand contiguous city/waterfront coverage without lowering the sample quality.
- [ ] Add meaningful code checks, versioned manifests and a measured performance budget.
- [x] Publish the verified sample with GitHub Pages and update instructions; large-area asset storage remains future work.

Wider Bay Area coverage, airport ground operations, live feeds and LCZ research functions have no delivery date in this initial roadmap.
