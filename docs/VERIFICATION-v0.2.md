# Waterfront v0.2 verification — 2026-11-10

Scope: revise the existing Ferry Building / Financial District / Embarcadero sample. Geographic coverage is unchanged.

## Observed checks

- `npm test`: 16/16 model and geometry tests passed. New geometry tests were observed failing before the implementation existed, then passed. They cover metre-based local axes, non-orthogonal projected axes and foreshortening, raised car cabins, metric hulls, aircraft wings/vertical tail and finite vertices across headings. Existing clock, pause, visibility, route and lighting invariants remain green.
- `python tools/test_source_pipeline.py`: 1/1 source-bundle regression passed, including matching scene/depth/water dimensions after regeneration.
- `node tools/audit-assets.mjs`: all 84 v2 runtime-asset hashes and four source PNG hashes/dimensions passed. Four 1536 × 1024 appearances produce 72 DZI pyramid tiles, including six native-detail tiles per appearance. Two invalid rounded footprint rings are repaired only for the illustrative hard-surface mask; original source geometry is retained.
- `npm run build`: TypeScript and Vite production build passed. The application bundle is approximately 604 kB minified / 168 kB gzip; the bundler's size advisory remains. No performance or frame-rate guarantee is claimed.
- Actual production-browser workflow passed for car/ferry/cargo/aircraft motion, all-clock pause, traffic switches without clock resets, pan/zoom, dry night, wet day/night, retained coastal fog, About/Escape, 390 × 844 mobile controls and reduced-motion initial pause. Current interface text is English; the decorative lower-left caption is absent. Zero page/console errors or failed resource responses were observed in that run.
- The browser reported `webgl2-world-mesh`. Vehicle hulls/bodies/wings use the same world-to-image projection as the city. Actual paused zoom captures are retained for [cars](screenshots/v0.2/car-detail.png), [ferries](screenshots/v0.2/ferry-detail.png) and [aircraft](screenshots/v0.2/plane-detail.png).
- Initial observed desktop frame: 26 visible cars, three boats and one aircraft. Counts depend on simulation time, occlusion and viewport; 72 cars are configured overall.
- Two paused full-page screenshots were pixel-identical. With the animated atmosphere hidden and the same paused transport state, dry/wet map crops differed by a mean absolute RGB value of 48.19 / 32.98 / 29.58 on a 0–255 scale. Rain therefore changes the surfaces independently of the rain-streak overlay. See [rain day](screenshots/v0.2/rain-day.png) and [rain night](screenshots/v0.2/rain-night.png).
- An independent enclosing-radius check found minimum source-land clearance of 19.008 m and 18.312 m for the ferry routes versus a 16.140 m hull radius, and 49.644 m for cargo versus a 33.354 m hull radius. This checks the full model footprint against source land/piers, not final-art geolocation.
- The visibility/no-WebGL regression passed. A synthetic Page Visibility event suspended all worker clocks and preserved the user's pause choice; resuming advanced transport again. With WebGL2 unavailable, the capability notice appeared, unavailable weather controls were disabled, projected Canvas transport remained active and dry night remained available. No actual OS/minimized-tab transition is claimed.

Browser flows: [qa-browser.js](../tools/qa-browser.js), [qa-regressions.js](../tools/qa-regressions.js), [qa-vehicle-detail.js](../tools/qa-vehicle-detail.js). Screenshots are captures of the running production application, not generated interface mockups.

[Actual application recording](Waterfront-actual-demo-v0.2.mp4): 32-second native browser recording, H.264 MP4, 1440 × 960 at 25 fps. It shows moving transport, wet daytime, wet night, dry night and retained coastal fog. It contains no generated interface video or added audio. A decoded frame was inspected after transcoding.

## Publication

The deployment commit, independent review and live HTTPS result will be recorded after publication.

## Remaining display limits

Vancouver's metric corner-construction and shared-projection method informed the independently written renderer; no reference artwork or unverified-license source code was copied. See the [reference audit](v0.2-reference-audit.md).

The source-input region is 1200 × 1200 m in EPSG:32610. The illustration is a cropped orthographic frame; input extent is not completed land area. Dry/wet appearances share a camera and were visually reviewed, but AI drawing can alter local edges. Source-depth masks, window lights, pavement impacts and lane offsets remain approximate display proxies. The WebGL vehicle path clips per fragment against source depth; the Canvas fallback uses approximate face-centre clipping and painter ordering.

Weather, lighting, reflection patterns and traffic are illustrative. The project does not model physical rainfall/runoff, changing solar shadows, full traffic signals/following, live schedules or airport operations. Clear and Coastal Fog retain the original dry artwork. Wider city and Bay Area coverage remain future work.
