import OpenSeadragon from "openseadragon";
import { sceneRoot } from "./assets.ts";
import { regionTileSource } from "./regionTiles.ts";
import type { DetailLayer, ImageBounds, SceneData } from "./types.ts";

const appearances = ["scene", "night", "rain-day", "rain-night"] as const;
const maxScreenPixelsPerSourcePixel = 1.25;

type Layer = {
  source: DetailLayer;
  x: number;
  y: number;
  width: number;
  bounds: ImageBounds[];
  images: OpenSeadragon.TiledImage[];
};

function contains([x0, y0, x1, y1]: ImageBounds, p: OpenSeadragon.Point) {
  return p.x >= x0 && p.y >= y0 && p.x <= x1 && p.y <= y1;
}

function intersects([x0, y0, x1, y1]: ImageBounds, view: OpenSeadragon.Rect) {
  return x1 > view.x && x0 < view.x + view.width && y1 > view.y && y0 < view.y + view.height;
}

export class RegisteredDetails {
  readonly layers: Layer[];
  private readonly viewer: OpenSeadragon.Viewer;
  private readonly base: SceneData;
  private readonly mediumBounds: ImageBounds[];
  private readonly overviewScale: number;
  private panEnded = false;

  constructor(
    viewer: OpenSeadragon.Viewer,
    base: SceneData,
    config: NonNullable<SceneData["nativeDetail"]>,
  ) {
    this.viewer = viewer;
    this.base = base;
    const layout = base.tileLayout!;
    this.overviewScale = base.projection.scale / 2 ** (layout.maxLevel - layout.detail!.baseLevel);
    this.mediumBounds = config.regionalBounds.map(bounds => bounds.map(x => x / base.width) as ImageBounds);
    this.layers = config.layers.map(source => {
      // Express each native layer in the base image's viewport coordinates.
      const ratio = base.projection.scale / source.projection.scale;
      const x = (base.projection.origin[0] - source.projection.origin[0] * ratio) / base.width;
      const y = (base.projection.origin[1] - source.projection.origin[1] * ratio) / base.width;
      const scale = ratio / base.width;
      return {
        source, x, y, width: source.width * scale, images: [],
        bounds: source.bounds.map(([x0, y0, x1, y1]) => [
          x + x0 * scale, y + y0 * scale, x + x1 * scale, y + y1 * scale,
        ]),
      };
    });
    const limitAtPixel = (pixel: OpenSeadragon.Point) => {
      const viewport = this.viewer.viewport;
      this.limitZoom(viewport.pointFromPixel(pixel, true), viewport.getZoom(true));
    };
    viewer.addHandler("canvas-scroll", event => limitAtPixel(event.position));
    viewer.addHandler("canvas-double-click", event => limitAtPixel(event.position));
    viewer.addHandler("canvas-pinch", event => limitAtPixel(event.center));
    viewer.addHandler("canvas-drag-end", () => {
      this.panEnded = true;
      this.constrainAtCentre();
    });
    viewer.addHandler("animation-finish", () => {
      if (!this.panEnded) return;
      this.panEnded = false;
      this.constrainAtCentre();
    });
    viewer.addHandler("resize", () => this.constrainAtCentre());
  }

  async load() {
    for (const layer of this.layers) {
      for (const appearance of appearances) {
        if (!this.viewer.isOpen()) return;
        const image = await new Promise<OpenSeadragon.TiledImage>((resolve, reject) =>
          this.viewer.addTiledImage({
            tileSource: regionTileSource(layer.source, sceneRoot(layer.source), appearance),
            x: layer.x, y: layer.y, width: layer.width, opacity: 0, preload: false,
            success: event => resolve((event as unknown as { item: OpenSeadragon.TiledImage }).item),
            error: () => reject(new Error("Detailed map layer could not open")),
          }));
        if (layer.source.crop) {
          const clipped = image as OpenSeadragon.TiledImage & {
            setCroppingPolygons(polygons: OpenSeadragon.Point[][]): void;
          };
          clipped.setCroppingPolygons(layer.source.crop.map(ring =>
            ring.map(([x, y]) => new OpenSeadragon.Point(x, y))));
        }
        layer.images.push(image);
      }
    }
    this.limitZoom();
  }

  limitZoom(point = this.viewer.viewport.getCenter(), currentZoom = 0) {
    const viewport = this.viewer.viewport as OpenSeadragon.Viewport & { maxZoomLevel: number };
    let density = this.mediumBounds.some(bounds => contains(bounds, point))
      ? this.base.projection.scale : this.overviewScale;
    for (const layer of this.layers) {
      if (layer.bounds.some(bounds => contains(bounds, point)))
        density = Math.max(density, layer.source.projection.scale);
    }
    const width = Math.max(1, viewport.getContainerSize().x);
    const sourceLimit = maxScreenPixelsPerSourcePixel * density *
      this.base.width / (width * this.base.projection.scale);
    viewport.maxZoomLevel = Math.max(sourceLimit, currentZoom);
  }

  private constrainAtCentre() {
    if (!this.viewer.viewport) return;
    this.limitZoom();
    this.viewer.viewport.applyConstraints();
  }

  update(pixelsPerMetre: number, night: number, wet: boolean) {
    const view = this.viewer.viewport.getBounds(true);
    for (const layer of this.layers) {
      const [from, to] = layer.source.revealScale;
      const alpha = pixelsPerMetre > from && layer.bounds.some(bounds => intersects(bounds, view))
        ? Math.min(1, (pixelsPerMetre - from) / (to - from)) : 0;
      const [day, dark, rainDay, rainNight] = layer.images;
      day?.setOpacity(wet || night === 1 ? 0 : alpha);
      dark?.setOpacity(wet ? 0 : alpha * night);
      rainDay?.setOpacity(wet && night < 1 ? alpha : 0);
      rainNight?.setOpacity(wet ? alpha * night : 0);
    }
  }
}
