# City-core artwork

Seven native 1536 × 1024 daylight plates connect Ferry Building, the Financial District, Chinatown, North Beach and Fisherman's Wharf, with a branch to Union Square. Two context plates cover the inland margins at a lower density. Nine wet-night edits share the daylight geometry and maintain lighting across the overlaps. Adjacent prompt files retain the exact imagegen text.

Regenerate structural references from the checked-in source with `python tools/render_city_core.py`. The references use the existing EPSG:32610 origin, 39° orthographic camera and 1.854545 pixels per metre. The approved Wharf plates supply the illustration and wet-night style references. Transamerica Pyramid and Coit Tower use the retained source footprint and lidar upper envelope for their simplified reference silhouettes.

`tools/package_city_core.py` places these plates in the existing v0.4 image coordinate system. Registered masks, window samples and `tools/golden_gate_lighting.py` supply the other lighting and wet-material appearances. The packager copies existing encoded tiles outside the inland patch and its resampling margin. The new regional directories use one shared Deep Zoom grid.
