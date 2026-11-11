# Golden Gate waterfront extension implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation, with one fresh whole-branch reviewer at completion.

**Goal:** Extend the continuous illustrated map to Golden Gate Bridge, blend offshore seams and publish a verified v0.4.

**Design:** [Golden Gate waterfront extension](../specs/2026-11-10-golden-gate-design.md).

**Architecture:** Keep v3 assets and geography reproducible. Register a western source snapshot and native art against the original EPSG:32610 camera. Build v4 appearance pyramids, shared depth and weather masks, and one extended waterfront scene. Preserve the React/OpenSeadragon and simulation interfaces.

### Task 1: Western source and bridge

- [x] Use a dedicated feature branch; verify clean v0.3 baseline.
- [x] Acquire bounded DataSF footprints, OSM shoreline/roads/vegetation, and USGS 3DEP elevation. Save a reproducible source snapshot and attribution.
- [x] Verify old and new frames have equal projected pixels per metre, continuous overlaps and in-frame jump points. Define the two-tower bridge profile, bridge cars, ship pier clearance, and western overflight. Exercise new geometry invariants before and after implementation.

### Task 2: Artwork and sea

- [x] Produce registered western art at native scale, with coherent daylight, night and wet surfaces. Use a single dimensioned bridge graphic and display masks registered to its deck and towers.
- [x] Test that changing the plate edge does not change truly offshore output, and that coast/structures remain intact. Apply the same continuous offshore field and a smooth water-only transition to all appearances.
- [x] Build v4 tiles and overview; update map labels, build, audit and CI.

### Task 3: Real preview and publication

- [x] Exercise desktop/mobile, pan/zoom, projected vehicles, fog/rain/night, reduced motion, scene switch and the existing east. Inspect matched wide-water before/after captures.
- [x] Review, verify and show a real browser recording and captures before synchronizing.
- [x] Publish the tested commit to GitHub, confirm Pages and smoke-test the public HTTPS map.
