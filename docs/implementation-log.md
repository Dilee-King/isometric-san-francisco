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

## v0.3 — waterfront corridor and regional atlas

- User authorized detailed extension from Fisherman's Wharf to Mission Bay, a Bay Area overview, retained effects and GitHub publication. Work is isolated on `codex/waterfront-corridor`. [Design](waterfront-corridor-design.md) and [plan](superpowers/plans/2026-11-10-waterfront-corridor.md) record the scope.
- The generator returned 1536 × 1024 for large structural frames. Use native-size detail patches so the coastal strip retains the original metres per pixel, with separate lower-density illustrated context for margins. The tradeoff is more retained source assets; runtime fetches only relevant tiles.
- Derived corridor structure from bounded open footprints, EPT lidar and OSM. Built a terrain-based regional atlas with mapped coastline/urban context and schematic connectors. Both use a common origin and orientation. The frame and ship-clearance audits passed.
- Scene transfer preserves clocks and controls. A real repeated-switch test reproduced two base elements before fixing ownership; it passed with one active base afterwards. All original projection/clock/fallback behaviors and new southern paint checks passed.
- Reviewed the visible edges after the first integration run, replaced low-detail context exposed in common views with registered art, and focused the bridge jump on the completed approach.
- Independent review of `1beca74..4ec5520` found no blocking issues and verified both builds and browser flows, including repeated scene switches while automatic time was running. At wider waterfront zooms, some open-water plate edges are still visible; this visual polish item is documented in [verification](VERIFICATION-v0.3.md).
- Published `35697c8` to main and the feature branch; GitHub Actions [42925359527](https://github.com/Dilee-King/isometric-san-francisco/actions/runs/42925359527) passed build and Pages deploy. Confirmed the published waterfront, wet night, regional overview and retained clock in Chromium with zero page or resource errors. The native recording and public-site screenshots are linked in [verification](VERIFICATION-v0.3.md). This final documentation update does not change the published runtime.

## v0.4 — Golden Gate waterfront

- The user authorized an extension from Fisherman's Wharf through the Marina and Presidio to the Golden Gate Bridge, offshore seam repair, a real preview, and subsequent GitHub publication. See the [design](superpowers/specs/2026-11-10-golden-gate-design.md) and [plan](superpowers/plans/2026-11-10-golden-gate.md).
- Retained the native detail scale and eastern route/art sources. Added ten registered native western daylight plates, four contextual plates, and four authored wet-night edits. Registered wet materials and night lights cover the other western variants.
- An early bridge render exposed a terrain-depth gap at the north approach. A shared independent bridge stamp now preserves the continuous deck and clips vehicles against the same rendered structure. The bridge continuity, land/sea controls, vessel clearances and native overlap checks passed.
- Matched v0.3 and v0.4 Chromium views demonstrate the offshore repair. The full desktop/mobile flow verified western and southern traffic, weather and clocks. Captures and the decoded browser recording are in [verification](VERIFICATION-v0.4.md).
