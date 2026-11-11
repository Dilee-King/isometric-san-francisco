# City core and regional tiles — v0.5 verification

Detailed coverage connects Ferry Building through the Financial District, Chinatown and North Beach to Fisherman's Wharf, with a branch to Union Square. The existing Golden Gate Bridge to Mission Bay waterfront remains part of the same map. The selector has 30 location jumps.

## Source geometry and artwork

- Seven new native 1536 × 1024 detail plates use the existing 39° camera and 1.854545 pixels per metre. Two broader plates cover the inland margins. Nine paired wet-night edits maintain lighting across these new plates. Day, dry night and wet day share registered masks and window samples. All selected PNGs and exact prompts are retained in [city-core artwork](../assets/city-core/).
- The inland snapshot reuses the bounded DataSF footprints, OSM vectors and USGS lidar inputs. It contains 8,580 building records and 7,641 road/path records. Merging it with the retained western source yields 11,360 buildings and 13,925 road/path records. The [provenance](../data/city-core/provenance.json) and [assembly](../data/city-core/assembly.json) retain source hashes and counts. Transamerica Pyramid and Coit Tower use simplified landmark silhouettes registered to the footprint and lidar upper envelope.
- Existing encoded imagery outside the inland patch and resampling margin is copied byte for byte. Each appearance retains 887 of its 1,006 v0.4 tiles. Depth, hard-surface and water mask pixels outside the city patch match v0.4. Offshore color and bridge geometry remain registered in the shared map coordinates.
- The detailed view has 699 configured cars, six ferries, three cargo vessels and five occasional overflights. The new inland roads add 140 cars and a city overflight. These are configured simulation instances. Architecture, lane offsets, occlusion and weather remain illustrative.

## Regional loading

The 12722 × 14408 detailed image uses eight directories, comprising seven region/context packages and a shared low-zoom package. Every visible tile resolves through one Deep Zoom grid. Regions share scene metadata, masks, depth and the worker. Each region has a file manifest. The combined v0.5 release contains 4,176 image tiles across the detailed map and Bay Area view.

Chromium requested 35 tiles in the first Ferry Building view, from `overview`, `embarcadero` and `city-core`. Inactive high-resolution appearances stayed unloaded. The five city jumps requested 90 tiles cumulatively, with the existing cache. One level-12 tile assigned to Marina spans the western edge of the Wharf view. Golden Gate and southern detail loaded after their respective jumps. This check records requests for this viewport and run.

## Running application checks

- All 23 Node tests, 14 Python tests, original asset checks, v3/v4 audits, the v0.5 regional audit and TypeScript/Vite production build passed. The build retains the existing 500 kB JavaScript chunk advisory.
- A real drag crossed the Financial District–Chinatown join. New district jumps retained the same simulation worker and paused clock. City–Bay Area–City transfers preserved controls and the last named city location, with one active map element.
- Cars, ferries, cargo vessels and aircraft changed world position during the live run. Independent transport switches removed their mode and preserved other modes and paused route positions. Isolated WebGL draws showed new cars in Chinatown and Union Square and existing bridge cars after returning west. The new aircraft drew 480 nontransparent pixels over North Beach in the tested frame.
- Clear daylight, coastal fog, dry night, wet day and wet night passed in the new city views. With atmosphere hidden and clocks paused, the matching Chinatown dry/wet map crop differed by mean absolute RGB values 36.37 / 20.18 / 7.62 on the 0–255 scale. Wet material remains visible in the map imagery.
- A 390 × 844 Chromium viewport kept Union Square and the rain controls usable, switched views and showed no horizontal overflow. Reduced-motion startup paused the simulation. Synthetic Page Visibility suspension/resumption and the projected Canvas fallback with its unavailable-weather notice passed. The mobile check uses a browser viewport, and the visibility check uses synthetic events.
- The final local browser flow observed zero page/console errors and zero failing resource responses. Browser flows are retained for [city core](../tools/qa-city-core.js), [fallback and visibility](../tools/qa-regressions.js) and [recording](../tools/record-city-core.js).

The [45-second actual recording](City-core-actual-demo-v0.5.mp4) shows Ferry Building, the Financial District–Chinatown drag, North Beach, the Wharf, Union Square in clear/rain/night, coastal fog, the bridge and Bay Area overview. It is a 1440 × 960, 25 fps H.264 browser capture with the opening load and trailing idle removed.

## Independent review

The review rebuilt all four appearances and the Bay overview in an isolated checkout, decoded all 4,176 tiles at their expected dimensions, and repeated the city and Bay navigation in Chromium. Prepublication checks identified a staged scene that omitted the city overflight and a source refresh that could reach derivation before creating its input manifest. The updated audit checks for the city aircraft, and a browser draw confirms it is visible. The source refresh creates the input manifest before deriving geometry. A separate cache with the retained raw inputs and no manifest reproduced the same inland source SHA-256.

The isolated rebuild produced 49 small wet-day encoding differences. The release uses the freshly rebuilt tiles and matches all 4,024 detailed image tile hashes from that rebuild. The regional audit, production build and browser checks passed on the updated package.

## Publication

GitHub Actions [42942714875](https://github.com/Dilee-King/isometric-san-francisco/actions/runs/42942714875) built and deployed `430c162`. The [public HTTPS atlas](https://dilee-king.github.io/isometric-san-francisco/?v=0.5.0) passed a fresh Chromium check with 30 city jumps and the WebGL vehicle renderer. The opening Ferry Building view requested 36 tiles from the shared overview, Embarcadero and city-core packages. Chinatown, North Beach, Union Square wet day and wet night, and the Bay Area return passed with the paused clock and controls preserved. The run observed zero page or console errors and zero failing resource responses.

Public captures show [Chinatown in daylight](screenshots/v0.5/online-chinatown-clear.jpg), [Union Square in rain at night](screenshots/v0.5/online-union-square-rain-night.jpg) and the [Bay Area overview](screenshots/v0.5/online-bay-overview.jpg).
