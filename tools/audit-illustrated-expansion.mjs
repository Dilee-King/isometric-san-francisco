import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { project } from "../src/model.ts";
import { regionTileSource } from "../src/regionTiles.ts";

const root = process.argv[2] ?? "public/map";
const assetRoot = "assets/illustrated-expansion";
const json = path => JSON.parse(readFileSync(path, "utf8"));
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
const layout = json(join(assetRoot, "layout.json"));
const shared = join(root, "illustrated-bay");
const common = json(join(shared, "manifest.json"));
const original = json("public/map/v5/waterfront/scene.json");
const appearances = ["scene", "night", "rain-day", "rain-night"];

function files(folder, manifest) {
  const found = new Map();
  for (const file of manifest.files) {
    assert.ok(!found.has(file.path), file.path);
    const bytes = readFileSync(join(folder, file.path));
    assert.equal(bytes.length, file.bytes, file.path);
    assert.equal(digest(bytes), file.sha256, file.path);
    found.set(file.path, file.sha256);
  }
  return found;
}

assert.equal(common.artwork, layout.frames.length, "Incomplete ImageGen layout");
assert.equal(common.layoutSHA256, digest(readFileSync(join(assetRoot, "layout.json"))));
const southern = readFileSync(join(assetRoot, "plates/southern-context.png"));
assert.equal(common.southernContextSHA256, digest(southern));
assert.deepEqual([southern.readUInt32BE(16), southern.readUInt32BE(20)], [1536, 1024]);
assert.ok(readFileSync(join(assetRoot, "plates/southern-context.prompt.txt"), "utf8").trim().length > 100);
const originalArt = new Map();
for (const frame of layout.frames) {
  const path = join(assetRoot, "plates", frame.id);
  const bytes = readFileSync(path + ".png");
  assert.deepEqual([bytes.readUInt32BE(16), bytes.readUInt32BE(20)], [1536, 1024], frame.id);
  assert.ok(readFileSync(path + ".prompt.txt", "utf8").trim().length > 100, frame.id);
  assert.ok(!originalArt.has(frame.id), frame.id);
  originalArt.set(frame.id, digest(bytes));
}
const commonFiles = files(shared, common);
const latest = json(join(root, "v8-art/waterfront/manifest.json"));
const latestBackdrop = new Set(latest.files.filter(file => file.path.startsWith("regions/overview/")).map(file => file.path));
const mask = readFileSync(join(shared, "masks.png"));
assert.deepEqual([mask.readUInt32BE(16), mask.readUInt32BE(20)], [4608, 2560]);
assert.equal(mask[25], 2, "Packed mask must be RGB");
const sharedSHA = digest(readFileSync(join(shared, "manifest.json")));
const weatherHash = createHash("sha256").update(Buffer.from(sharedSHA, "hex"));
for (const stage of [6, 7, 8]) {
  const manifest = json(join(root, `v${stage}-art/waterfront/manifest.json`));
  for (const file of manifest.files) {
    if (/^regions\/overview\/(night|rain-day|rain-night)_files\//.test(file.path)) {
      weatherHash.update(Buffer.from(file.sha256, "hex"));
    }
  }
}
const weatherRevision = weatherHash.digest("hex").slice(0, 12);
let earlierRoutes = original.routes;
let earlierPlaces = original.landmarks.length;
const allVariants = new Set();
const physicalRoute = ({ hiddenSegments, ...route }) => route;
const authoredAppearances = {
  night: ["-dry-night", ["civic-center", "jack-london", "sausalito"]],
  "rain-day": ["-rain-day", ["civic-center", "jack-london", "sausalito"]],
  "rain-night": ["-night", ["bay-bridge-east", "civic-center", "jack-london", "sausalito", "bayview"]],
};
const weatherArt = new Map(common.weatherArtwork.map(row => [`${row.id}/${row.appearance}`, row.sha256]));
assert.equal(weatherArt.size, 11);
for (const [appearance, [suffix, ids]] of Object.entries(authoredAppearances)) {
  for (const id of ids) {
    const path = join(assetRoot, "plates", id + suffix);
    const bytes = readFileSync(path + ".png");
    assert.deepEqual([bytes.readUInt32BE(16), bytes.readUInt32BE(20)], [1536, 1024], path);
    assert.notEqual(digest(bytes), originalArt.get(id), path);
    assert.equal(digest(bytes), weatherArt.get(`${id}/${appearance}`), path);
    assert.ok(readFileSync(path + ".prompt.txt", "utf8").trim().length > 100, path);
  }
}
for (const stage of [6, 7, 8]) {
  const folder = join(root, `v${stage}-art`);
  const cityFolder = join(folder, "waterfront");
  const atlas = json(join(folder, "atlas.json"));
  const scene = json(join(cityFolder, "scene.json"));
  const manifest = json(join(cityFolder, "manifest.json"));
  const cityFiles = files(cityFolder, manifest);
  files(join(folder, "bay"), json(join(folder, "bay/manifest.json")));
  assert.equal(atlas.version, `0.${stage}.1`);
  assert.equal(scene.release, `inner-bay-v${stage}`);
  assert.equal(scene.assetRoot, `map/v${stage}-art/waterfront/`);
  assert.equal(scene.maskBundle, "map/illustrated-bay/masks.png");
  assert.equal(scene.lightsPreFiltered, true);
  assert.equal(scene.appearanceRevision, weatherRevision);
  assert.equal(manifest.sharedManifestSHA256, sharedSHA);
  assert.deepEqual(scene.projection, layout.camera);
  assert.deepEqual(scene.routes.slice(0, original.routes.length), original.routes);
  assert.deepEqual(scene.routes.slice(0, earlierRoutes.length).map(physicalRoute), earlierRoutes.map(physicalRoute));
  for (const route of scene.routes)
    assert.ok(route.hiddenSegments?.every(index => index >= 0 && index + 1 < route.points.length) ?? true, route.id);
  assert.ok(scene.routes.length > earlierRoutes.length);
  assert.ok(scene.landmarks.length > earlierPlaces);
  earlierRoutes = scene.routes;
  earlierPlaces = scene.landmarks.length;
  const rows = layout.frames.filter(frame => frame.stage <= stage);
  assert.equal(manifest.artwork.length, rows.length);
  for (const [index, frame] of rows.entries()) {
    assert.deepEqual(manifest.artwork[index], {
      id: frame.id, frame: frame.frame, kind: frame.kind, sha256: originalArt.get(frame.id),
    });
  }
  const layoutForStage = scene.tileLayout;
  const active = Object.fromEntries(Object.entries(common.nativeBlocks)
    .filter(([, [first]]) => first <= stage).map(([key, [, region]]) => [key, region]));
  assert.deepEqual(layoutForStage.sparse.blocks, active);
  const overrides = common.appearanceOverrides[stage];
  const sharedBackdropRoot = layoutForStage.sparse.backdropRoot;
  assert.deepEqual(layoutForStage.sparse.appearanceOverrides, overrides);
  let native = 0, overview = 0, localOverview = 0, substituted = 0;
  for (const appearance of appearances) {
    const source = regionTileSource(scene, "", appearance);
    for (let level = 0; level <= layoutForStage.maxLevel; level++) {
      const divisor = layoutForStage.tileSize * 2 ** (layoutForStage.maxLevel - level);
      for (let row = 0; row < Math.ceil(scene.height / divisor); row++) {
        for (let col = 0; col < Math.ceil(scene.width / divisor); col++) {
          if (!source.tileExists(level, col, row)) continue;
          const [path, query] = source.getTileUrl(level, col, row).split("?");
          assert.equal(query, appearance === "scene" ? undefined : `rev=${scene.appearanceRevision}`);
          if (level <= layoutForStage.sharedMaxLevel) {
            if (sharedBackdropRoot && path.startsWith(sharedBackdropRoot)) {
              assert.ok(latestBackdrop.has(path.slice(sharedBackdropRoot.length)), path);
            } else {
              assert.ok(cityFiles.has(path), path);
              localOverview++;
            }
            overview++;
          } else {
            const relative = path.replace(layoutForStage.sparse.root, "");
            assert.ok(commonFiles.has(relative), path);
            const override = overrides[`${appearance}/${level}/${col}_${row}`];
            if (override) {
              allVariants.add(relative);
              substituted++;
            }
            native++;
          }
        }
      }
    }
    for (const mark of scene.landmarks) {
      const { x, y } = project(mark.p, scene.projection);
      assert.ok(source.tileExists(layoutForStage.maxLevel, Math.floor(x / 512), Math.floor(y / 512)), mark.id);
    }
  }
  assert.equal(substituted, Object.keys(overrides).length);
  assert.equal(native, Object.keys(active).length * 45 * 4);
  assert.equal(overview, latest.tileCount);
  assert.equal(localOverview, manifest.tileCount);
  console.log(`v0.${stage}.1: ${rows.length} ImageGen plates, ${scene.landmarks.length} places, ${native} native tiles`);
}
assert.equal(common.tileCount, Object.keys(common.nativeBlocks).length * 45 * 4 + allVariants.size);
console.log("Illustrated expansion audit passed.");
