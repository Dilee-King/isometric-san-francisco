# Isometric San Francisco — project design

Date: 2026-11-10. This document preserves the initial planning contract. The working v0.2 sample is described in the [README](../README.md), [active visual contract](../DESIGN.md) and [verification record](VERIFICATION-v0.2.md).

## Intent

Create a finely drawn, continuously browsable San Francisco map in dialogue with Isometric NYC and Isometric Vancouver. Cars, boats and aircraft share the scene while time of day and weather change independently. The user's selected first geographical target is San Francisco city and the bay waterfront, followed by wider Bay Area expansion.

The initial design phase established the scope and technical route and created a repository for updates. The implemented waterfront sample does not claim a finished city map. Large-scale expansion follows the reviewed design and implementation plan.

## Scope and spatial support

Target: San Francisco's urban area plus its northern/eastern bay shoreline and adjacent water needed to show maritime activity. Proposed production sequence: Ferry Building, Financial District and Embarcadero; neighboring downtown streets; northern waterfront; SoMa and Mission Bay; further contiguous city neighborhoods. Record the actual published coverage separately from the planning boundary.

The first quality sample is a contiguous region around the Ferry Building, containing both city streets and water. At least four adjacent generation quadrants are required to judge seams and density. Its ground extent and pixel density are chosen through camera calibration; four quadrants are not a substitute for the full city target.

SFO and the East Bay are expansion areas. First-stage aircraft are illustrative overflights. Do not put a fictional runway in the city or label an overflight as an actual scheduled flight.

## Goals

- Recognizable street structure, individual roofs, piers, waterfront and city slope, with consistent dense illustration.
- Fixed-view continuous pan and deep zoom, compact controls and readable credits.
- Cars, ferries/cargo vessels and occasional aircraft visible together, with separate toggles.
- Day/twilight/night, localized city and vehicle lights, and clear/cloudy/fog/rain modes.
- Weather independent of time, with smooth transitions and a usable freeze state.
- Repeatable tile updates through a repository, a versioned coverage/asset manifest, release notes and issue templates.

## Constraints and exclusions

The viewer is a 2D tile map with effects layers. A source 3D model may be used offline to establish orthographic structure, masks and depth. Free-orbit city rendering is outside this product direction.

Illustrative transport does not require live trip feeds, flight tracking or ferry schedules. Atmospheric appearance does not imply a thermal, precipitation or hydrodynamic simulation. LCZ analysis, redevelopment interventions and quantitative climate evaluation are separate future products, not automatically included from earlier experiments.

No paid service, model training job, mass imagery capture, cloud GPU, production hosting or city-wide generation is provisioned in this setup revision. Choose those resources explicitly when preparing the first visual sample. Only assets with a documented route to permitted publication enter a release; public access to a source does not grant redistribution rights.

## Approaches

| Approach | Benefit | Tradeoff | Decision |
| --- | --- | --- | --- |
| Offline orthographic, structure-guided illustrated tiles; 2D deep-zoom viewer and dynamic overlays | Matches NYC/Vancouver's illustrated map method; detailed art can be reviewed tile by tile | Needs seam repair, registered masks and separately authored night appearance | Selected by user's instruction to follow the two references |
| Freely rotatable, live geometric city | Geometry supports arbitrary viewpoints and physical lighting | Rebuilds the visual problem around live 3D; inconsistent with the requested first product direction | Not selected |
| One decorative city illustration with screen-space particles | Quick single-view illustration | Cannot support continuous city expansion, accurate route registration or real depth behavior | Not selected |

## Source production

1. Define coverage, source snapshots and one meter-based local coordinate system: EPSG:32610. Keep horizontal coordinates and vertical datum/unit metadata explicit.
2. Calibrate one orthographic camera and record azimuth, elevation, scale, origin and image axes. Source texture and structural render must use the same camera. Ground/elevated route points project through the same transform.
3. Build reference bundles from permitted city geometry, terrain/height inputs, streets and coastline. The reference authors use Google's photorealistic 3D tiles; equivalent source access/terms for this project's capture and publication have not been established. Do not substitute an unreviewed source under a “same source” claim.
4. Generate/redraw adjacent quadrants using a stable style reference, overlap/infill rules and persistent lineage. Review street continuity, roof/terrain artifacts, water colors and vegetation manually. Image generation backend, sample resolution and prompt are builder proposals until tested.
5. Create clean backgrounds without baked moving vehicles, plus aligned masks for water, structures/depth, ground and emission. AI redrawing can shift edges; compare masks with final artwork and correct them rather than assuming source depth still aligns.
6. Publish an immutable WebP tile pyramid/DZI, metadata, coordinates and checksums. Each release points at a manifest; never overwrite immutable tiles in place.

## Viewer and synchronization

Proposed first implementation: React + TypeScript + Vite for controls; OpenSeadragon for deep-zoom navigation and DZI loading, following NYC's documented stack. Use npm with a committed lockfile for compatibility with the available local workflow; the NYC reference uses Bun, which is not a requirement of the user-visible method.

OpenSeadragon owns the camera. A single adapter converts world to image and image to CSS/device pixels. A WebGL2 overlay uses exactly that transform for sprites, masks, light and weather. Handle device-pixel ratio in that adapter once. Do not maintain a second unsynchronized camera or implement two independent tile loaders.

Traffic simulation runs in a worker, exchanging compact world-coordinate state. Separate rendering from simulation ticks and update only visible entities. Cache tiles with a bounded memory budget and share geometry/masks between light states. A no-WebGL2 fallback may show the static base map with dynamic functions explicitly unavailable.

## Dynamic layers

Cars use mapped, reviewed road directions and inferred/verified lanes. Lane geometry and signals are illustrative when not sourced, and their derivation belongs in metadata. Support stop/wait, turning and headlight/taillight emission. Ground sprites must pass behind structural foreground masks and remain above the relevant road/deck.

Boats use reviewed water routes, with ferry/cargo speeds that read differently. Show simple docking dwell and wakes clipped to water. Do not interpolate a ferry across land or through a pier. Route animation is illustrative, not an observed voyage.

Aircraft are occasional elevated sprites with separate overflight paths, suitable apparent size and navigation lights. They remain registered to map coordinates but draw above ground structures at their assigned height. Fog attenuation follows the aircraft's assigned scene height where supported. First-stage routes need not imply an airport exists in published coverage.

## Time, lighting and weather

State contains `transportTime`, `environmentTime`, `hour`, `weather`, `intensity`, `simulationRate`, three transport toggles and `paused`. Manual hour selection freezes the hour cycle without resetting routes. Weather selection changes its target field without changing the camera or city geometry. Global pause freezes transport, automatic hour advance and weather evolution; pan and zoom remain active.

Use registered day, twilight and night appearance layers plus local emission masks to avoid counting a global blue filter as lighting. Tile structure is identical between appearance states. Short crossfades are acceptable when they preserve registration. Baked daylight cast shadows are not relightable: claim moving sun/shadows only after producing aligned surface/depth or equivalent relightable data. Initial visual time-of-day therefore means authored appearance and emission changes, not a physical solar model.

Weather presets: clear, cloudy, coastal fog and rain. Weather and hour combine independently. Clouds modulate scene light and add gentle large-scale movement; fog progresses from coastal fields, uses distance/height when available and stays spatially stable under map movement; rain, surface response and wakes respect water/ground masks. Do not move all weather solely with viewport coordinates or leave rain running while paused.

Respect `prefers-reduced-motion`: start with clocks paused, suppress automatic transitions and provide explicit opt-in playback. Keyboard users can reach every control. Focus is visible; a closeable mobile sheet does not trap map navigation.

## Repository and releases

Dedicated repository: `isometric-san-francisco`. It contains original source and documentation, small reviewed fixtures, coverage/release manifests, provenance and notices. It excludes raw imagery, old unrelated project output, local paths, credentials, large generated tiles and provider models.

Use small changes, descriptive commits and issues for tile defects. Each tile record eventually carries bounds, image dimensions, camera version, source IDs, source dates/rights, generation settings, parent neighbors, mask revisions, manual corrections, output hashes and review status. Each release ties the viewer commit to one immutable tile/mask manifest.

The initial revision is documentation only. Do not enable a fake deployment workflow or publish a placeholder map. Add meaningful code checks and a deploy pipeline when runnable code exists and an appropriate hosting target is selected.

## Acceptance and milestones

1. Calibration sample: one fixed camera, four or more adjacent full-detail quadrants, matched masks and native-resolution landmark/street/shoreline review.
2. Navigable sample: DZI loading, continuous pan/zoom, coverage manifest, credits, desktop and 390 px verification.
3. Living sample: all three transport modes, correct occlusion, stable projection across zoom, pause and toggles.
4. Environment sample: registered day/twilight/night, local lights, four weather presets, day/night weather combinations and reduced motion.
5. Expand coverage without reducing tile quality, then prepare a versioned public map release and documented update flow.

Verification is functional and visual: exercise controls in a real browser, inspect actual drawn frames, inspect failed requests/console, compare known world/image control points and test route/clock/registration invariants. Performance budgets are measured on the sample before becoming release claims; no frame-rate or city coverage claims are made here.

## Builder choices and unresolved resources

Builder choices already proposed: working name, sampling order, npm-compatible viewer stack, EPSG:32610, DZI/WebP, overflight-only first aircraft stage, separate clocks and a map-first charcoal UI. They are implementation proposals, not new user quotations.

Before artwork production: select and document source-capture access, publication rights, image-generation backend and any needed credentials/budget; choose exact coverage boundary, camera and density through the calibration sample; select large-asset storage and hosting before deployment. These do not block publishing this design repository, but a repository is not proof that those resources exist or the map is ready.
