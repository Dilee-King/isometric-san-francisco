# Illustrated Bay Area v0.9.0

The Bay Area view covers the regional frame from the Pacific coast and North Bay to the South Bay and the Delta. Sixteen overlapping 1536 × 1024 ImageGen plates form its 5120 × 3584 regional artwork. Sixteen aerial-guided closer views share the same 39° camera and add eight times the regional pixel density. The City view uses the v0.8.1 detail at its original scale and offers 63 jumps.

The artwork uses [Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html), Natural Earth, USGS elevation and [USDA NAIP aerial guides](https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer). The selected PNGs and prompts are in [the artwork archive](../assets/full-bay/). The [manifest](../public/map/v9-art/bay/manifest.json) records 1,580 tiles, the guide and artwork hashes, and the common projection.

The four appearances share the same tile coordinates. SFO has separately illustrated rainy-day and rainy-night surfaces. San Jose has a paired clear night and Vallejo has a paired rainy night. The four artwork pairs have a zero-pixel full-frame edge-correlation displacement. The procedural weather pass provides the moving precipitation, impacts and coastal fog. A distant camera uses the continuous regional artwork between closer plates. Some detail-to-region transitions are visible when panning at close range.

## Zoom measurements

The [Chromium script](../tools/qa-zoom.js) runs 12 wheel steps out and 12 steps in from Ferry Building, followed by a drag, at 1360 × 900. The before and after use the same v0.8.1 artwork and control settings. Measurements describe this desktop browser run.

| City appearance | Before p95 frame interval | After p95 frame interval |
| --- | ---: | ---: |
| Clear day | 69.2 ms | 7.1 ms |
| Clear night | 76.6 ms | 20.8 ms |
| Rainy night | 97.1 ms | 20.8 ms |

The rainy-night run recorded 30 main-thread long tasks before the change and zero afterwards. The same wheel sequence at SFO on v0.9.0 recorded a 7.0 ms p95 frame interval in rainy night, with zero intervals above 33.4 ms.

The WebGL renderer uploads each vehicle style once and updates positions and headings through instancing. The 2D overlays project fixed lights once, group window styles and stamp lamp glows. A fully painted rainy-night layer takes over from its lower appearance layers. A still, paused map reuses its last animation overlay.

## Browser checks

The [browser script](../tools/qa-full-bay.js) exercises the startup pyramid, wheel zoom and drag, all 16 closer views, day and night rain, coastal fog, traffic, pause across City and Bay Area, and a 390 × 844 mobile viewport. The new scene has 128 car paths, five ferry paths, two cargo paths and five aircraft paths. The regional vessel paths were checked against the source land polygons.

The production preview loaded nine regional daylight tiles at startup and requested higher levels while visiting the closer views. The browser check reported zero page, console or HTTP errors. The previous three illustrated versions also passed the landmark and appearance regression.

[Actual browser recording](Full-Bay-browser-demo.mp4) · [Full Bay](screenshots/v0.9.0/whole-bay.jpg) · [SFO in rain](screenshots/v0.9.0/sfo-rain-night.jpg) · [Alviso](screenshots/v0.9.0/alviso.jpg) · [Vallejo in rain](screenshots/v0.9.0/vallejo-rain-night.jpg)

The Pages upload contains the viewer and supported v0.5–v0.9 releases. Historical v0.3 tile files remain in the source archive.

## Native detail in v0.9.1

At the same 0.34 screen pixels per metre, the v0.9.0 downtown view used a regional tile at 0.034 source pixels per metre. The v0.9.1 view progressively opens the original City pyramid. Wheel zoom and drag across the Ferry Building waterfront reached native level 16 in Bay Area. [Same-camera browser capture](screenshots/v0.9.1/downtown-before-after.jpg)

The default view requests regional tiles. The City and regional detail layers open as their coverage enters the view at higher zoom. New close-ups use native level 19 at 1.854545 source pixels per metre. The location-based zoom limit caps enlargement at 1.25 CSS pixels per available source pixel. As the camera leaves a close-up, its feathered edges give way to the regional artwork.

The browser checks visit all 16 close-ups, check the native day, night and rain URLs, and exercise fog, traffic controls, City switching and a 390 × 844 viewport. The source and tile audit checks 97 retained City blocks, 16 aerial-guided ImageGen plates and 1,492 new tiles across four appearances. [Browser script](../tools/qa-native-bay.js) · [Tile audit](../tools/audit-native-bay.mjs)

The Pages artifact publishes the v0.5–v0.9.1 viewer and assets. The v0.4 tile archive is available in the repository.
