# Implementation log — waterfront sample

Plan: docs/superpowers/plans/2026-11-10-waterfront-sample.md

- User approved the design and explicitly requested implementation, actual effects and GitHub synchronization on 2026-11-10.
- Execution: native, one whole-branch reviewer at completion. A dedicated clean repository and `codex/waterfront-sample` branch isolate this work from the legacy project; no additional worktree is required.
- Source decision: use the already reviewed, openly distributable DataSF building / USGS lidar / OSM derived snapshot for the orthographic structure reference. The production method follows the reference projects; it does not claim to use their Google imagery or trained weights.
- Source production and illustration quality are checked before map-wide expansion. This turn delivers only the continuous sample.

- Task 1 complete: original day/night imagegen artwork, recorded prompts, calibrated source/depth/water and two deterministic DZI pyramids.
- Task 2 complete: nine clock/projection/route tests observed RED before model implementation, then GREEN.
- Task 3 complete: production TypeScript/build and actual browser workflow passed; paused screenshots were pixel-identical. Source-based centre-point occlusion and inferred lane offsets remain display approximations as documented.
- Route investigation: the legacy schematic ferry routes intersected piers; replaced them with deterministic buffered-land A* water routes. Short road segments were restored to preserve intersections, producing 22 directed road cycles within the sample.
- No additional paid API/GPU was provisioned. Built-in imagegen produced the selected day illustration and registered night edit.
- Final independent review: three P2 findings, no critical findings. All were reproduced RED and fixed GREEN in one pass: visibility suspends worker clocks; absent WebGL2 is visible/disabled in UI; source preparation now refreshes the canonical scene/depth/water bundle. Final model suite 10/10, source pipeline 1/1, normal production browser flow and regression flow passed. No deferred minor findings.
- Accepted scope decisions: approximate final-art geolocation/centre-point occlusion, simple illustrative traffic, visual weather/light and overflight-only aircraft remain as originally documented; no city-wide accuracy or full physical simulations are claimed.
- Task 4 complete: source and fixes synchronized to main and the feature branch; GitHub Actions build/deploy succeeded; the live HTTPS app was verified in a browser with zero page/resource errors, including night/rain and all transport modes. Actual application video is preserved as H.264 MP4. Final documentation-only update does not change runtime code.

## v0.2 — projection, rain and English revision

Plan: [projection-rain-english](superpowers/plans/2026-11-10-projection-rain-english.md).

- Inspected Vancouver's deployed traffic renderer. Independently implemented metric world-space car bodies/cabins, vessel hulls/decks and aircraft fuselage/wings/tail. All vertices share the city projection; WebGL clips against source depth per fragment, with a documented approximate Canvas fallback.
- Preserved dry artwork and Coastal Fog. Built-in imagegen authored registered wet day/night appearances; rain adds staggered streaks, surface impacts and a visibility veil. Source-derived hard-surface masking repairs two invalid rounded footprint rings locally, without changing canonical geometry.
- Current UI, accessibility text, map labels and main repository documents are English. Removed the lower-left decorative caption/sample label. Exposed the desktop panel close control after a real-browser capture timed out on the previously hidden button; the same interaction then passed in the full flow.
- Verified 16/16 model/geometry tests, 1/1 source-bundle regression, 84 runtime asset hashes and production build. Real-browser normal, fallback/visibility and vehicle-detail flows passed. Paused images were identical; rain surfaces still differed with the atmosphere hidden. An enclosing-radius audit passed for every ship route.
- Native browser recording and actual desktop/mobile/detail screenshots are committed. A fresh whole-branch read-only reviewer found no material or minor issues and no declined judgments in `f608e66..6988222`; independently repeated tests/audit/type checks also passed. No deferred findings or scope rulings remain.
- Published `e7646fd` to main and the feature branch. GitHub Actions [42901775919](https://github.com/Dilee-King/isometric-san-francisco/actions/runs/42901775919) passed build/deploy. Actual live HTTPS verification confirmed the v2 scene, projected meshes, English UI and wet day/night with zero page/resource errors. Final verification/capture update skips redundant CI and changes no runtime files.
