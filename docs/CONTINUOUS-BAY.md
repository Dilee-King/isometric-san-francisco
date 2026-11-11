# Continuous Bay street detail

The target is continuous illustration at 1.854545 source pixels per metre across the existing Bay Area map extent. Coverage includes the streets between place jumps, the terrain and shoreline, and a shared native-scale water texture. The place menu serves navigation within that artwork.

Isometric NYC uses adjacent masked infill and a WebP image pyramid. Isometric Vancouver redraws adjacent areas on one fixed camera, repairs their seams and serves visible tiles from indexed regional AVIF packs with byte-range requests. Its coverage file reports the extent already drawn. [NYC production notes](https://cannoneyed.com/projects/isometric-nyc) · [Vancouver viewer](https://vancouver.isoworld.xyz/) · [Vancouver coverage](https://vancouver.isoworld.xyz/coverage.json)

## East Bay preview

The first infill connects the Oakland north waterfront with Emeryville Marina, the I-80 interchange, Berkeley Aquatic Park and the existing Berkeley Marina artwork. The preview covers 10.02 square kilometres, including water and retained coverage. Six planning frames use existing City tiles, and 16 new ImageGen panels overlap on the original 39° orthographic grid. The same regional pack serves day, night, rain by day and rain by night. The v0.5 water texture continues through the new panels, with a transition into the painted shoreline.

The drawing guides combine USDA NAIP aerial windows with completed artwork at the edges. The frame plan, selected PNGs, prompts and source checksums are recorded with the art. [Frame and artwork sources](../assets/continuous-bay/) · [Tile coverage](../public/map/v10-continuous/coverage.json) · [Tile manifest](../public/map/v10-continuous/detail/manifest.json)

## Build and inspect

```powershell
python tools/package_continuous_bay.py
npm run dev
```

Open `http://127.0.0.1:5186/?v=0.10.0-preview&p=emeryville-marina`. The browser check drags the camera along the waterfront at a fixed close zoom and verifies the native tiles at each stop. The 1440 × 960 viewport was fully inside the native coverage at all 411 sampled positions along that path. [Browser recording](screenshots/v0.10.0-preview/east-bay-drag.mp4) · [Browser check](../tools/qa-continuous-bay.js)

Generate guide windows with `python tools/continuous_bay_guides.py --cutout`, then use `--context --wave 1` for the first overlapping group. Add reviewed ImageGen output and its prompt to the artwork directory before preparing the following wave. The original day artwork determines the shoreline transition consistently across appearances.

## Coverage audit

The coverage planner divides the current atlas into 61,965 native-scale cells. Using the regional land mask, 42,539 touch land or shoreline. The current preview and retained native layers completely cover 627 of those land or shoreline cells. The remaining 41,912 cells require further artwork and 19,096 offshore cells require water coverage. The planner checks each core cell against the union of the native layers and accounts for the tapered image edges. These counts are coverage estimates at the stated grid size.

```powershell
python tools/plan_continuous_bay.py --scene public/map/v10-continuous/bay/scene.json --queue .local/continuous-bay/bay-land-queue.jsonl.gz
```
