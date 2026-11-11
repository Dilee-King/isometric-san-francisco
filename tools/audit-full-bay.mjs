import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { regionTileSource } from "../src/regionTiles.ts";

const root = process.argv[2] ?? "public/map/v9-art/bay";
const json = path => JSON.parse(readFileSync(join(root, path), "utf8"));
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const scene = json("scene.json"), manifest = json("manifest.json");
const appearances = ["scene", "night", "rain-day", "rain-night"];
const { tileSize, maxLevel, detail } = scene.tileLayout;
const { baseLevel, tiles } = detail;
const regional = manifest.artwork.filter(row => row.kind === "regional");
const local = manifest.artwork.filter(row => row.kind === "detail");
assert.equal(scene.release, "full-bay-v9");
assert.equal(scene.appearanceRevision, manifest.revision);
assert.deepEqual(scene.projection, manifest.projection);
assert.deepEqual(scene.projection.east, [.8, .6]);
assert.deepEqual(scene.projection.north, [.6, -.8]);
assert.equal(regional.length, 16);
assert.equal(local.length, 16);
assert.equal(manifest.weatherArtwork.length, 4);
assert.deepEqual(manifest.aerialGuides, JSON.parse(readFileSync("assets/full-bay/aerial-guide-sha256.json", "utf8")));
assert.equal(Object.keys(manifest.aerialGuides).length, local.length);
assert.equal(scene.landmarks.filter(mark => mark.detail).length, local.length);
assert.equal(new Set(scene.landmarks.map(mark => mark.id)).size, scene.landmarks.length);
assert.ok(scene.routes.some(route => route.kind === "car"));
assert.ok(scene.routes.some(route => route.kind === "ferry" && route.id === "bay-vessel-san-pablo"));
assert.ok(scene.routes.some(route => route.kind === "cargo"));
assert.equal(scene.routes.filter(route => route.id.startsWith("bay-flight-")).length, 3);

const files = new Map();
for (const file of manifest.files) {
  assert.ok(!files.has(file.path), `duplicate file ${file.path}`);
  const bytes = readFileSync(join(root, file.path));
  assert.equal(bytes.length, file.bytes, file.path);
  assert.equal(hash(bytes), file.sha256, file.path);
  files.set(file.path, file);
}
assert.equal(manifest.tileCount, files.size - 1);
assert.equal(manifest.bytes, manifest.files.reduce((sum, file) => sum + file.bytes, 0));
const mask = readFileSync(join(root, "masks.png"));
assert.deepEqual([mask.readUInt32BE(16), mask.readUInt32BE(20)], scene.maskSize);

for (const row of [...manifest.artwork, ...manifest.weatherArtwork]) {
  const stem = row.id + (row.appearance ? `-${row.appearance}` : "");
  const artwork = readFileSync(`assets/full-bay/plates/${stem}.png`);
  assert.deepEqual([artwork.readUInt32BE(16), artwork.readUInt32BE(20)], [1536, 1024], stem);
  assert.equal(hash(artwork), row.sha256, stem);
  assert.ok(readFileSync(`assets/full-bay/plates/${stem}.prompt.txt`, "utf8").trim());
}
const referenced = new Set(["masks.png"]);
for (const appearance of appearances) {
  const source = regionTileSource(scene, "", appearance);
  const check = (level, col, row) => {
    assert.ok(source.tileExists(level, col, row));
    const path = source.getTileUrl(level, col, row).split("?")[0];
    assert.ok(files.has(path), path);
    referenced.add(path);
  };
  for (let level = 0; level <= baseLevel; level++) {
    const span = tileSize * 2 ** (maxLevel - level);
    for (let row = 0; row < Math.ceil(scene.height / span); row++) {
      for (let col = 0; col < Math.ceil(scene.width / span); col++) check(level, col, row);
    }
  }
  for (const key of Object.keys(tiles)) {
    const [level, col, row] = key.split(/[/_]/).map(Number);
    assert.ok(level > baseLevel && level <= maxLevel);
    check(level, col, row);
  }
}
assert.equal(referenced.size, files.size);
console.log(`Full Bay verified: ${regional.length} continuous plates, ${local.length} closer views, ${scene.landmarks.length} places, ${manifest.tileCount} tiles, ${manifest.bytes.toLocaleString()} bytes.`);
