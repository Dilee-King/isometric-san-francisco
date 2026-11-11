# Changelog

## 0.5.0 — City core and regional tiles

- Connected Ferry Building through the Financial District, Chinatown and North Beach to Fisherman's Wharf, with detailed coverage to Union Square.
- Added seven native detail plates, two inland context plates, 140 source-directed cars, a city overflight and eight location jumps.
- Packaged the imagery into named regional directories with a shared low-zoom pyramid. A single coordinate system and simulation worker preserve continuous navigation, time and weather.
- Added registered city lighting and wet surfaces, regional tile audits and actual browser captures. See [verification](docs/VERIFICATION-v0.5.md).

## 0.4.0 — Golden Gate waterfront extension

- Connected Fisherman's Wharf to the Golden Gate Bridge through the Marina and Presidio, using the existing native detail scale.
- Added both bridge towers, the continuous deck and projected bridge traffic, a strait passage and a western overflight.
- Harmonized distant water across all four appearances while retaining coastal textures and reflections.
- Updated the Bay Area outline and added 10 location jumps. See [verification](docs/VERIFICATION-v0.4.md).

## 0.3.0 — Waterfront corridor and Bay Area overview

- Extended continuous detailed navigation from Fisherman's Wharf to Mission Bay with 12 location jumps and four registered appearances.
- Added a terrain-based Bay Area overview, waterfront coverage outline, regional crossings and airport markers.
- Preserved clocks, controls and the last named waterfront location across view changes. Expanded mask/depth support and loaded only needed imagery.
- Added source records, atlas asset checks, real browser captures and [verification](docs/VERIFICATION-v0.3.md).

## 0.2.0 — Projected vehicles and wet waterfront

- Rebuilt vehicles in world metres through the city camera, added wet day/night art, retained Clear and Coastal Fog, and switched the current interface and documentation to English.
- See the [v0.2 verification record](docs/VERIFICATION-v0.2.md).

## 0.1.0 — living waterfront sample, 2026-11-10

- Added a continuous original day/night illustrated Ferry Building / Financial District / Embarcadero sample, 1536 × 1024, with two DZI pyramids.
- Added source-registered moving cars, two ferries, a cargo ship and an occasional aircraft; transport switches, speed and pause.
- Added authored day/night crossfades, local light overlays, an automatic day clock, and independent clear/cloudy/fog/rain controls.
- Added compact mobile controls, reduced-motion startup, source credits, recorded prompts and reproducible tile packaging.
- Passed core model invariants, production build, source water/route checks and actual desktop/mobile browser verification. See [verification](docs/VERIFICATION-v0.1.md) for practical limits.

## Unreleased — repository setup, 2026-11-10

- Defined San Francisco city and bay waterfront as the first map target.
- Documented the NYC/Vancouver illustrated-tile approach and its observed sources.
- Specified cars, boats, aircraft, authored day/night lighting and independent weather.
- Added a visual contract, coverage planning record, credits, roadmap and contribution templates.

The initial setup revision contained documentation only.
