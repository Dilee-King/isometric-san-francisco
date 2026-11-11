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
