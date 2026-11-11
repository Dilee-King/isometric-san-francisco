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
- [x] Project complete metric vehicle surfaces through the shared map camera, including raised cabins, hulls, wings and tails; add per-fragment source-depth clipping and a projected Canvas fallback.

## 4 — Environment

- [x] Registered day/night art, blended twilight appearance and local light layers.
- [x] Clear, coastal fog and rain, independent of hour; remove the redundant cloudy preset in v0.2.
- [x] Author registered wet day/night surfaces with soaked paving, dark roofs, reflections and a disturbed bay; add layered rain streaks and surface impacts.
- [x] Freeze weather/transport/time together and verify zoom registration.
- [x] Record authored appearance versus any genuinely relightable shadows.

## 5 — Expand and release

- [x] Extend the detailed waterfront from Fisherman's Wharf to Mission Bay while retaining native patch density and four appearances.
- [x] Add a Bay Area overview and return to the detailed corridor with preserved controls and clocks.
- [x] Extend the waterfront through the Marina and Presidio to the Golden Gate Bridge and harmonize offshore water across tile boundaries.
- [x] Connect Ferry Building, the Financial District, Chinatown, North Beach and Fisherman's Wharf, then extend to Union Square.
- [x] Load visible imagery through named region packages with a shared low-zoom pyramid and continuous simulation state.
- [x] Cover the mainland city and nearby islands, and connect both Bay Bridge spans through Yerba Buena Island.
- [x] Add the Port of Oakland, Jack London Square, Alameda terminals and source-constrained vessels.
- [x] Connect the Golden Gate north landing to Fort Baker and Sausalito, with a ferry to San Francisco.
- [ ] Add meaningful code checks, versioned manifests and a measured performance budget.
- [x] Publish the verified sample with GitHub Pages and update instructions; large-area asset storage remains future work.
- [x] Ship an English interface and documentation, without the decorative lower-left caption.

Wider street-level coverage, airport ground operations, live feeds and LCZ research functions have no delivery date in this roadmap.
