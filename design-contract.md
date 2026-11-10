# Reference design contract

Target: a fixed-view illustrated map of San Francisco's urban area and bay waterfront. Audience: people exploring the city and following an evolving public map project.

## Evidence

| Evidence | Confidence | Consequence |
| --- | --- | --- |
| User chose San Francisco city and bay waterfront before the wider Bay Area | provided | Prioritize continuous city/waterfront detail |
| User requested the technical approach of NYC and Vancouver | provided | Use their documented tile-making and viewing approach |
| Cars, boats, aircraft, day/night and weather requested | provided | Treat all as acceptance requirements |
| NYC author article, MIT repository and app documentation | observed, 2026-11-10 | Orthographic source views, AI-assisted tile drawing, seam repair, React/OpenSeadragon/DZI |
| Vancouver live page source and its How it's made / credits text | observed, 2026-11-10 | Fixed camera, structure-guided tile drawing, WebGL2 main viewer, worker traffic, classic OpenSeadragon view |
| Ferry Building/Financial District/Embarcadero as first contiguous sample | inferred implementation choice | Representative streets, tall buildings, piers and navigable water in one sample |
| Aircraft first appear as overflights because SFO is outside the first city scope | inferred implementation choice | Keep aircraft visible without claiming airport ground operations |

## Keep / change / do not copy

| Reference | Keep | Change | Do not copy |
| --- | --- | --- | --- |
| Isometric NYC | Real city structure, orthographic source render, tile generation/repair, deep zoom; reuse licensed code when useful | NYC data and bounds become San Francisco; add transport and environment layers | NYC tile artwork as SF, identity, donations or coverage claims |
| Isometric Vancouver | Detailed continuous map, compact controls, real-road illustrative traffic, WebGL/worker performance ideas | SF shoreline, routes, typography and expanded dynamics | Vancouver tiles, proprietary training sets/weights, sponsor panels or unsupported license assumptions |
| Existing local SF experiments | Potential source records and useful geographic knowledge after provenance review | Deliver a separate illustrated tile project | Unrelated NYC screenshots, legacy builds, raw personal files or unreviewed image assets |

## Final stance

Build a dense San Francisco city illustration as a registered, multiresolution tile map. Match the reference projects' production principles and map interaction. Add separately composited transport, lighting and weather tied to the same coordinates. Start with a small contiguous quality sample, then expand toward the city and its bay-facing coast. Artwork quality remains a gate before scaling coverage.

## Decisions and boundaries

- Selected approach: offline illustrated tiles plus a 2D viewer and dynamic layers. See the alternatives in [project design](docs/project-design.md#approaches).
- First implementation uses NYC's React/TypeScript/Vite/OpenSeadragon/DZI approach; WebGL2 is reserved for synchronized compositing, and traffic simulation uses a worker. This is the builder's choice within the user's selected method.
- Full coverage boundaries, exact camera azimuth/elevation, pixel density, tile artwork provider and asset storage host are not yet frozen. The calibration sample and provenance review resolve them before mass generation.
- The two references do not supply San Francisco artwork, a transferable city-wide style model, or ready-made day/night/weather assets. Those remain work to produce.
- Full Vancouver pipeline/weights have not been verified as publicly available. Its deployed viewer's credited ancestor is not a license for every file or asset.

## Quality gate

- One fixed camera and projection across at least four adjacent full-detail sample quadrants.
- Named landmarks, roofs, streets, piers and shoreline remain coherent at native resolution.
- No visible seams, duplicated structures, baked/moving vehicle overlap or water-color discontinuities.
- Car behind a building is occluded; boat follows water and pauses at a pier; aircraft remains registered across zoom changes.
- Day, twilight and night preserve geometry and add local lights; fog/rain work at both day and night.
- Pause, toggles, keyboard navigation, touch targets and reduced motion work at desktop and 390 px width.
- Source manifest, rights records, status and screenshots describe delivered content accurately.

These are future acceptance criteria. They are not test results for this document-only revision.
