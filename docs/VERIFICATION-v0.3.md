# Waterfront corridor and Bay Area overview — v0.3 verification

Detailed coverage runs continuously from Fisherman's Wharf to Mission Bay. The regional atlas is an overview; it does not claim full Bay Area street-level illustration.

## Source and artwork

- Shared EPSG:32610 origin, 39° orthographic camera and 1.854545 pixels per metre for detailed waterfront artwork. Ten overlapping 1536 × 1024 patches produce four 5372 × 7398 appearances. Original Ferry Building artwork remains the registration anchor.
- Nine new detailed patches and four lower-density context plates per appearance. Selected original PNGs and prompts are checked in. Imagegen can shift individual edges; the local precision of the final illustration is not surveyed.
- The geometry snapshot holds 5,269 building records, 7,898 retained road/path records and 4,171 mapped tree positions within the production selection. The bounded EPT crop includes 21,589,939 returns at depth ≤ 6. These are source-support counts, not a building census of the detailed artwork.
- The regional atlas is 2560 × 1792. Natural Earth coastline and urban context, USGS 3DEP terrain, named simplified crossings, 26 city/town labels and three airport markers support regional orientation. The highlighted polygon shows detailed waterfront coverage.
- Every detailed vessel route exceeds its enclosing hull radius of 16.140 m or 33.354 m against source land/piers. Regional vessels also pass clearance with their illustrative symbol enlargement. Vehicle and environmental effects use a common camera and source-derived display masks, not surveyed final-art depth or a physical weather model.

## Observed application checks

- 19/19 Node model, vehicle and atlas tests; 1/1 original source-bundle regression; 4/4 atlas geometry tests. New atlas modules were observed RED before implementation, then GREEN.
- TypeScript/Vite production build passed. Vite's bundle-size advisory remains. The v2 audit passed all 84 original runtime hashes; v3 audit checked 1,124 runtime files, 1,108 DZI tiles, 40 native-detail appearances and 16 context appearances.
- Actual desktop browser checks passed for all four transport kinds in motion, pause, per-mode switches, continuous drag between patches, place jumps, wet day/night, fog, regional pan/zoom and return, and preserving the clock/controls during a paused scene switch.
- A repeated scene-switch test initially reproduced two retained base elements; the corrected renderer retains exactly one active base element through repeated switches. The normal and mobile integration flows assert the same condition.
- In the final desktop run, the first view requested 29 of the 1,108 v3 tiles. It reported 45 visible cars, three boats and one plane. The southern check rendered 5,706 nontransparent vehicle-layer pixels and reported 40 cars, one boat and one plane. Counts depend on viewport and time; these are a single run, not a frame-rate or load-time guarantee.
- With the animated atmosphere hidden and transport paused, the wet and dry Oracle Park map crops differed by a mean absolute RGB value of 61.52 / 47.55 / 41.87 on a 0–255 scale. Rain changes the underlying illustration independently of the animated streaks.
- The 390 × 844 browser viewport showed no horizontal overflow and retained the location selector, environment controls and regional navigation. Reduced-motion startup, the Canvas/no-WebGL2 path and synthetic Page Visibility suspension/resumption passed. The visibility test is not a claim of OS-level tab hiding.
- Browser runs observed no page/console errors or failed resource responses. Actual captures: [Wharf](screenshots/v0.3/wharf-clear.jpg), [northern join](screenshots/v0.3/northern-join.jpg), [Oracle Park rain](screenshots/v0.3/oracle-rain-night.jpg), [Mission Bay rain](screenshots/v0.3/mission-bay-rain-night.jpg), [Bay Area](screenshots/v0.3/bay-overview.jpg), [mobile](screenshots/v0.3/mobile-rain.jpg).

Browser flows: [corridor](../tools/qa-corridor.js), [fallback and visibility](../tools/qa-regressions.js). Source and attribution: [provenance](../data/corridor/provenance.json), [Acknowledgments](../ACKNOWLEDGMENTS.md).

## Publication

The [45.6-second native browser recording](Waterfront-actual-demo-v0.3.mp4) shows the actual application: Wharf, Pier 39, fog, continuous waterfront pan, Ferry Building, Bay Bridge approach, Oracle Park in rain, Mission Bay at night and the Bay Area view. It is H.264 MP4 at 1440 × 960, 25 fps, without added audio or generated interface footage. A decoded frame was inspected after transcoding.

Independent review and online deployment results are recorded when completed.
