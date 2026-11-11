import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { regionForTile } from "../src/regionTiles.ts";

const root = "public/map/v5";
const json = (path) => JSON.parse(readFileSync(path, "utf8"));
const hash = (data) => createHash("sha256").update(data).digest("hex");
const atlas = json(join(root, "atlas.json"));
assert.equal(atlas.version, json("package.json").version);
assert.equal(atlas.defaultScene, "waterfront");
let totalTiles = 0;

for (const entry of atlas.scenes) {
  const directory = join(root, entry.id);
  const scene = json(join(root, entry.path));
  const manifest = json(join(root, entry.manifest));
  assert.equal(scene.release, entry.release);
  assert.deepEqual([scene.width, scene.height], entry.size);
  assert.deepEqual(scene.originUTM, [553326.4257226175, 4183298.4609667137]);
  assert.equal(scene.crs, "EPSG:32610");
  assert.deepEqual(scene.maskSize, manifest.maskSize);
  const paths = new Set();
  for (const file of manifest.files) {
    assert.ok(!paths.has(file.path), "Duplicate runtime file " + file.path);
    paths.add(file.path);
    const bytes = readFileSync(join(directory, file.path));
    assert.equal(bytes.length, file.bytes, file.path);
    assert.equal(hash(bytes), file.sha256, file.path);
  }
  for (const name of ["depth", "water", "hard"]) {
    const bytes = readFileSync(join(directory, name + ".png"));
    assert.equal(bytes.subarray(1, 4).toString(), "PNG");
    assert.deepEqual([bytes.readUInt32BE(16), bytes.readUInt32BE(20)], scene.maskSize);
  }
  const maximumLevel = Math.ceil(Math.log2(Math.max(scene.width, scene.height)));
  const appearances = ["scene", "night", "rain-day", "rain-night"];
  const regions = new Set();
  let expected = 0;
  for (const appearance of appearances) {
    for (let level = 0; level <= maximumLevel; level++) {
      const divisor = 512 * 2 ** (maximumLevel - level);
      for (let row = 0; row < Math.ceil(scene.height / divisor); row++) {
        for (let column = 0; column < Math.ceil(scene.width / divisor); column++) {
          const region = scene.tileLayout
            ? regionForTile(scene.tileLayout, scene.width, scene.height, level, column, row)
            : undefined;
          const prefix = region ? "regions/" + region + "/" : "";
          const path = prefix + appearance + "_files/" + level + "/" + column + "_" + row + ".webp";
          assert.ok(paths.has(path), "Missing tile " + path);
          if (region) regions.add(region);
          expected++;
        }
      }
    }
  }
  assert.equal(expected, manifest.tileCount);
  assert.equal(expected, entry.tileCount);
  if (scene.tileLayout) {
    assert.deepEqual(manifest.tileLayout, scene.tileLayout);
    assert.ok(regions.has("city-core") && regions.has("golden-gate") && regions.has("overview"));
    assert.equal(scene.landmarks.length, 30);
    assert.equal(scene.detailFrames.length, 28);
    assert.ok(scene.routes.filter((route) => route.id.startsWith("core-")).length >= 80);
    assert.ok(scene.routes.some(route => route.id === "core-overflight" && route.kind === "plane"), "Missing the city overflight");
    assert.equal(new Set(scene.routes.map(route => route.id)).size, scene.routes.length);
    assert.equal(hash(readFileSync("data/city-core/source.json.gz")), manifest.coreSourceSHA256);
    assert.equal(hash(readFileSync("public/map/v4/waterfront/manifest.json")), manifest.baseManifestSHA256);
    for (const art of manifest.artwork) {
      const bytes = readFileSync(art.path);
      assert.equal(hash(bytes), art.sha256, art.path);
      assert.deepEqual(art.size, [1536, 1024]);
    }
    for (const region of regions) {
      const local = json(join(directory, "regions", region, "manifest.json"));
      assert.equal(local.id, region);
      assert.ok(local.files.length > 0);
      assert.deepEqual(local.files, manifest.files.filter(file => file.path.startsWith("regions/" + region + "/")));
    }
    const old = json("public/map/v4/waterfront/scene.json");
    assert.deepEqual(scene.routes.slice(0, old.routes.length), old.routes);
    assert.deepEqual(scene.projection, old.projection);
  }
  console.log(entry.id + ": " + expected + " tiles, " + manifest.files.length + " files, " + regions.size + " regional packs");
  totalTiles += expected;
}
console.log("City-core audit passed: " + totalTiles + " tiles");
