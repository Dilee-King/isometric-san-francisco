import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { join, normalize } from "node:path";
import { regionTileSource } from "../src/regionTiles.ts";

const publicRoot = "public";
const nativeRoot = join(publicRoot, "map/v9-native");
const read = path => JSON.parse(readFileSync(path, "utf8"));
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const city = read(join(publicRoot, "map/v8-art/waterfront/scene.json"));
const regional = read(join(publicRoot, "map/v9-art/bay/scene.json"));
const scene = read(join(nativeRoot, "bay/scene.json"));
const manifest = read(join(nativeRoot, "detail/manifest.json"));
const [retained, native] = scene.nativeDetail.layers;
const appearances = ["scene", "night", "rain-day", "rain-night"];

assert.equal(scene.release, "full-bay-native-v9");
for (const key of ["assetRoot", "width", "height", "projection", "appearanceRevision", "tileLayout", "maskBundle", "routes"])
  assert.deepEqual(scene[key], regional[key], key);

for (const key of ["width", "height", "assetRoot", "projection", "appearanceRevision"])
  assert.deepEqual(retained[key], city[key], key);
const { minLevel, ...retainedLayout } = retained.tileLayout;
assert.ok(minLevel <= retainedLayout.sharedMaxLevel);
assert.deepEqual(retainedLayout, city.tileLayout);

const blocks = Object.keys(city.tileLayout.sparse.blocks);
assert.equal(blocks.length, 97);
assert.equal(retained.bounds.length, blocks.length);
assert.ok(retained.crop.length > 0);
assert.equal(native.projection.scale, retained.projection.scale);
const v5 = read(join(publicRoot, "map/v5/waterfront/scene.json"));
assert.equal(native.projection.scale, v5.projection.scale, "Original v0.5 artwork scale");
for (const key of ["east", "north", "sinElevation", "cosElevation"])
  assert.deepEqual(native.projection[key], scene.projection[key], key);

const landmarks = new Map(scene.landmarks.map(mark => [mark.id, mark]));
assert.equal(landmarks.size, scene.landmarks.length, "Duplicate jump identifier");
const scaleRatio = scene.projection.scale / retained.projection.scale;
for (const original of city.landmarks) {
  const mark = landmarks.get(original.id);
  assert.deepEqual(mark.p, original.p);
  assert.ok(mark.cityDetail);
  assert.equal(mark.viewHeight, (original.viewHeight ?? 1080) * scaleRatio);
  assert.equal(mark.viewWidth, (original.viewWidth ?? 0) * scaleRatio);
}
const tileSpan = retained.tileLayout.sparse.blockSize / retained.tileLayout.tileSize;
for (const appearance of appearances) {
  const original = regionTileSource(city, city.assetRoot, appearance);
  const reused = regionTileSource(retained, retained.assetRoot, appearance);
  for (const key of blocks) {
    const [col, row] = key.split("_").map(value => Number(value) * tileSpan);
    const level = retained.tileLayout.maxLevel;
    const url = reused.getTileUrl(level, col, row);
    assert.equal(url, original.getTileUrl(level, col, row), "Native City tile must be reused byte-for-byte");
    assert.ok(existsSync(normalize(join(publicRoot, url.split("?")[0]))), url);
  }
}

const guides = read("assets/native-bay/aerial-guide-sha256.json");
assert.deepEqual(manifest.aerialGuides, guides);
const closeups = manifest.artwork;
assert.equal(closeups.length, 16);
assert.deepEqual(Object.keys(guides).sort(), closeups.map(row => row.id).sort());
assert.equal(native.bounds.length, closeups.length);
for (const [index, { id, frame: [x, y, w, h], p }] of closeups.entries()) {
  assert.match(guides[id], /^[0-9a-f]{64}$/);
  assert.deepEqual([w, h], [1536, 1024]);
  assert.deepEqual(native.bounds[index], [x, y, x + w, y + h]);
  assert.ok(x >= 0 && y >= 0 && x + w <= native.width && y + h <= native.height);
  const mark = landmarks.get(id);
  assert.deepEqual(mark.p, p);
  assert.ok(mark.detail && !mark.cityDetail);
  const camera = native.projection;
  const u = camera.east[0] * p[0] + camera.north[0] * p[1];
  const v = (camera.east[1] * p[0] + camera.north[1] * p[1]) * camera.sinElevation - p[2] * camera.cosElevation;
  assert.ok(Math.abs(camera.origin[0] + camera.scale * u - x - w / 2) < 1e-6, id);
  assert.ok(Math.abs(camera.origin[1] + camera.scale * v - y - h / 2) < 1e-6, id);
}
for (const plate of [...closeups, ...manifest.weather]) {
  const stem = plate.id + (plate.appearance ? "-" + plate.appearance : "");
  const png = readFileSync("assets/native-bay/plates/" + stem + ".png");
  assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], [1536, 1024], stem);
  assert.equal(hash(png), plate.sha256, stem);
  assert.ok(readFileSync("assets/native-bay/plates/" + stem + ".prompt.txt", "utf8").trim());
}

assert.equal(native.appearanceRevision, manifest.revision);
assert.equal(hash(manifest.files.map(file => file.sha256).join("")).slice(0, 12), manifest.revision);
const files = new Map(manifest.files.map(file => [file.path, file]));
assert.equal(files.size, manifest.files.length);
const { tileLayout } = native;
for (const appearance of appearances) {
  const source = regionTileSource(native, "", appearance);
  for (const key of Object.keys(tileLayout.detail.tiles)) {
    const [level, col, row] = key.split(/[/_]/).map(Number);
    assert.ok(source.tileExists(level, col, row), key);
    assert.ok(!source.tileExists(tileLayout.minLevel - 1, col, row));
    const path = source.getTileUrl(level, col, row).split("?")[0];
    const file = files.get(path);
    assert.ok(file, path);
    const bytes = readFileSync(join(nativeRoot, "detail", path));
    assert.equal(bytes.length, file.bytes, path);
    assert.equal(hash(bytes), file.sha256, path);
    files.delete(path);
  }
}
assert.equal(files.size, 0, "Unreferenced detail tiles");
console.log("Native Bay verified. " + blocks.length + " retained City blocks, " + closeups.length +
  " ImageGen close-ups, " + manifest.files.length + " new appearance tiles and " + landmarks.size + " place jumps.");
