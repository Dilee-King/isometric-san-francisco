# Projection, Rain and English Revision Plan

> **For agentic workers:** Native execution using superpowers:executing-plans; one fresh whole-branch review before delivery.

**Goal:** Correct transport perspective using the Vancouver method, make rain visibly transform the city, remove lower-left prose, and ship an English-facing GitHub demo.

**Architecture:** Every vehicle vertex is constructed in local forward/side/up metres, transformed to world ENU, and projected by the existing orthographic camera. An original lightweight mesh renderer adds body/roof/hull/fuselage surfaces and per-fragment source-depth occlusion. Dry art is retained; original registered wet day/night images and animated surface/rain effects form the rainy appearance. All layers use the same camera and clocks.

**Spec:** User feedback of 2026-11-10, plus the existing project design. Clear and Coastal Fog are retained, Cloudy is removed, Rain is rebuilt. All current UI, accessible copy, map labels and main README use English. The lower-left decorative caption and sample label are removed; map tools and required source credits remain.

## Global Constraints

- Preserve the continuous sample, navigation, time controls, traffic toggles, pause, visibility suspension and reduced motion.
- Inspect Vancouver's deployed `traffic.js`; use observed geometric principles, without copying unverified-license code or assets.
- Source geometry and final AI artwork remain approximate; do not claim measured final-art geolocation or physical weather simulation.
- Use a new `map/v2` asset namespace and retain the prior release history.

## Review Focus

- A 90-degree heading change must reproject width/height correctly, not rotate a screen-space icon.
- Hulls and fuselage must have visible height and correctly occluded faces.
- Rain must remain visually distinct when animation is paused, in daylight and at night.
- Clear/fog must keep the approved dry artwork; disabling traffic must not reset clocks.
- No-WebGL fallback and 390 px English labels must remain usable without overflow.

### Task 1: Observed reference and wet artwork

Files: `docs/v0.2-reference-audit.md`, `assets/prompts/waterfront-rain-*.txt`, original rain PNGs, `tools/package_tiles.py`, `public/map/v2/`.

- [x] Record Vancouver world-corner/roof projection, physical dimensions, ordering and masks.
- [x] Generate and inspect registered wet day/night artwork; preserve geography and camera.
- [x] Package four appearance pyramids, masks and manifest in the v2 namespace.

Validation: matched dimensions, native-resolution visual review, source/hash audit and navigable DZI assets.

### Task 2: World-space transport geometry and rendering

Files: `src/VehicleGeometry.ts`, geometry tests, `src/VehicleRenderer.ts`, `src/SpriteRenderer.ts`, `src/MapView.ts`.

Interfaces: `worldOffset(pose,forward,side,up)`, `vehicleFaces(pose)` return world-coordinate surface polygons; all projection uses `project(point,camera)`.

- [x] Write tests for rotated world bases, projected non-orthogonal axes, metric body height, vessel dimensions and aircraft volume; observe failure.
- [x] Build original car, ferry, cargo and aircraft meshes; render projected vertices with source-depth clipping and a Canvas fallback.
- [x] Verify actual headings, sides, roofs and lighting at normal/detail zoom in the browser.

Validation: geometry tests, full model tests, build, source hull audit and actual vehicle close-ups.

### Task 3: Rain environment and English interface

Files: `src/Atmosphere.ts`, `src/App.tsx`, `src/assets.ts`, `src/types.ts`, `src/style.css`, `index.html`, README, active design/handoff docs, QA scripts.

- [x] Integrate wet day/night layers; add rain streaks at multiple scales, impact ripples and reduced visibility while preserving all-clock pause.
- [x] Keep Clear / Coastal Fog / Rain; translate UI/errors/accessibility/map labels and main GitHub documentation.
- [x] Remove lower-left decorative prose and sample label.

Validation: wet-versus-dry paused screenshots, English desktop/390 px UI, working clear/fog/night, capability fallback, pause/toggles/visibility regression flow.

### Task 4: Review, publish and demonstrate

- [x] Run a fresh whole-branch review, resolve material findings with regression checks.
- [x] Capture actual screenshots/recording, update verification and credits.
- [x] Push GitHub, wait for deployment, verify the live page and show the user.
