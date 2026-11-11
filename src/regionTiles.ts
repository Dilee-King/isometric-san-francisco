import type { TileSourceOptions } from "openseadragon";
import type { RegionTileLayout, SceneData } from "./types.ts";

type RegionalSourceOptions = TileSourceOptions & {
  width: number;
  height: number;
  tileOverlap: number;
  getTileUrl(level: number, column: number, row: number): string;
  tileExists?(level: number, column: number, row: number): boolean;
};

function sparseRegion(layout: RegionTileLayout, level: number, column: number, row: number) {
  const sparse = layout.sparse;
  if (!sparse) return undefined;
  const tileWidth = layout.tileSize * 2 ** (layout.maxLevel - level);
  const blockColumn = Math.floor(column * tileWidth / sparse.blockSize);
  const blockRow = Math.floor(row * tileWidth / sparse.blockSize);
  return sparse.blocks[`${blockColumn}_${blockRow}`];
}

export function regionForTile(
  layout: RegionTileLayout,
  width: number,
  height: number,
  level: number,
  column: number,
  row: number,
): string {
  if (level <= layout.sharedMaxLevel) return "overview";
  if (layout.detail && level > layout.detail.baseLevel)
    return layout.detail.tiles[`${level}/${column}_${row}`] ?? layout.fallback;
  if (layout.sparse) return sparseRegion(layout, level, column, row) ?? layout.fallback;
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
  data: Pick<SceneData, "width" | "height" | "tileLayout" | "appearanceRevision">,
  root: string,
  appearance: string,
): string | RegionalSourceOptions {
  const layout = data.tileLayout;
  if (!layout) return `${root}${appearance}.dzi`;
  const revision = data.appearanceRevision ? `?rev=${data.appearanceRevision}` : "";
  const backdropOverrides = new Set(layout.sparse?.backdropOverrides);
  return {
    width: data.width,
    height: data.height,
    tileSize: layout.tileSize,
    tileOverlap: layout.overlap,
    minLevel: 0,
    maxLevel: layout.maxLevel,
    ...(layout.sparse || layout.detail ? {
      tileExists(level: number, column: number, row: number) {
        const divisor = layout.tileSize * 2 ** (layout.maxLevel - level);
        if (level < 0 || level > layout.maxLevel || column < 0 || row < 0 ||
            column >= Math.ceil(data.width / divisor) || row >= Math.ceil(data.height / divisor)) return false;
        if (layout.detail)
          return level <= layout.detail.baseLevel || !!layout.detail.tiles[`${level}/${column}_${row}`];
        return level <= layout.sharedMaxLevel || !!sparseRegion(layout, level, column, row);
      },
    } : {}),
    getTileUrl(level, column, row) {
      const key = `${appearance}/${level}/${column}_${row}`;
      const region = layout.sparse?.appearanceOverrides?.[key]
        ?? regionForTile(layout, data.width, data.height, level, column, row);
      const tileRoot = level > layout.sharedMaxLevel ? layout.sparse?.root
        : backdropOverrides.has(key) ? undefined : layout.sparse?.backdropRoot;
      return `${root}${tileRoot ?? ""}regions/${region}/${appearance}_files/${level}/${column}_${row}.webp${revision}`;
    },
  };
}
