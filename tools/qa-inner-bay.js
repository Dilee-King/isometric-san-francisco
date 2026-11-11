async page => {
  const location = new URL(page.url());
  const base = location.origin + location.pathname;
  const online = location.hostname.endsWith("github.io");
  const errors = [], failures = [], requests = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("response", response => { if (response.status() >= 400) failures.push([response.status(), response.url()]); });
  page.on("request", request => {
    const match = request.url().match(/\/map\/inner-bay\/regions\/([^/]+)\/([^/]+)_files\//);
    if (match) requests.push([match[1], match[2]]);
  });
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  const button = name => page.getByRole("button", { name, exact: true });
  const state = () => page.evaluate(() => window.__sf.snapshot());
  const ack = () => page.waitForFunction(() => window.__sf.frame.sequence === window.__sf.sequence);
  const settle = async release => {
    await page.waitForFunction(release => window.__sf?.ready && window.__sf.data.release === release, release);
    await page.waitForFunction(() => {
      const map = window.__sf, viewport = map.viewer.viewport;
      return viewport.getCenter(true).distanceTo(viewport.getCenter()) < .0001
        && Math.abs(viewport.getZoom(true) - viewport.getZoom()) < .001
        && map.viewer.world.getItemAt(0).getFullyLoaded();
    });
    await page.evaluate(() => new Promise(resolve => {
      let frames = 0;
      const step = () => ++frames >= 15 ? resolve(true) : requestAnimationFrame(step);
      requestAnimationFrame(step);
    }));
  };
  const shot = async (version, name) => {
    const size = page.viewportSize();
    await page.mouse.move(size.width - 3, size.height - 3);
    await page.screenshot({ path: `docs/screenshots/v0.${version}/${online ? "online-" : ""}${name}.jpg`, quality: 93 });
  };
  const jump = async (version, identity) => {
    await page.getByRole("combobox", { name: "Jump to a place" }).selectOption(identity);
    await page.waitForFunction(id => window.__sf.location === id, identity);
    await settle(`inner-bay-v${version}`);
  };
  const inspectArea = async (version, left, top, width, height) => {
    await page.evaluate(([left, top, width, height]) => {
      const map = window.__sf, viewport = map.viewer.viewport;
      const [x, y] = map.data.projection.origin, imageWidth = map.data.width;
      const bounds = viewport.getBounds();
      Object.assign(bounds, { x: (x + left) / imageWidth, y: (y + top) / imageWidth,
        width: width / imageWidth, height: height / imageWidth });
      viewport.fitBoundsWithConstraints(bounds);
    }, [left, top, width, height]);
    await settle(`inner-bay-v${version}`);
  };
  const layer = async name => {
    await ack();
    await page.waitForFunction(key => window.__sf[key].getOpacity() > .99 && window.__sf[key].getFullyLoaded(), name);
  };
  const painted = prefix => page.evaluate(prefix => {
    const map = window.__sf, gl = map.vehicles.gl;
    const poses = map.frame.poses.filter(pose => pose.id.startsWith(prefix));
    map.vehicles.draw({ ...map.frame, poses }, map.transform);
    const pixels = new Uint8Array(gl.drawingBufferWidth * gl.drawingBufferHeight * 4);
    gl.readPixels(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    let count = 0;
    for (let offset = 3; offset < pixels.length; offset += 4) count += Number(pixels[offset] > 0);
    map.vehicles.draw(map.frame, map.transform);
    return count;
  }, prefix);
  const open = async (version, places) => {
    const start = requests.length;
    await page.goto(`${base}?v=0.${version}.0`);
    await settle(`inner-bay-v${version}`);
    const initial = requests.slice(start);
    check(initial.length > 0, "No visible native tiles at Ferry Building");
    check(initial.every(([region, appearance]) => !["east-bay-waterfront", "sausalito-shore"].includes(region) && appearance === "scene"), "A distant or inactive detail region loaded at startup");
    const status = await state();
    check(status.landmarks.length === places && status.vehicleRenderer === "webgl2-world-mesh" && status.webgl2, "Unexpected version or renderer");
    if (version === 8) {
      await page.waitForFunction(time => window.__sf.frame.clock.transportTime > time + .8, status.frame.clock.transportTime);
      const moved = new Map((await state()).frame.poses.map(pose => [pose.id, pose]));
      const kinds = new Set(status.frame.poses.filter(pose => {
        const current = moved.get(pose.id);
        return current && current.point.some((value, i) => Math.abs(value - pose.point[i]) > .1);
      }).map(pose => pose.kind));
      check(["car", "ferry", "cargo", "plane"].every(kind => kinds.has(kind)), "One of the four transport kinds did not move");
    }
    await button("Pause animation").click();
    await ack();
    return initial.length;
  };

  await page.setViewportSize({ width: 1440, height: 960 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const startup6 = await open(6, 54);
  const clock6 = (await state()).frame.clock;
  await page.evaluate(() => { window.__innerBayWorker = window.__sf.worker; });
  for (const identity of ["ocean-beach", "golden-gate-park", "alamo-square", "mission-dolores", "lake-merced", "bayview", "hunters-point"]) {
    await jump(6, identity);
    check(JSON.stringify((await state()).frame.clock) === JSON.stringify(clock6), "City navigation changed the paused clock");
    check(await page.evaluate(() => window.__sf.worker === window.__innerBayWorker), "A city jump restarted the worker");
    if (["ocean-beach", "golden-gate-park", "alamo-square", "lake-merced", "bayview"].includes(identity)) await shot(6, identity);
  }
  await inspectArea(6, -26900, -9000, 29400, 21600);
  await shot(6, "san-francisco-wide");
  await jump(6, "bay-bridge-west");
  const westCars = await painted("bay-bridge-");
  check(westCars > 50, "West span has no visible bridge cars");
  await shot(6, "bay-bridge-west");
  const beforeDrag = (await state()).transform;
  await page.mouse.move(810, 430);
  await page.mouse.down();
  await page.mouse.move(440, 560, { steps: 27 });
  await page.mouse.up();
  await settle("inner-bay-v6");
  const afterDrag = (await state()).transform;
  check(Math.hypot(afterDrag.left - beforeDrag.left, afterDrag.top - beforeDrag.top) > 220, "Bridge drag did not move the camera");
  check(await page.evaluate(() => window.__sf.worker === window.__innerBayWorker), "Bridge drag replaced the worker");
  await jump(6, "yerba-buena");
  await shot(6, "yerba-buena");
  await jump(6, "bay-bridge-east");
  const eastCars = await painted("bay-bridge-");
  check(eastCars > 50, "East span has no visible bridge cars");
  await shot(6, "bay-bridge-east");
  await jump(6, "oakland-touchdown");
  check(requests.some(([region]) => region === "bay-bridge"), "No bridge tiles requested on crossing");
  await inspectArea(6, 9230, 1910, 1515, 1010);
  check(requests.some(([region]) => region === "through-v6"), "The v0.6 Oakland context did not use its pre-port appearance");
  check(!requests.some(([region]) => region === "east-bay-waterfront" || region === "sausalito-shore"), "Future detail was requested by v0.6");
  await button("Bay Area").click();
  await settle("bay-overview-v6");
  await shot(6, "bay-overview");

  const startup7 = await open(7, 59);
  await jump(7, "oakland-port");
  await shot(7, "oakland-port");
  await jump(7, "jack-london");
  const oaklandFerry = await painted("oakland-ferry-");
  check(oaklandFerry > 30, "Oakland ferry missing from the terminal view");
  await shot(7, "jack-london");
  if (!online) {
    await page.locator(".atmosphere").evaluate(element => element.style.visibility = "hidden");
    await page.screenshot({ path: "output/inner-bay-dry.png" });
  }
  await button("Rain").click();
  await layer("rainDayLayer");
  if (!online) {
    await page.screenshot({ path: "output/inner-bay-wet.png" });
    await page.locator(".atmosphere").evaluate(element => element.style.visibility = "" );
  }
  await shot(7, "jack-london-rain");
  await button("Night").click();
  await layer("rainNightLayer");
  await shot(7, "jack-london-rain-night");
  await jump(7, "alameda-main");
  await layer("rainNightLayer");
  await shot(7, "alameda-main-rain-night");
  await jump(7, "alameda-seaplane");
  check(requests.some(([region, appearance]) => region === "east-bay-waterfront" && appearance === "rain-night"), "East Bay night rain tiles were not requested");
  await inspectArea(7, -7000, -9700, 1515, 1010);
  await layer("rainNightLayer");
  check(requests.some(([region, appearance]) => region === "through-v7" && appearance === "rain-night"), "The v0.7 Marin context did not use its pre-Fort Baker appearance");

  const startup8 = await open(8, 63);
  await jump(8, "golden-gate-bridge");
  await shot(8, "golden-gate-bridge");
  await jump(8, "fort-baker");
  await shot(8, "fort-baker");
  await jump(8, "sausalito");
  const marinFerry = await painted("sausalito-ferry-");
  check(marinFerry > 30, "Sausalito ferry missing from the landing view");
  await shot(8, "sausalito");
  await button("Coastal fog").click();
  await ack();
  await shot(8, "sausalito-fog");
  await button("Rain").click();
  await button("Night").click();
  await layer("rainNightLayer");
  await shot(8, "sausalito-rain-night");
  check(requests.some(([region]) => region === "sausalito-shore"), "Marin detail was not fetched");
  const before = (await state()).frame;
  await button("Bay Area").click();
  await settle("bay-overview-v8");
  const after = (await state()).frame;
  check(JSON.stringify(before.clock) === JSON.stringify(after.clock) && JSON.stringify(before.controls) === JSON.stringify(after.controls), "Bay view reset time or weather");
  await button("Day").click();
  await button("Clear").click();
  await ack();
  await button("Close environment panel").click();
  await page.waitForFunction(() => window.__sf.nightLayer.getOpacity() < .001 && window.__sf.rainNightLayer.getOpacity() < .001);
  await shot(8, "bay-overview");
  await button("City").click();
  await settle("inner-bay-v8");
  check((await state()).location === "sausalito" && await page.locator(".base-map").count() === 1, "City return lost Sausalito or leaked a map");

  if (!online) {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await settle("inner-bay-v8");
    await jump(8, "sausalito");
    await button("Environment").click();
    await button("Rain").click();
    await layer("rainDayLayer");
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "Mobile map overflows horizontally");
    await shot(8, "mobile-sausalito");
  }
  check(errors.length === 0 && failures.length === 0, JSON.stringify({ errors, failures }));
  return { passed: true, startup: [startup6, startup7, startup8], westCars, eastCars, oaklandFerry, marinFerry, errors, failures };
}
