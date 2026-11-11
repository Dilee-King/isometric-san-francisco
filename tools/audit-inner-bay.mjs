import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { project } from "../src/model.ts";
import { regionTileSource } from "../src/regionTiles.ts";

const root = "public/map";
const json = path => JSON.parse(readFileSync(path, "utf8"));
const sha = bytes => createHash("sha256").update(bytes).digest("hex");
const digest = path => sha(readFileSync(path));
const appearances = ["scene", "night", "rain-day", "rain-night"];
const shared = join(root, "inner-bay");
const common = json(join(shared, "manifest.json"));
const commonSHA = digest(join(shared, "manifest.json"));
const sourceSHA = digest("data/inner-bay/source.json.gz");
const prior = json(join(root, "v5/waterfront/scene.json"));

function auditedFiles(folder, manifest) {
  const entries = new Map();
  for (const file of manifest.files) {
    assert.ok(!entries.has(file.path), file.path);
    const content = readFileSync(join(folder, file.path));
    assert.equal(content.length, file.bytes, file.path);
    assert.equal(sha(content), file.sha256, file.path);
    entries.set(file.path, file.sha256);
  }
  return entries;
}

const sharedFiles = auditedFiles(shared, common);
const mask = readFileSync(join(shared, "masks.png"));
assert.equal(mask.subarray(1, 4).toString(), "PNG");
assert.deepEqual([mask.readUInt32BE(16), mask.readUInt32BE(20)], common.maskSize);
assert.equal(mask[25], 2, "Packed mask must use RGB with opaque surface bits");
let priorBlockCount = 0;
let priorPlaceCount = prior.landmarks.length;
const variantFiles = new Set();
for (const version of [6, 7, 8]) {
  const folder = join(root, `v${version}`);
  const atlas = json(join(folder, "atlas.json"));
  assert.equal(atlas.version, `0.${version}.0`);
  const city = json(join(folder, "waterfront/scene.json"));
  const cityManifest = json(join(folder, "waterfront/manifest.json"));
  const cityFiles = auditedFiles(join(folder, "waterfront"), cityManifest);
  const bay = json(join(folder, "bay/scene.json"));
  const bayManifest = json(join(folder, "bay/manifest.json"));
  auditedFiles(join(folder, "bay"), bayManifest);
  assert.equal(city.release, `inner-bay-v${version}`);
  assert.equal(bay.release, `bay-overview-v${version}`);
  assert.deepEqual([city.width, city.height], common.size);
  assert.deepEqual(city.maskSize, common.maskSize);
  assert.equal(city.maskBundle, "map/inner-bay/masks.png");
  assert.equal(cityManifest.sharedManifestSHA256, commonSHA);
  assert.equal(cityManifest.sourceSHA256, sourceSHA);
  assert.deepEqual(city.originUTM, prior.originUTM);
  assert.equal(city.projection.scale, prior.projection.scale);
  assert.deepEqual(city.projection.east, prior.projection.east);
  assert.deepEqual(city.projection.north, prior.projection.north);
  assert.deepEqual(city.routes.slice(0, prior.routes.length), prior.routes);
  const layout = city.tileLayout;
  const native = Object.entries(common.nativeBlocks).filter(([, [stage]]) => stage <= version);
  assert.deepEqual(layout.sparse.blocks, Object.fromEntries(native.map(([key, [, region]]) => [key, region])));
  const overrides = layout.sparse.appearanceOverrides ?? {};
  assert.deepEqual(overrides, common.appearanceOverrides?.[version] ?? {});
  assert.equal(Object.keys(overrides).length > 0, version < 8);
  assert.ok(native.length > priorBlockCount);
  assert.ok(city.landmarks.length > priorPlaceCount);
  priorBlockCount = native.length;
  priorPlaceCount = city.landmarks.length;
  assert.equal(new Set(city.routes.map(route => route.id)).size, city.routes.length);
  const crossing = city.routes.filter(route => route.id.startsWith("bay-bridge-"));
  assert.equal(crossing.length, 110);
  assert.ok(crossing.every(route => route.hiddenSegments.length >= 4 && route.points.length > 400));
  assert.equal(city.routes.some(route => route.id === "oakland-cargo"), version >= 7);
  assert.equal(city.routes.some(route => route.id === "sausalito-ferry-0"), version >= 8);
  for (const [name, proof] of Object.entries(cityManifest.vesselClearance)) {
    assert.ok(proof.minClearanceMetres > (name.includes("cargo") ? 33.35 : 16.14));
  }
  for (const art of cityManifest.artwork) {
    const image = readFileSync(art.path);
    assert.equal(sha(image), art.sha256);
    assert.deepEqual([image.readUInt32BE(16), image.readUInt32BE(20)], art.size);
  }

  let sharedTiles = 0, nativeTiles = 0, substitutedTiles = 0;
  for (const appearance of appearances) {
    const source = regionTileSource(city, "", appearance);
    for (let level = 0; level <= layout.maxLevel; level++) {
      const divisor = layout.tileSize * 2 ** (layout.maxLevel - level);
      for (let row = 0; row < Math.ceil(city.height / divisor); row++) {
        for (let column = 0; column < Math.ceil(city.width / divisor); column++) {
          if (!source.tileExists(level, column, row)) continue;
          const path = source.getTileUrl(level, column, row);
          if (level > layout.sharedMaxLevel) {
            const relative = path.replace(layout.sparse.root, "");
            assert.ok(sharedFiles.has(relative), path);
            const override = overrides[`${appearance}/${level}/${column}_${row}`];
            if (override) {
              const pixels = layout.tileSize * 2 ** (layout.maxLevel - level);
              const block = `${Math.floor(column * pixels / layout.sparse.blockSize)}_${Math.floor(row * pixels / layout.sparse.blockSize)}`;
              const normal = `regions/${layout.sparse.blocks[block]}/${appearance}_files/${level}/${column}_${row}.webp`;
              assert.ok(sharedFiles.has(normal), normal);
              assert.notEqual(sharedFiles.get(relative), sharedFiles.get(normal), relative);
              variantFiles.add(relative);
              substitutedTiles++;
            }
            nativeTiles++;
          } else {
            assert.ok(cityFiles.has(path), path);
            sharedTiles++;
          }
        }
      }
    }
    for (const place of city.landmarks) {
      const image = project(place.p, city.projection);
      assert.ok(source.tileExists(layout.maxLevel, Math.floor(image.x / layout.tileSize), Math.floor(image.y / layout.tileSize)), place.name);
    }
  }
  assert.equal(sharedTiles, cityManifest.tileCount);
  assert.equal(nativeTiles, native.length * 45 * 4);
  assert.equal(substitutedTiles, Object.keys(overrides).length);
  console.log(`v0.${version}: ${city.landmarks.length} places, ${native.length} detail blocks, ${nativeTiles} native and ${sharedTiles} backdrop tiles`);
}
assert.equal(common.tileCount, priorBlockCount * 45 * 4 + variantFiles.size);
console.log(`Inner Bay audit passed with ${priorBlockCount * 45 * 4} shared native tiles and ${variantFiles.size} early-release variants`);
