# Reference audit — 2026-11-10

These are observed public sources and explicit implementation inferences. A technology named by a reference is not evidence that this project has implemented it.

## Isometric NYC

- [Author's process article](https://cannoneyed.com/projects/isometric-nyc): orthographic source rendering; illustrated tile generation; adjacent masked infill; human correction for water, trees and seams. The article also describes a SQLite-backed generation workflow and substantial manual review.
- [Public source](https://github.com/cannoneyed/isometric-nyc), observed main revision `008446357ec67512c4329d25edefb6c508c7b24d`.
- [App documentation at the observed revision](https://github.com/cannoneyed/isometric-nyc/blob/008446357ec67512c4329d25edefb6c508c7b24d/docs/app.md): React/TypeScript/Vite/OpenSeadragon, DZI descriptors and image pyramids.
- [License](https://github.com/cannoneyed/isometric-nyc/blob/008446357ec67512c4329d25edefb6c508c7b24d/LICENSE): MIT, copyright Andy Coenen, 2025. Carry the notice when copying substantive code. No upstream code is copied into this documentation-only revision.

## Isometric Vancouver

- [Live site](https://vancouver.isoworld.xyz/), including How it's made and Data & credits, retrieved directly because the search reader could not open it.
- The published explanation describes one fixed isometric camera, structure-guided image drawing, multiple drawing models across areas and subsequent seam repair. Streets support illustrative traffic, including lanes and signals.
- Current page module comments and its renderer identify WebGL2 textured tiles and a traffic worker (`traffic-worker.js`). The live page retains [a classic OpenSeadragon viewer](https://vancouver.isoworld.xyz/classic.html).
- The page credits [borodutch's viewer](https://github.com/backmeupplz/vancouver) as an ancestor of the illustrated renderer. That repository is a separate code-rendered Vancouver project, not proof that isoworld's complete generation service, illustrated assets or model weights are open source.
- Observed ancestor repository main revision: `b0126e51aa98621295a16390a5b1295d975992b2`. Its GitHub API license field was null; the live site's reference to `public/illustrated.js` was not present at that revision. Review per-file permission before copying code. This project has copied no code from it in the setup revision.

## Project decisions inferred from those sources

Use NYC's clearly documented viewer/data pipeline as the baseline and Vancouver's shared-transform WebGL/worker organization as a performance reference. Add locally produced SF artwork, transport state, emission/occlusion/water masks and independent hour/weather control.

Both references use source 3D views during artwork production; an illustrated 2D viewer does not require an interactive 3D city. Complete SF source access, tile art, new dynamic masks and environment behavior remain to be produced and verified.

The article's model names, training choices, service costs and throughput are historical accounts. They are not requirements, estimates or claims for this project.
