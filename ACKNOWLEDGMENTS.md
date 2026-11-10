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
- Dry and wet day/night illustrations are original AI-generated artwork guided by the open source geometry reference; facade/window details and the heritage clock-tower supplement are illustrative.
- Vancouver's deployed traffic renderer was inspected for its metric corner construction, shared projection and source-mask approach. The v0.2 vehicle geometry and renderer are independently implemented; see the [reference audit](docs/v0.2-reference-audit.md).

When code or data is added, retain the exact required notices and keep a per-source record. Attribution to a software repository does not replace the terms for imagery or other external datasets used by that software.
