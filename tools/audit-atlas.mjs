import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const revision = process.argv[2] ?? "v4";
assert.ok(["v3", "v4"].includes(revision), "unsupported atlas revision");
const latest = revision === "v4";
const root = `public/map/${revision}`;
const json = (path) => JSON.parse(readFileSync(path, "utf8"));
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const pngSize = (bytes) => {
  assert.equal(bytes.subarray(1, 4).toString(), "PNG");
  return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
};
const atlas = json(join(root, "atlas.json"));
assert.equal(atlas.version, latest ? json("package.json").version : "0.3.0");
assert.equal(atlas.defaultScene, "waterfront");
assert.deepEqual(
  atlas.scenes.map((s) => s.id),
  ["waterfront", "bay"],
);
let totalTiles = 0;
for (const entry of atlas.scenes) {
  const folder = join(root, entry.id);
  const scene = json(join(root, entry.path));
  const manifest = json(join(root, entry.manifest));
  assert.equal(scene.release, entry.release);
  assert.equal(scene.kind, entry.id);
  assert.deepEqual(scene.originUTM, [553326.4257226175, 4183298.4609667137]);
  assert.equal(scene.crs, "EPSG:32610");
  assert.deepEqual(scene.projection.east, [0.8, 0.6]);
  assert.deepEqual(scene.projection.north, [0.6, -0.8]);
  assert.deepEqual([scene.width, scene.height], entry.size);
  assert.deepEqual(scene.maskSize, manifest.maskSize);
  assert.ok(scene.maskSize.every((x) => x <= (latest ? 4096 : 2048)));
  const actual = new Set();
  for (const file of manifest.files) {
    assert.ok(!actual.has(file.path), "duplicate manifest entry");
    actual.add(file.path);
    const data = readFileSync(join(folder, file.path));
    assert.equal(data.length, file.bytes, file.path);
    assert.equal(hash(data), file.sha256, file.path);
  }
  for (const name of ["depth", "water", "hard"])
    assert.deepEqual(
      pngSize(readFileSync(join(folder, name + ".png"))),
      scene.maskSize,
    );
  let expectedTiles = 0;
  for (const name of ["scene", "night", "rain-day", "rain-night"]) {
    const dzi = readFileSync(join(folder, name + ".dzi"), "utf8");
    assert.ok(dzi.includes(`Width="${scene.width}" Height="${scene.height}"`));
    const top = Math.ceil(Math.log2(Math.max(scene.width, scene.height)));
    for (let level = 0; level <= top; level++) {
      const div = 512 * 2 ** (top - level);
      for (let row = 0; row < Math.ceil(scene.height / div); row++)
        for (let col = 0; col < Math.ceil(scene.width / div); col++) {
          assert.ok(
            actual.has(`${name}_files/${level}/${col}_${row}.webp`),
            "missing pyramid tile",
          );
          expectedTiles++;
        }
    }
  }
  assert.equal(manifest.tileCount, expectedTiles);
  assert.equal(entry.tileCount, expectedTiles);
  assert.deepEqual(
    new Set(scene.routes.map((r) => r.kind)),
    new Set(["car", "ferry", "cargo", "plane"]),
  );
  assert.ok(
    scene.routes.every((r) => r.points.every((p) => p.every(Number.isFinite))),
  );
  if (entry.id === "waterfront") {
    assert.equal(manifest.artwork.length, 40);
    assert.equal(manifest.contextArtwork.length, 16);
    for (const art of [...manifest.artwork, ...manifest.contextArtwork,
      ...(manifest.westernArtwork ?? []), ...(manifest.westernContextArtwork ?? [])]) {
      const original = readFileSync(art.path);
      assert.equal(hash(original), art.sha256);
      assert.deepEqual(pngSize(original), [1536, 1024], art.path);
    }
    for (const row of manifest.shipClearance)
      assert.ok(row.minSourceLandMetres > row.hullRadiusMetres);
    assert.equal(scene.detailFrames.length, latest ? 21 : 10);
    if (latest) {
      assert.equal(manifest.westernArtwork.filter((a) => a.appearance === "day").length, 10);
      assert.equal(manifest.westernContextArtwork.length, 4);
      assert.equal(scene.landmarks.length, 22);
      assert.equal(scene.routes.filter((r) => r.id.startsWith("golden-gate-car-")).length, 48);
      assert.equal(manifest.shipClearance.length, 9);
      assert.equal(manifest.bridgeProfile.end - manifest.bridgeProfile.start, 2737);
      assert.ok(manifest.waterBlend.nearPx < manifest.waterBlend.farPx);
      const source = json("data/golden-gate/provenance.json");
      assert.equal(hash(readFileSync("data/golden-gate/source.json.gz")), source.sourceSHA256);
    }
    for (const landmark of scene.landmarks) {
      const [e, n, z] = landmark.p,
        p = scene.projection;
      const x = p.scale * (0.8 * e + 0.6 * n),
        y =
          p.scale * ((0.6 * e - 0.8 * n) * p.sinElevation - z * p.cosElevation);
      assert.ok(
        scene.detailFrames.some(
          (f) =>
            x >= f.x && x < f.x + f.width && y >= f.y && y < f.y + f.height,
        ),
        landmark.name + " is outside the illustrated corridor",
      );
    }
  }
  totalTiles += expectedTiles;
  console.log(
    `${entry.id}: ${expectedTiles} tiles, ${manifest.files.length} audited files, ${scene.routes.length} routes`,
  );
}
console.log(
  `Atlas ${revision} audit passed: ${totalTiles} DZI tiles, registered artwork, masks, routes and landmarks.`,
);
