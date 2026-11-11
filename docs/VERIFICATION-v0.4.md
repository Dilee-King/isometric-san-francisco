# Golden Gate waterfront — v0.4 verification

The detailed waterfront extends from Mission Bay to the Golden Gate Bridge, with 22 location jumps. The Bay Area overview marks this shoreline coverage. Inland areas beyond the illustrated strip use lower-detail context.

## Geometry and art

- A shared EPSG:32610 origin, 39° camera, and 1.854545 pixels per metre register the eastern and western artwork, roads, and moving objects. Ten new native 1536 × 1024 western plates join the ten eastern plates. Four new context plates and four selected wet-night edits are retained with their exact prompts.
- The western source uses 31,416 candidate DataSF footprints from three pages, bounded OSM ways and nodes, and USGS 3DEP terrain. The snapshot adds 2,021 building records, 2,520 road/path records and 1,756 mapped trees. See [provenance](../data/golden-gate/provenance.json) and [acknowledgments](../ACKNOWLEDGMENTS.md).
- The [bridge drawing](../tools/paint_golden_gate.py) uses one continuous metric profile for both towers, the deck and approaches. The separate bridge depth layer prevents bare-earth samples from hiding sections of the deck. The bridge geometry, lighting, roads and traffic are illustrative; they are not engineering or traffic records.
- Every vessel route exceeds its enclosing hull radius against source land and bridge pier obstacles. The four appearance pyramids use one water field per appearance. The blend protects mapped land, piers and near-shore texture, tapering from 70 to 285 native pixels offshore.

## Verified in the running app

- All 19 Node tests, 11 Python tests, original asset audit, v3/v4 atlas audits and the TypeScript/Vite production build passed. The v4 audit checked 4,192 runtime files, including 4,176 tiles. The usual Vite chunk-size advisory remains.
- Chromium requested 35 distinct v4 tiles for the first view. A real drag crossed the old Wharf boundary. All new location jumps, two-tower framing, independent transport switches, fog, dry night, wet day/night, southern traffic, and return from the overview passed. The regional switch preserved the paused clock and controls. The 390 × 844 viewport kept both bridge towers and switched between views without horizontal overflow.
- At one bridge viewpoint the isolated WebGL render drew 221 nontransparent car pixels, 174 cargo-vessel pixels and 80 aircraft pixels. The southern route check drew 850 pixels. These are examples from the final browser test; counts depend on time and viewport.
- Reduced-motion startup, synthetic Page Visibility suspension/resumption, and the projected Canvas fallback with an unavailable-weather notice passed. The synthetic event does not claim OS-level tab hiding.
- With the atmosphere hidden and motion paused, the dry and wet Marina crops differed by mean absolute RGB values 30.77 / 17.00 / 7.77. The wet material is in the map as well as in the animated weather layer.
- The matched [offshore comparison](screenshots/v0.4/offshore-comparison.jpg) uses the same camera coordinates and browser scale. In the sampled strips across the old Wharf plate boundary, the mean RGB step fell from 5.08 to 0.31 (0–255 scale). The two uncropped browser captures are [v0.3](screenshots/v0.4/offshore-v03.jpg) and [v0.4](screenshots/v0.4/offshore-v04.jpg).

Browser flows: [waterfront](../tools/qa-golden-gate.js), [water comparison](../tools/qa-offshore-comparison.js), [fallback and visibility](../tools/qa-regressions.js). The [52-second actual application recording](Waterfront-actual-demo-v0.4.mp4) shows the Wharf-to-Marina drag, bridge traffic and overflight, clear/fog/rain, and the updated regional overview. It is a 1440 × 960, 25 fps H.264 capture of the browser, with no added audio.

## Independent review

The reviewer independently repeated the runtime audits, tests, production build and a Chromium route through Fort Point, wet night and the Bay Area view. The review found a south approach that missed the painted highway, and a clean-checkout failure when Natural Earth files were absent. The shared south connector now follows the painted lane center and tangent. Its endpoint test failed by 194 native pixels before the correction and passed afterward. The rebuilt [Fort Point browser view](screenshots/v0.4/fort-point-clear.jpg) shows the corrected join. Both Natural Earth layers were fetched and opened from an empty cache. The active `npm run tiles` command now packages v0.4.

The smaller arc at Aquatic Park is the separately mapped [Hyde Street Breakwater](https://parkplanning.nps.gov/projectHome.cfm?ProjectID=42980), and is retained alongside Municipal Pier. Survey-grade alignment and performance on physical mobile devices were outside the review scope.

## Publication

GitHub Actions [42934464036](https://github.com/Dilee-King/isometric-san-francisco/actions/runs/42934464036) built and deployed `ceaab30`. The [public HTTPS app](https://dilee-king.github.io/isometric-san-francisco/?v=0.4.0) passed a Chromium check of both v0.4 views, 22 jumps, the WebGL vehicle renderer, wet night and the unchanged paused clock across views. The run observed no page or console errors and no failing resource responses.

Public-site captures: [Golden Gate Bridge](screenshots/v0.4/online-bridge-clear.jpg), [coastal fog](screenshots/v0.4/online-bridge-coastal-fog.jpg), [Marina rain at night](screenshots/v0.4/online-marina-rain-night.jpg), and [Bay Area overview](screenshots/v0.4/online-bay-overview.jpg).
