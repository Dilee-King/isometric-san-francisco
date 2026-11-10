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
