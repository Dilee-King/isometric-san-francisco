# Acknowledgments

This project is inspired by:

- [Isometric NYC](https://cannoneyed.com/projects/isometric-nyc) by Andy Coenen, and its [MIT-licensed source](https://github.com/cannoneyed/isometric-nyc): orthographic illustrated city tiles, repair workflows and deep-zoom viewing.
- [Isometric Vancouver](https://vancouver.isoworld.xyz/) by [@imnotchalk](https://x.com/imnotchalk): continuous detailed city illustration, waterfront treatment and illustrative traffic.
- [OpenSeadragon](https://openseadragon.github.io/): the viewer underlying NYC and Vancouver's classic map interface.

These references are acknowledged as influences. The projects and their authors have not endorsed or partnered with Isometric San Francisco.

## Third-party materials

The initial revision contained documentation only. Version 0.1 adds original SF illustration and a derived local geometry snapshot, with the notices below. No NYC/Vancouver artwork, training datasets or model weights are bundled.

- OpenSeadragon, React, Vite and related packages retain the notices distributed through their npm packages and lockfile. NYC viewer architecture is referenced; its source code was not copied into this implementation.
- DataSF [Building Footprints](https://data.sf.gov/Geographic-Locations-and-Boundaries/Building-Footprints/ynuv-fyni), published as PDDL: clipped footprint geometry and source height fallback.
- [USGS San Francisco 2023 lidar](https://www.fisheries.noaa.gov/inport/item/73386), US Government public domain: the derived roof/ground snapshot, not the raw LAZ point cloud.
- [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0: 2026-11-09 streets, coast, piers and tree positions. The derived snapshot and selected road tags are available under `data/source/`; the ODbL data notice applies to those OSM-derived database portions separately from the original MIT application code.
- v0.3 uses a separately acquired bounded OSM corridor snapshot. Its source endpoint, timestamp and checksums are in [corridor provenance](data/corridor/provenance.json); the derived geometry is distributed in `data/corridor/source.json.gz`.
- v0.4 extends the DataSF/OSM source with 3DEP terrain. See the [western source snapshot and provenance](data/golden-gate/); the same ODbL notice applies to its OSM-derived database portions. The [Golden Gate Bridge District's dimensions](https://www.goldengate.org/bridge/history-research/statistics-data/design-construction-stats/) guide the independently drawn bridge. The [Presidio's trail map](https://presidio.gov/explore/attractions/golden-gate-promenade-bay-trail) and [NPS Fort Mason description](https://www.nps.gov/places/000/2-exploring-fort-mason.htm) informed landmark selection.
- v0.6–v0.8 use citywide DataSF footprints and [Recreation and Parks Properties](https://data.sf.gov/Culture-and-Recreation/Recreation-and-Parks-Properties/gtr9-ntp6), USGS 3DEP terrain and bounded OpenStreetMap extracts. The [source archive and provenance](data/inner-bay/) retain the derived OSM database portions under ODbL 1.0.
- [Caltrans Bay Bridge documentation](https://dot.ca.gov/-/media/dot-media/district-4/documents/d4-transportation-planning-local-assistance/system-regional-planning/tcrs/f0020234_draft-final-i-80-sfobb-tcr-final-091917-a11y.pdf) guides the illustrated west and east spans. The port and ferry landmarks use the [Port of Oakland](https://www.portofoakland.com/community/waterfront-recreation), [San Francisco Bay Ferry](https://sanfranciscobayferry.com/?page_id=17827), [Fort Baker](https://www.nps.gov/goga/planyourvisit/fort-baker.htm) and [Golden Gate Ferry terminal](https://www.goldengate.org/ferry/riding-the-ferry/terminal-locations-parking/) descriptions.
- The regional overview uses [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) land and urban vectors (public domain) and [USGS 3DEP elevation](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer). Regional connector lines are illustrative.
- The v0.9 regional plates use 2025 [Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) water and primary roads. The 16 closer views use [USDA NAIP aerial imagery from The National Map](https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer) as registered drawing guides. The [tile manifest](public/map/v9-art/bay/manifest.json) records the source hashes.
- Dry and wet day/night illustrations are original AI-generated artwork guided by the open source geometry reference; facade/window details and the heritage clock-tower supplement are illustrative.
- Vancouver's deployed traffic renderer was inspected for its metric corner construction, shared projection and source-mask approach. The v0.2 vehicle geometry and renderer are independently implemented; see the [reference audit](docs/v0.2-reference-audit.md).

When code or data is added, retain the exact required notices and keep a per-source record. Attribution to a software repository does not replace the terms for imagery or other external datasets used by that software.
