# Waterfront v0.1 verification — 2026-11-10

This is a working continuous sample, not a full-city map.

## Observed checks

- `npm test`: 10 meaningful projection, route, clock, pause, visibility, toggle, dwell and lighting invariants passed. Initial test run failed before `model.ts` existed, then passed after implementation.
- `npm run build`: TypeScript and Vite production build passed. OpenSeadragon and React currently share one approximately 595 kB minified application bundle (approximately 166 kB gzip); no frame-rate guarantee is claimed.
- `python tools/package_tiles.py`: equal 1536 × 1024 day/night layers, 36 DZI pyramid tiles total, 6 native-detail tiles per appearance, 22 source-directed road cycles. All ship centrelines avoid source land/piers with hull clearance.
- Actual production-browser workflow: car/ferry/cargo/plane motion; all-clock pause; independent traffic toggles; automatic day clock while paused; pan/zoom; night tile loading; cloudy/fog/rain presets; About/Escape; 390 × 844 mobile controls; reduced-motion initial pause. No page errors or failed resource responses in that run.
- Initial observed desktop frame: 26 visible cars, three boats, one aircraft. Counts change with simulation time and viewport; 72 car instances are configured overall.
- Two paused full-page captures were pixel-identical (`ImageChops.difference(...).getbbox()` returned `None`). This check was performed after map assets settled.
- A fresh independent whole-branch review identified three material edge paths: background worker advancement, unavailable WebGL2 weather controls, and stale source masks during regeneration. All three were reproduced before fixes and then passed regression checks: a model visibility invariant; `tools/qa-regressions.js`; and `python tools/test_source_pipeline.py`. The browser visibility check dispatches a synthetic Page Visibility event; it does not claim an observed OS/minimized-tab transition.
- Without WebGL2, the map/night/traffic remain available, a capability notice appears, and unavailable weather controls are disabled. Hidden pages suspend all scene clocks without changing the user's pause choice.

Script: [qa-browser.js](../tools/qa-browser.js), executed through the Playwright CLI against the local production preview. Screenshots in [screenshots](screenshots/) are captures of the actual application, not generated interface mockups.

## Published version

- [Live demo](https://dilee-king.github.io/isometric-san-francisco/).
- [GitHub build and Pages deployment](https://github.com/Dilee-King/isometric-san-francisco/actions/runs/42894009293): both jobs completed successfully for runtime commit `49ebff91f72ddd076602f3d9eea75047840ddf82`.
- Real-browser HTTPS smoke check: map ready, WebGL2 available, 26 cars / 3 boats / 1 plane visible in the initial frame, authored night and rain active, zero page errors or failed resource responses. [Online capture](screenshots/online-night-rain.png).
- [Actual running application recording](Waterfront-actual-demo.mp4): native browser video capture of daytime transport, authored night, rain and fog, transcoded to H.264 MP4. No generated interface video, synthetic camera motion or added audio.

The subsequent documentation/recording commit does not alter the deployed application. It is marked to skip a redundant CI deployment.

## Spatial and rendering limits

The source input extent is a 1200 × 1200 m UTM region, EPSG:32610. The displayed illustration is a cropped orthographic frame within that source view; source-input area is not the completed map's land area. The scene retains its source origin, crop, projection and dimension scaling in `public/map/v1/scene.json`.

Day/night art shares the camera/frame and was visually checked for correspondence. AI drawing can alter local edges and details; no independent final-art geolocation accuracy is claimed. Occlusion uses centre-point tests against source depth, with a small display tolerance, rather than per-fragment final-art depth. Window lights and lane offsets are inferred. Small cars may disappear as a unit along an occluding edge.

Cars follow directed source-road cycles with short waits, without full signal-controller or collision/following simulation. Ships use illustrative water routes and docking dwell; planes are occasional overflights, without airport operations or observed schedules. Weather and light are authored visual effects, without physical sun/shadow, meteorological, thermal or hydrodynamic modeling.
