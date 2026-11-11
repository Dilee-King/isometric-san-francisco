import assert from "node:assert/strict";
import test from "node:test";
import { regionForTile, regionTileSource } from "./regionTiles.ts";
import type { RegionTileLayout } from "./types.ts";

const layout: RegionTileLayout = {
  tileSize: 512,
  overlap: 1,
  maxLevel: 14,
  sharedMaxLevel: 11,
  fallback: "context",
  regions: [
    { id: "west", bounds: [0, 0, 2048, 14408] },
    { id: "city-core", bounds: [2048, 0, 8192, 14408] },
  ],
};

test("wide views use the shared pyramid and closer views request a visible region", () => {
  assert.equal(regionForTile(layout, 12722, 14408, 11, 0, 0), "overview");
  assert.equal(regionForTile(layout, 12722, 14408, 14, 1, 3), "west");
  assert.equal(regionForTile(layout, 12722, 14408, 14, 5, 3), "city-core");
  assert.equal(regionForTile(layout, 12722, 14408, 14, 22, 3), "context");
});

test("the partial edge tile is routed using its clipped image bounds", () => {
  const edge = {
    ...layout,
    regions: [{ id: "edge", bounds: [12288, 0, 12520, 14408] as [number, number, number, number] }],
  };
  assert.equal(regionForTile(edge, 12722, 14408, 14, 24, 0), "edge");
});

test("appearance URLs retain one image geometry across regional boundaries", () => {
  const data = { width: 12722, height: 14408, tileLayout: layout };
  const day = regionTileSource(data, "/map/v5/waterfront/", "scene");
  const wet = regionTileSource(data, "/map/v5/waterfront/", "rain-night");
  assert.equal(typeof day, "object");
  assert.equal(typeof wet, "object");
  if (typeof day === "string" || typeof wet === "string") throw new Error("Expected regional sources");
  assert.equal(day.width, 12722);
  assert.equal(day.height, 14408);
  assert.equal(day.tileOverlap, 1);
  assert.equal(day.getTileUrl?.(14, 5, 3), "/map/v5/waterfront/regions/city-core/scene_files/14/5_3.webp");
  assert.equal(wet.getTileUrl?.(14, 5, 3), "/map/v5/waterfront/regions/city-core/rain-night_files/14/5_3.webp");
});

test("existing scene descriptors retain their DZI entry point", () => {
  assert.equal(
    regionTileSource({ width: 2560, height: 1792 }, "/map/v4/bay/", "night"),
    "/map/v4/bay/night.dzi",
  );
});

test("sparse atlases keep lower levels and request native tiles only inside active blocks", () => {
  const tileLayout = {
    ...layout, maxLevel: 16, sharedMaxLevel: 14,
    sparse: { root: "../../inner-bay/", blockSize: 3072, blocks: { "4_2": "west-city" },
      appearanceOverrides: { "scene/16/25_12": "through-v6" } },
  };
  const source = regionTileSource({ width: 55296, height: 30720, tileLayout }, "/map/v6/waterfront/", "scene");
  if (typeof source === "string") throw new Error("Expected sparse source");
  assert.equal(source.tileExists?.(16, 24, 12), true);
  assert.equal(source.tileExists?.(15, 14, 8), true);
  assert.equal(source.tileExists?.(16, 30, 12), false);
  assert.equal(source.tileExists?.(14, 7, 3), true);
  assert.equal(source.tileExists?.(14, -1, 3), false);
  assert.equal(source.getTileUrl(16, 24, 12), "/map/v6/waterfront/../../inner-bay/regions/west-city/scene_files/16/24_12.webp");
  assert.equal(source.getTileUrl(16, 25, 12), "/map/v6/waterfront/../../inner-bay/regions/through-v6/scene_files/16/25_12.webp");
  assert.equal(source.getTileUrl(14, 7, 3), "/map/v6/waterfront/regions/overview/scene_files/14/7_3.webp");
});

test("cumulative releases share matching backdrops and keep different tiles", () => {
  const tileLayout = {
    ...layout,
    sparse: {
      root: "../../illustrated-bay/",
      blockSize: 3072,
      blocks: {},
      backdropRoot: "../../v8-art/waterfront/",
      backdropOverrides: ["night/11/1_1"],
    },
  };
  const source = regionTileSource({ width: 12000, height: 9000, tileLayout }, "/map/v6-art/waterfront/", "night");
  if (typeof source === "string") throw new Error("Expected regional source");
  assert.equal(source.getTileUrl(11, 0, 0), "/map/v6-art/waterfront/../../v8-art/waterfront/regions/overview/night_files/11/0_0.webp");
  assert.equal(source.getTileUrl(11, 1, 1), "/map/v6-art/waterfront/regions/overview/night_files/11/1_1.webp");
});

test("full Bay reads the continuous regional pyramid and only registered close-up tiles", () => {
  const tileLayout = {
    ...layout, maxLevel: 16,
    detail: { baseLevel: 13, tiles: { "16/24_12": "detail-sfo", "15/12_6": "detail-sfo" } },
  };
  const source = regionTileSource({
    width: 40960, height: 28672, tileLayout, appearanceRevision: "v9-revision",
  }, "/map/v9-art/bay/", "rain-night");
  if (typeof source === "string") throw new Error("Expected regional source");
  assert.equal(source.tileExists?.(13, 9, 6), true);
  assert.equal(source.tileExists?.(13, 10, 6), false);
  assert.equal(source.tileExists?.(16, 24, 12), true);
  assert.equal(source.tileExists?.(16, 25, 12), false);
  assert.equal(source.getTileUrl(16, 24, 12),
    "/map/v9-art/bay/regions/detail-sfo/rain-night_files/16/24_12.webp?rev=v9-revision");
});

test("native overlays request no tiles below their starting level or outside their footprint", () => {
  const tileLayout = {
    ...layout, minLevel: 14, maxLevel: 19, sharedMaxLevel: 0, regions: [],
    detail: { baseLevel: 0, tiles: { "14/2_1": "sfo", "19/79_55": "sfo" } },
  };
  const source = regionTileSource({ width: 282624, height: 196608, tileLayout }, "/detail/", "night");
  if (typeof source === "string") throw new Error("Expected sparse overlay source");
  assert.equal(source.minLevel, 14);
  assert.equal(source.tileExists?.(0, 0, 0), false);
  assert.equal(source.tileExists?.(14, 2, 1), true);
  assert.equal(source.tileExists?.(19, 79, 55), true);
  assert.equal(source.tileExists?.(19, 80, 55), false);
  assert.equal(source.getTileUrl(19, 79, 55), "/detail/regions/sfo/night_files/19/79_55.webp");
});
