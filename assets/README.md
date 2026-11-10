# Assets and provenance

## v0.3 corridor and regional atlas

[corridor](corridor/) contains 52 selected original 1536 × 1024 PNGs and their exact prompts: nine new detailed patches and four context plates, each with dry day, dry night, rain day and rain night. The existing four Ferry Building appearances are reused as the tenth detailed patch. The context plates fill margins at lower native density; the detailed patches retain the original pixels per metre. The imagegen tool did not expose a separate model identity.

[Corridor provenance](../data/corridor/provenance.json) records the bounded source extraction. [The v3 atlas index](../public/map/v3/atlas.json) points to both manifests, including dimensions, source and artwork hashes, tile counts, mask sizes and route coverage. Regional relief is drawn from Natural Earth land/urban vectors and USGS 3DEP elevation. The viewer loads the packaged assets, with no runtime external map API.

## Retained v0.2 artwork

Four selected original 1536 × 1024 PNG appearances are included: dry day, dry night, rain day and rain night. The dry pair is preserved from v0.1. The wet pair was authored as registered image edits using the Codex built-in imagegen tool; the service did not expose a separate model identifier.

Exact prompts are in [prompts](prompts/). Source dates, licenses, artwork roles and SHA-256 checksums are in [data/provenance.json](../data/provenance.json). The current [runtime manifest](../public/map/v2/manifest.json) records the four appearances, camera-sized outputs, 72 pyramid tiles, masks, routes and all 84 runtime-asset checksums. [package_tiles.py](../tools/package_tiles.py) performs deterministic image conversion, pyramid cutting and source-derived display-mask preparation.

The artwork was guided by our DataSF/USGS/OpenStreetMap structure reference. No NYC or Vancouver artwork, trained weights or unverified-license renderer code is included. AI drawing can alter local edges; shared dimensions and a fixed camera do not imply surveyed final-art accuracy. Depth, water, window lights and the hard-surface mask are approximate display proxies. Two invalid rounded footprint rings are repaired only when deriving the hard-surface mask; canonical input geometry is retained.

Original project code/documentation use the repository MIT license. Third-party data retain DataSF PDDL, USGS public-domain and OpenStreetMap ODbL notices; see [Acknowledgments](../ACKNOWLEDGMENTS.md). Tool-generated artwork is identified as such, without a claim of exclusive rights or a separate third-party copyright license.

This small sample keeps selected originals and runtime tiles in Git for reproducible deployment. The previous `public/map/v1` namespace remains available as release history. Raw lidar/captures, local reference inspection files, build output and credentials remain ignored; wider-area asset storage is future work.
