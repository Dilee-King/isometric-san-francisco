import type { TileSourceOptions } from "openseadragon";
import type { RegionTileLayout, SceneData } from "./types.ts";

type RegionalSourceOptions = TileSourceOptions & {
  width: number;
  height: number;
  tileOverlap: number;
  getTileUrl(level: number, column: number, row: number): string;
};

export function regionForTile(
  layout: RegionTileLayout,
  width: number,
  height: number,
  level: number,
  column: number,
  row: number,
): string {
  if (level <= layout.sharedMaxLevel) return "overview";
  const divisor = 2 ** (layout.maxLevel - level);
  const levelWidth = Math.ceil(width / divisor);
  const levelHeight = Math.ceil(height / divisor);
  const left = column * layout.tileSize;
  const top = row * layout.tileSize;
  const right = Math.min(left + layout.tileSize, levelWidth);
  const bottom = Math.min(top + layout.tileSize, levelHeight);
  const x = ((left + right) / 2) * (width / levelWidth);
  const y = ((top + bottom) / 2) * (height / levelHeight);
  const region = layout.regions.find(({ bounds: [x0, y0, x1, y1] }) =>
    x >= x0 && x < x1 && y >= y0 && y < y1,
  );
  return region?.id ?? layout.fallback;
}

export function regionTileSource(
  data: Pick<SceneData, "width" | "height" | "tileLayout">,
  root: string,
  appearance: string,
): string | RegionalSourceOptions {
  const layout = data.tileLayout;
  if (!layout) return `${root}${appearance}.dzi`;
  return {
    width: data.width,
    height: data.height,
    tileSize: layout.tileSize,
    tileOverlap: layout.overlap,
    minLevel: 0,
    maxLevel: layout.maxLevel,
    getTileUrl(level, column, row) {
      const region = regionForTile(layout, data.width, data.height, level, column, row);
      return `${root}regions/${region}/${appearance}_files/${level}/${column}_${row}.webp`;
    },
  };
}
