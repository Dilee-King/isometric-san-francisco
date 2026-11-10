# Waterfront corridor and Bay Area overview — v0.3

The user approved contiguous expansion from Fisherman's Wharf to Mission Bay, a whole-bay overview, retained visual detail/transport/time/weather, actual demonstrations and GitHub publication on 2026-11-10.

The waterfront uses the existing 39-degree orthographic camera and 1.854545 pixels per world metre. Four overlapping 3072 × 2048 source frames cover the northern waterfront, Embarcadero/Ferry Building, southern Embarcadero/Oracle Park, and Mission Bay. The built-in generator returned 1536 × 1024, so nine native-sized targets extend the original Ferry anchor at its original density; the larger frames provide lower-density illustrated context around that detailed strip. New artwork uses source footprints, height surfaces, roads and shoreline. Four appearances preserve dry day/night and wet day/night. Adjacent frames are registered, inspected and exported into one immutable DZI pyramid per appearance.

Source acquisition uses DataSF building footprints, a bounded USGS 2023 EPT lidar crop and current OSM vectors. Record dates, CRS, repair counts, actual support and inferred details separately. Original inputs remain immutable. The final illustration is approximate and is not surveyed geometry.

A separate regional atlas shows the whole bay with source coastline/urban context, major cities, bridges and airports. It is an overview for orientation and navigation, not newly claimed detailed city coverage. Native cartographic graphics are appropriate at regional scale; the waterfront remains the full-detail illustrated surface. Regional and detailed cameras share the same ENU origin and axes. Regional transport symbols may be enlarged for legibility and must retain projected shape.

React/OpenSeadragon and the worker remain. Scene switching preserves the transport, environment and hour clocks, pause and all controls. Location navigation exposes Wharf, Pier 39, Ferry Building, Bay Bridge, Oracle Park and Mission Bay. The Bay Area overview provides an explicit return to the detailed waterfront. All UI and repository-facing content remain English, with no lower-left descriptive caption.

Large imagery is loaded as viewport-selected DZI tiles. Display masks use explicit dimensions independent of artwork dimensions, with bounded texture sizes and scene-specific depth encoding. The shader camera-depth range expands to cover the corridor; no fixed v0.2 depth constant may clip southern geometry.

Visual thesis: a continuous richly illustrated waterfront, framed by quiet charcoal controls and an amber navigation accent. Content: map first, locations second, environment as the existing collapsible panel. Interaction: map-space traffic, navigable landmark jumps, and a reversible regional/detail transition.

Acceptance: continuous recognizable shore from Wharf through Ferry Building, Rincon/Pier 30, Oracle Park and Mission Bay; original local density; all four appearances; projected traffic; visible aircraft/boats; correct clock preservation; English desktop and 390px layout; no page/resource errors; valid provenance and deployable asset hashes. Ship clearance and graph direction are illustrative but source constrained. No live feeds, physical climate model or airport ground operations are implied.
