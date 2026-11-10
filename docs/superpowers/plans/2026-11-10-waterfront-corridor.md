# Waterfront Corridor Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation, with one fresh whole-branch reviewer at completion.

**Goal:** Publish the continuous Wharf–Mission Bay waterfront and a whole-bay overview while retaining v0.2 quality and behavior.

**Architecture:** One registered multi-frame illustrated waterfront atlas plus a source-derived regional atlas. Explicit mask dimensions/depth encoding keep the shared world-space renderer bounded. Scene navigation rebuilds camera/assets while initializing the worker from the saved clocks and controls.

**Tech Stack:** Existing React/TypeScript/Vite/OpenSeadragon/WebGL2, Python/Pillow/NumPy/Shapely/PyProj/laspy, built-in imagegen.

**Spec:** `docs/waterfront-corridor-design.md`, implementing the user's approved expansion request.

## Global Constraints

- Preserve 1.854545 waterfront artwork pixels per world metre and the existing camera axes/elevation.
- Current UI, accessible copy, place labels and main documentation remain English; no lower-left decorative prose.
- Clear, Coastal Fog, Rain, dry/wet night, independent traffic switches, global pause, visibility suspension and reduced motion remain.
- Original Ferry Building art is the local style/registration anchor. Record AI-art deviations; no accuracy or physical-simulation claims.
- Use immutable `map/v3` assets; retain v1/v2 history. No paid resource provisioning is required.

## Review Focus

- Scene switches during pause or automatic day/night preserve all clocks and controls.
- Southern corridor vehicle geometry remains visible beyond the old fixed depth range.
- Mask dimensions differing from artwork dimensions still align occlusion and weather during pan/zoom.
- Adjacent illustrated frames and all four appearances preserve shoreline/road/landmark continuity.
- Mobile navigation and regional/detail transitions remain usable, with truthful coverage labels.

### Task 1: Registered source and atlas production

Files: `tools/corridor_source.py`, `tools/atlas_geometry.py`, `tools/test_atlas_geometry.py`, `data/corridor/`, `assets/corridor/`, `tools/package_corridor.py`, `public/map/v3/`.

- [x] Write and observe failing tests for camera registration, frame coverage, depth packing and mask sampling geometry; implement and pass.
- [x] Acquire/reuse bounded open inputs and prepare source structures, landmarks, routes and per-frame references with explicit provenance.
- [x] Author and inspect the four registered appearances; retain original Ferry anchor and check joins at native/detail zoom.
- [x] Export viewport-loadable pyramids, bounded masks, regional atlas and complete hash manifests; audit route/coverage geometry.

### Task 2: Multi-scene rendering and navigation

Files: `src/atlas.ts`, `src/atlas.test.ts`, `src/types.ts`, `src/SpriteRenderer.ts`, `src/VehicleRenderer.ts`, `src/Atmosphere.ts`, `src/MapView.ts`, `src/simulation.worker.ts`, `src/App.tsx`, `src/style.css`.

Interfaces: `SceneData` gains assetRoot, maskSize/depthEncoding, locations and optional transport exaggeration; `MapView` accepts a saved frame and initial location. `sceneTransfer(frame)` preserves clocks and controls. Worker initialization consumes saved clocks without resetting time.

- [x] Write and run RED tests for scene transfer, independent mask indices and expanded depth range, then implement and run GREEN.
- [x] Replace fixed mask/root/depth assumptions; preserve projected transport and capability fallback.
- [x] Add waterfront/overview navigation and location jumps with the existing restrained UI.
- [x] Verify real-browser north/middle/south detail, regional navigation, every appearance, clocks, switches, mobile and fallback paths.

### Task 3: Review, demonstrate and publish

Files: browser QA/recording scripts, README, coverage/provenance/changelog, verification and actual capture artifacts.

- [x] Run meaningful model/geometry/source/asset checks and production build; inspect actual effects and performance behavior.
- [x] Request one read-only fresh whole-branch review; fix material findings with RED→GREEN checks.
- [ ] Record the real application, commit and synchronize GitHub, wait for Pages success, verify HTTPS and show the user.
