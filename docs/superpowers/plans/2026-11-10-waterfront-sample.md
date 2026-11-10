# Waterfront Sample Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for native execution. Steps use checkbox syntax for tracking.

**Goal:** Deliver and show a working continuous Ferry Building / Financial District / Embarcadero illustrated sample with cars, boats, aircraft, day/night and weather, then synchronize GitHub.

**Architecture:** Offline orthographic render from the existing reviewed DataSF/USGS/OSM snapshot guides an original imagegen illustration. A versioned DZI pyramid is viewed with React/OpenSeadragon. Shared projection, source-depth masks, worker simulation and WebGL2 atmosphere keep effects registered.

**Tech Stack:** React, TypeScript, Vite, OpenSeadragon, WebGL2, Canvas2D, Web Worker; Python/Pillow for vector rasterization and deterministic tile packaging; Node test runner for simulation/projection invariants.

**Spec:** [project design](../../project-design.md), approved for execution by the user on 2026-11-10.

## Global Constraints

- Fixed orthographic view, EPSG:32610, one world-to-image transform.
- Use the dedicated repository; preserve the separate legacy project.
- Publish original SF illustration, never reference-site artwork or raw source captures.
- Demonstration traffic/weather; no live-feed or physical climate accuracy claims.
- All clocks freeze on pause; pan/zoom remains active. Start paused under reduced motion.
- A 390 px layout, credits and accurate coverage/source metadata are required.

## Review Focus

- Pausing during automatic time or weather must freeze every evolving scene value.
- Resume after a background-tab delay must not jump vehicles or advance a whole night.
- Viewport resize/device-pixel ratio must preserve sprite/landmark registration.
- Ships must remain over water and cars must disappear behind intervening structures.
- Toggling a transport mode must not restart other routes or the environment clock.

### Task 1: Calibrated illustrated source and asset package

Files: `tools/prepare_source.py`, `tools/package_tiles.py`, `data/source/ferry.json`, `data/provenance.json`, `public/map/`, `assets/prompts/`.

Interfaces: source preparation emits `scene.json` with projection, extent, roads, ships, building surfaces and source-depth/mask PNGs; packaging emits `scene.dzi` and a versioned WebP pyramid. Projection maps `(east,north,height)` to image pixels and depth.

- [x] Prepare an offline orthographic source, controls and masks from the reviewed local snapshot; inspect actual image.
- [x] Generate original detailed illustration with imagegen, preserve geography and camera, inspect alignment.
- [x] Package contiguous illustration quadrants and DZI levels; record hashes, provenance, prompt and limitations.

Validation: valid metadata, matched dimensions, recognized Ferry Building, connected roads/shoreline, adjacent tile continuity; actual native-resolution image review.

### Task 2: Shared projection and transport/environment simulation

Files: `src/model.ts`, `src/model.test.ts`, `src/simulation.worker.ts`, `src/types.ts`, package/TypeScript/Vite configuration.

Interfaces: `project(point,projection)`, `sampleRoute(route,distance)`, `advance(state,delta,controls)`, `transportFrame(state,routes)`; immutable input/output state with independent clocks and transport switches.

- [x] Write invariant tests for route wrapping, zero-length segments, freeze, negative/large delta, independent clocks and toggles; run and observe failure.
- [x] Implement those interfaces and worker messages; run tests to green.

Validation: `npm test` passes all specified invariants; production TypeScript accepts worker and shared model.

### Task 3: Navigable, living waterfront

Files: `src/App.tsx`, `src/MapView.ts`, `src/SpriteRenderer.ts`, `src/Atmosphere.ts`, `src/style.css`, `index.html`.

Interfaces: OpenSeadragon owns image-to-screen transform. Sprite renderer consumes worker snapshots and metadata; atmosphere receives the same transform and frozen environment time. Controls update worker state with sequence acknowledgments.

- [x] Build the map-first viewer, compact controls, independent transport switches, pause, manual hour/automatic cycle and clear/cloudy/fog/rain modes.
- [x] Add illustrated sprites, source-aware occlusion, water-clipped wakes, local windows/lamps and registered WebGL2 atmosphere.
- [x] Exercise desktop/mobile, zoom/pan, mode toggles, reduced motion and pause in a real browser; correct observed defects.

Validation: `npm run build`, no runtime/asset errors, real browser interactions, movement/pause samples and captured day/night/fog/rain images.

### Task 4: Delivery and GitHub update

Files: README, coverage/provenance, roadmap, changelog, verification, screenshots, launch instructions and GitHub workflow.

- [x] Perform a fresh whole-branch review; fix material issues and verify.
- [x] Capture actual application screenshots and an animation preview, open working preview for the user.
- [x] Commit tested source/assets and update GitHub; verify remote commit and delivery links.

Validation: clean working tree, remote SHA matches delivery commit, reproducible `npm ci`, tests and build; distinguish source registration from artwork accuracy.
