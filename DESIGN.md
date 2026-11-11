# Isometric San Francisco — visual direction

Status: active visual contract for the working waterfront atlas, revised for v0.4. Published coverage is recorded in [coverage](data/coverage-plan.json); see the [Golden Gate extension](docs/superpowers/specs/2026-11-10-golden-gate-design.md) and [regional/detail design](docs/waterfront-corridor-design.md).

## 1. Visual Theme & Atmosphere

A continuous, densely illustrated San Francisco seen through one fixed orthographic camera. Small buildings retain individual roofs, street-facing details and credible scale; waterfront geometry and sloping streets carry the city's identity. Use a restrained pixel-art finish consistent across adjacent tiles. The map fills the viewport. This is a navigable map surface, without a freestanding diorama base.

## 2. Color

UI tokens: `--surface: #111b22`, `--fg: #ecede6`, `--muted: #aebbc1`, `--border: rgba(255,255,255,.14)`, `--accent: #f4b64c`, `--focus: #f4b64c`. The amber accent marks the active control and keyboard focus; limit simultaneous filled accents to two. Check ordinary text at 4.5:1 and controls at 3:1 contrast.

Map colors are independent of UI tokens: warm stone and painted facades, cool roof shadows, muted greens, deep blue water. Night preserves readable silhouettes and localized warm emission. Fog reduces visibility spatially from the coast rather than whitening the whole screen. Weather may justify physical gradients; decorative UI gradients are unnecessary.

## 3. Typography

Use an offline system stack: `"Segoe UI", Arial, sans-serif`. UI sizes: 12, 14, 16 and 20 px; weights: 400, 500 and 600. English body line-height is 1.5. Uppercase labels use .08em tracking. Map labels and interface text stay sharp at every zoom.

## 4. Spacing & Grid

Use 4 / 8 / 12 / 16 / 24 px spacing. Desktop map insets are 16 px. Floating panels are at most 300 px wide; controls have at least 44 px touch targets. A 512 px generation quadrant follows the NYC convention; generation groups, texture tiles and DZI display tiles are separate concepts and need explicit metadata.

## 5. Layout & Composition

Map-first full-window composition. A compact identity/about control at top left, a bottom navigation strip, and collapsible time/weather controls. Avoid permanently covering the city with a large inspector. At 390 px width, place settings in a dismissible bottom sheet and keep navigation reachable above device safe areas. Credits remain available through About.

## 6. Components

Required: pan/zoom/home, pause, simulation speed, independent car/boat/plane toggles, time scrubber and automatic cycle, weather selector and intensity, and About/credits. Coverage and tile boundaries are optional developer views, initially hidden. Use simple line SVGs and explicit accessible names; no emoji feature icons or dashboard statistics cards.

## 7. Motion & Interaction

Animation stays attached to map coordinates while panning or zooming. Ground traffic follows mapped directions and lanes; ships follow water routes; aircraft cross sparingly at a distinct apparent height. Scene time, transport time and weather evolution are independent clocks. Pausing freezes all three clocks while map navigation remains available. Reduced-motion preference starts the scene paused and disables automatic weather transitions until explicitly enabled.

Day-to-night uses registered appearance layers with separate lights and masks. Rain uses registered wet day/night artwork, soaked paving and roofs, reflections, streaks and surface impacts. Weather choices are Clear, Coastal Fog and Rain. Fog uses shoreline-aware fields and depth data where available. Every vehicle surface is constructed in world metres and projected through the map camera. Artificially moving baked shadows is prohibited; physically changing cast shadows requires relightable geometry/buffers.

## 8. Voice & Brand

Working name: Isometric San Francisco. English interface, accessible copy, map labels and main project documentation for the GitHub audience. Use plain labels: Time / Weather / Traffic / Pause / Reset view. Credits say “Inspired by Isometric NYC and Isometric Vancouver”; do not imply endorsement, affiliation or that their artwork depicts San Francisco.

## 9. Anti-patterns

Do not replace buildings with generic box grids, vary the camera between tiles, place map geometry on a pedestal, leave conspicuous tile seams, ship baked cars underneath moving cars, show vehicles through buildings, detach effects during zoom, or count recoloring as completed lighting. Do not substitute another city's tiles for missing San Francisco artwork. Do not report planned area as completed coverage, simulated trips as observed traffic, or atmosphere effects as climate-model outputs.
