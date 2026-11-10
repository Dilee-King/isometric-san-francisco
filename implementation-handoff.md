# Implementation handoff

Current handoff: design/repository setup only. No application code, generated tiles, paid infrastructure or production deployment has been created in this revision.

Read, in order: [project design](docs/project-design.md), [reference audit](docs/reference-audit.md), [DESIGN](DESIGN.md), [coverage plan](data/coverage-plan.json), [asset rules](assets/README.md).

Use the selected illustrated-tile approach. Start from the NYC MIT viewer patterns; preserve any notices for code actually reused. Use React/TypeScript/Vite, OpenSeadragon and DZI; add a synchronized WebGL2 effects layer and worker simulation. Freeze one orthographic camera and one world-to-image transform during calibration. Never route runtime traffic in screen coordinates.

The first artifact must prove a contiguous, finely drawn Ferry Building / Financial District / Embarcadero sample, with image-space/ground-space control points and visible depth correctness. No city-wide generation before this sample is approved for quality. Keep project status precise if only a test sample exists.

Produce clean tile backgrounds plus registered structural/occlusion/water/emission masks. Align day/twilight/night art. Avoid copying the previous free-orbit SF prototype into the product; it may supply reviewed geographic inputs or offline render tooling.

Apply DESIGN's charcoal panels, amber active control, 44 px touch targets, offline type stack and 390 px layout. Keep the map dominant. Include all three transport modes, independent environment controls, global pause, reduced motion and credits.

Record exact image prompts, model/settings, tile lineage, control-point residuals, manual seam fixes, source rights and output hashes. Keep secrets/raw data out of Git. Before the first code implementation, turn the reviewed design into an executable plan; this document does not claim that implementation has begun.
