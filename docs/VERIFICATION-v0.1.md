# Waterfront v0.1 verification — 2026-11-10

This is a working continuous sample, not a full-city map.

## Observed checks

- `npm test`: 9 meaningful projection, route, clock, pause, toggle, dwell and lighting invariants passed. Initial test run failed before `model.ts` existed, then passed after implementation.
- `npm run build`: TypeScript and Vite production build passed. OpenSeadragon and React currently share one approximately 595 kB minified application bundle (approximately 166 kB gzip); no frame-rate guarantee is claimed.
- `python tools/package_tiles.py`: equal 1536 × 1024 day/night layers, 36 DZI pyramid tiles total, 6 native-detail tiles per appearance, 22 source-directed road cycles. All ship centrelines avoid source land/piers with hull clearance.
- Actual production-browser workflow: car/ferry/cargo/plane motion; all-clock pause; independent traffic toggles; automatic day clock while paused; pan/zoom; night tile loading; cloudy/fog/rain presets; About/Escape; 390 × 844 mobile controls; reduced-motion initial pause. No page errors or failed resource responses in that run.
- Initial observed desktop frame: 26 visible cars, three boats, one aircraft. Counts change with simulation time and viewport; 72 car instances are configured overall.
- Two paused full-page captures were pixel-identical (`ImageChops.difference(...).getbbox()` returned `None`). This check was performed after map assets settled.

Script: [qa-browser.js](../tools/qa-browser.js), executed through the Playwright CLI against the local production preview. Screenshots in [screenshots](screenshots/) are captures of the actual application, not generated interface mockups.

## Spatial and rendering limits

The source input extent is a 1200 × 1200 m UTM region, EPSG:32610. The displayed illustration is a cropped orthographic frame within that source view; source-input area is not the completed map's land area. The scene retains its source origin, crop, projection and dimension scaling in `public/map/v1/scene.json`.

Day/night art shares the camera/frame and was visually checked for correspondence. AI drawing can alter local edges and details; no independent final-art geolocation accuracy is claimed. Occlusion uses centre-point tests against source depth, with a small display tolerance, rather than per-fragment final-art depth. Window lights and lane offsets are inferred. Small cars may disappear as a unit along an occluding edge.

Cars follow directed source-road cycles with short waits, without full signal-controller or collision/following simulation. Ships use illustrative water routes and docking dwell; planes are occasional overflights, without airport operations or observed schedules. Weather and light are authored visual effects, without physical sun/shadow, meteorological, thermal or hydrodynamic modeling.
