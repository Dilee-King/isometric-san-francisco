# Assets and provenance

Four selected original 1536 × 1024 PNG appearances are included: dry day, dry night, rain day and rain night. The dry pair is preserved from v0.1. The wet pair was authored as registered image edits using the Codex built-in imagegen tool; the service did not expose a separate model identifier.

Exact prompts are in [prompts](prompts/). Source dates, licenses, artwork roles and SHA-256 checksums are in [data/provenance.json](../data/provenance.json). The current [runtime manifest](../public/map/v2/manifest.json) records the four appearances, camera-sized outputs, 72 pyramid tiles, masks, routes and all 84 runtime-asset checksums. [package_tiles.py](../tools/package_tiles.py) performs deterministic image conversion, pyramid cutting and source-derived display-mask preparation.

The artwork was guided by our DataSF/USGS/OpenStreetMap structure reference. No NYC or Vancouver artwork, trained weights or unverified-license renderer code is included. AI drawing can alter local edges; shared dimensions and a fixed camera do not imply surveyed final-art accuracy. Depth, water, window lights and the hard-surface mask are approximate display proxies. Two invalid rounded footprint rings are repaired only when deriving the hard-surface mask; canonical input geometry is retained.

Original project code/documentation use the repository MIT license. Third-party data retain DataSF PDDL, USGS public-domain and OpenStreetMap ODbL notices; see [Acknowledgments](../ACKNOWLEDGMENTS.md). Tool-generated artwork is identified as such, without a claim of exclusive rights or a separate third-party copyright license.

This small sample keeps selected originals and runtime tiles in Git for reproducible deployment. The previous `public/map/v1` namespace remains available as release history. Raw lidar/captures, local reference inspection files, build output and credentials remain ignored; wider-area asset storage is future work.
