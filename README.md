# Isometric San Francisco

A living illustrated map of San Francisco, the Bay Bridge, the Oakland and Alameda waterfront, and the Marin shore to Sausalito. Inspired by [Isometric NYC](https://cannoneyed.com/projects/isometric-nyc) and [Isometric Vancouver](https://vancouver.isoworld.xyz/).

**[Explore the live atlas](https://dilee-king.github.io/isometric-san-francisco/?v=0.8.1)** · [Browser recording](docs/Illustrated-Inner-Bay-actual-demo.mp4) · [Verification](docs/VERIFICATION-illustrated-expansion.md) · [Roadmap](ROADMAP.md)

![Sausalito in the running application](docs/screenshots/v0.8.1/sausalito.jpg)

## Explore

- **City** opens the detailed view. The latest release includes 63 place jumps across San Francisco and the inner Bay. Explore from Ocean Beach to Hunters Point, cross both Bay Bridge spans through Yerba Buena Island, and follow the shores to Alameda and Sausalito.
- **Bay Area** switches to a regional terrain atlas with coastline, 26 towns/cities, major crossings and SFO, OAK and SJC. The amber outline marks the detailed areas and crossings.
- **Time and weather:** Morning, Day, Dusk and Night; manual time or a five-minute cycle; Clear, Coastal Fog and Rain. Rain changes wet surfaces and reflections in addition to moving drops and impacts.
- **Traffic:** independently show cars, vessels and aircraft. The original world-space projection remains; the regional view enlarges transport for legibility. Pausing freezes all clocks, including across map-view switches.
- **Navigation:** drag and scroll, or use the map tools. Home returns to the default view; +/− zoom; Space plays or pauses when the map has focus. On mobile, use **Environment** to show the time/weather panel. Reduced motion starts paused. Without WebGL2, projected Canvas transport and dry lighting remain available; the unavailable effects are explained.

The releases are available from the same viewer.

| Version | Coverage | Browser capture |
| --- | --- | --- |
| [v0.6.1](https://dilee-king.github.io/isometric-san-francisco/?v=0.6.1) | Citywide San Francisco, the Bay Bridge and Yerba Buena Island | [Golden Gate Park](docs/screenshots/v0.6.1/golden-gate-park.jpg), [East Span](docs/screenshots/v0.6.1/bay-bridge-east.jpg) |
| [v0.7.1](https://dilee-king.github.io/isometric-san-francisco/?v=0.7.1) | Port of Oakland, Jack London Square and Alameda ferry terminals | [Port of Oakland](docs/screenshots/v0.7.1/oakland-port.jpg), [Jack London Square in rain](docs/screenshots/v0.7.1/jack-london-rain-night.jpg) |
| [v0.8.1](https://dilee-king.github.io/isometric-san-francisco/?v=0.8.1) | Fort Baker, Sausalito and the ferry across the bay | [Fort Baker](docs/screenshots/v0.8.1/fort-baker.jpg), [Bay overview](docs/screenshots/v0.8.1/bay-overview.jpg) |

## Run locally

Requires Node.js 24+. The map uses bundled assets; runtime does not need a map API key or an external basemap.

```powershell
npm ci
npm run dev
```

Development: `http://127.0.0.1:5186/`. Production preview:

```powershell
npm test
node tools/audit-atlas.mjs
node --experimental-strip-types tools/audit-city-core.mjs
node --experimental-strip-types tools/audit-illustrated-expansion.mjs
npm run build
npm run preview
```

The production preview runs at `http://127.0.0.1:4186/`. GitHub Actions verifies the source/mask and asset checks and deploys GitHub Pages on updates to `main`.

## How it is made

The inner Bay atlas uses the original 39° orthographic camera and a 55296 × 30720 pixel grid. ImageGen extends the v0.5 illustrations in overlapping passes. A new plate uses the completed neighboring artwork and a registered guide for road crossings, parcels and shorelines. Detail plates use the original 1.854545 pixels per metre at the new location jumps. Wider illustrated plates connect those views, following the v0.5 approach to context. Four appearances combine the selected illustrations, wet-night edits, street lighting and a common offshore water field.

Source structures use [DataSF footprints](https://data.sf.gov/Geographic-Locations-and-Boundaries/Building-Footprints/ynuv-fyni), [USGS 2023 lidar](https://www.fisheries.noaa.gov/inport/item/73386), [USGS 3DEP elevation](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer) and [OpenStreetMap](https://www.openstreetmap.org/copyright). The bridge proportions follow the [district's published dimensions](https://www.goldengate.org/bridge/history-research/statistics-data/design-construction-stats/). The regional view uses [Natural Earth](https://www.naturalearthdata.com/) land/urban vectors, 3DEP terrain and schematic connectors. Both views share an EPSG:32610 origin and orientation.

The four WebP pyramids use a shared grid and request high-resolution tiles by visible region. Each release activates its own coverage and routes. Geography supplies drawing guides, visibility masks and the routes that position projected vehicles. The west and east Bay Bridge carriageways use a continuous distance measure through the hidden tunnel segments. Ferry and cargo routes use source shoreline and bridge-pier clearances.

## Rebuild

Selected artwork and exact ImageGen prompts are in [assets/illustrated-expansion](assets/illustrated-expansion/). The original plates are in [assets/city-core](assets/city-core/), [assets/golden-gate](assets/golden-gate/) and [assets/corridor](assets/corridor/). The [registered data](data/illustrated-expansion/) and [source provenance](data/inner-bay/provenance.json) are checked in. Package the three illustrated releases from the selected plates:

```powershell
python -m pip install -r tools/requirements-corridor.txt
npm run tiles
node --experimental-strip-types tools/audit-illustrated-expansion.mjs
```

Use `python tools/illustrated_guides.py --ids civic-center` to regenerate a registered drawing guide. The tile command places the selected artwork, applies the four appearances and writes the regional packs. Completed blocks are reused when their source and output hashes match. [Explore the original v0.5 viewer](https://dilee-king.github.io/isometric-san-francisco/?v=0.5.0)

## Scope

Detailed coverage follows the mainland city, nearby islands, the Oakland and Alameda shoreline and the Marin shore to Sausalito. The Bay Area view supplies broader geographic context. AI artwork can shift individual edges. Lane offsets, facade details, bridge elevations, depth masks, lights and weather remain illustrative. Transport follows configured source-directed routes. See [coverage](data/coverage-plan.json) and [Acknowledgments](ACKNOWLEDGMENTS.md) for boundaries and licenses. Original code and documentation use the [MIT license](LICENSE). Third-party data retain their respective notices.
