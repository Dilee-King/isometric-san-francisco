async page => {
  const errors = [], failed = [], requests = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("response", response => {
    if (response.status() >= 400) failed.push([response.status(), response.url()]);
  });
  page.on("request", request => {
    const match = request.url().match(/\/map\/v5\/waterfront\/regions\/([^/]+)\/([^/]+)_files\/([0-9]+)\//);
    if (match) requests.push({ region: match[1], appearance: match[2], level: Number(match[3]), url: request.url() });
  });
  const check = (yes, why) => { if (!yes) throw new Error(why); };
  const button = name => page.getByRole("button", { name, exact: true });
  const state = () => page.evaluate(() => window.__sf.snapshot());
  const frames = (count = 15) => page.evaluate(count => new Promise(resolve => {
    let drawn = 0;
    const tick = () => ++drawn >= count ? resolve(true) : requestAnimationFrame(tick);
    requestAnimationFrame(tick);
  }), count);
  const settle = async kind => {
    await page.waitForFunction(k => window.__sf?.ready && window.__sf.data.kind === k, kind);
    await page.waitForFunction(() => {
      const map = window.__sf, viewport = map.viewer.viewport;
      return viewport.getCenter(true).distanceTo(viewport.getCenter()) < .0003
        && Math.abs(viewport.getZoom(true) - viewport.getZoom()) < .001
        && map.viewer.world.getItemAt(0).getFullyLoaded();
    });
    await frames();
  };
  const ack = () => page.waitForFunction(() => window.__sf.frame.sequence === window.__sf.sequence);
  const appearance = async layer => {
    await ack();
    await page.waitForFunction(key => window.__sf[key].getOpacity() > .99 && window.__sf[key].getFullyLoaded(), layer);
    await frames();
  };
  const jump = async identity => {
    await page.getByRole("combobox", { name: "Jump to a place" }).selectOption(identity);
    await page.waitForFunction(identity => window.__sf.location === identity, identity);
    await settle("waterfront");
  };
  const shot = async name => {
    const viewport = page.viewportSize();
    await page.mouse.move(viewport.width - 3, viewport.height - 3);
    await page.screenshot({ path: "docs/screenshots/v0.5/" + name + ".jpg", quality: 94 });
  };
  const painted = prefix => page.evaluate(prefix => {
    const map = window.__sf, gl = map.vehicles.gl;
    const poses = map.frame.poses.filter(pose => pose.id.startsWith(prefix));
    map.vehicles.draw({ ...map.frame, poses }, map.transform);
    const pixels = new Uint8Array(gl.drawingBufferWidth * gl.drawingBufferHeight * 4);
    gl.readPixels(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    let count = 0;
    for (let i = 3; i < pixels.length; i += 4) if (pixels[i] > 0) count++;
    map.vehicles.draw(map.frame, map.transform);
    return { poses: poses.length, pixels: count };
  }, prefix);

  await page.setViewportSize({ width: 1440, height: 960 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("http://127.0.0.1:4186/");
  await settle("waterfront");
  const first = await state();
  check(first.release === "city-core-v5" && first.landmarks.length === 30, "Incorrect city-core release");
  check(first.vehicleRenderer === "webgl2-world-mesh", "Projected renderer unavailable");
  const initialRequests = requests.slice();
  const initialRegions = [...new Set(initialRequests.map(request => request.region))];
  check(initialRequests.length > 0 && initialRequests.length < 100, "Unexpected initial tile request count");
  check(!initialRegions.some(region => ["golden-gate", "marina", "south-waterfront"].includes(region)), "A distant detail region loaded before navigation");
  check(initialRequests.filter(request => request.level > 11).every(request => request.appearance === "scene"), "An inactive appearance preloaded native tiles");
  check(await page.evaluate(() => !/\p{Script=Han}/u.test(document.body.innerText)), "Interface contains non-English text");
  const movingBefore = await page.evaluate(() => window.__sf.frame);
  await page.waitForFunction(time => window.__sf.frame.clock.transportTime > time + 1, movingBefore.clock.transportTime);
  const movingAfter = await page.evaluate(() => window.__sf.frame);
  const movedKinds = ["car", "ferry", "cargo", "plane"].filter(kind =>
    movingBefore.poses.some(before => {
      const after = movingAfter.poses.find(pose => pose.id === before.id);
      return before.kind === kind && after && Math.hypot(...after.point.map((value, index) => value - before.point[index])) > .1;
    }),
  );
  check(movedKinds.length === 4, "Transport motion missing for " + JSON.stringify(movedKinds));
  await button("Pause animation").click();
  await ack();
  const clock = (await state()).frame.clock;
  const traffic = await page.evaluate(() => window.__sf.frame.poses);
  for (const [name, kinds] of [["Cars", ["car"]], ["Boats", ["ferry", "cargo"]], ["Aircraft", ["plane"]]]) {
    await button("Show " + name).click();
    await ack();
    const hidden = await page.evaluate(() => window.__sf.frame.poses);
    check(hidden.every(pose => !kinds.includes(pose.kind)), name + " switch left its mode visible");
    check(JSON.stringify(hidden) === JSON.stringify(traffic.filter(pose => !kinds.includes(pose.kind))), name + " switch changed another mode");
    await button("Show " + name).click();
    await ack();
    check(JSON.stringify(await page.evaluate(() => window.__sf.frame.poses)) === JSON.stringify(traffic), name + " switch changed route positions");
  }
  await shot("ferry-building-clear");
  await page.evaluate(() => { window.__cityWorker = window.__sf.worker; });
  const counts = {};
  for (const identity of ["financial-district", "chinatown", "north-beach", "wharf", "union-square"]) {
    await jump(identity);
    check(JSON.stringify((await state()).frame.clock) === JSON.stringify(clock), "Regional jump reset the paused clock");
    check(await page.evaluate(() => window.__cityWorker === window.__sf.worker), "A district jump restarted the simulation");
    counts[identity] = await painted("core-");
    await shot(identity + "-clear");
  }
  check(counts["chinatown"].pixels > 50 && counts["union-square"].pixels > 50, "Core vehicles are hidden or absent");
  check(!requests.some(request => ["golden-gate", "south-waterfront"].includes(request.region)), "City navigation requested distant detail regions");
  check(!requests.some(request => request.region === "marina" && request.level > 12), "City navigation requested distant Marina detail");
  const cityRequests = requests.length;
  await jump("north-beach");
  await button("Play animation").click();
  await page.waitForFunction(() => window.__sf.frame.clock.transportTime >= 12);
  await button("Pause animation").click();
  await ack();
  const flight = await painted("core-overflight");
  check(flight.pixels > 20, "City aircraft did not render over North Beach");
  await shot("north-beach-clear");
  await jump("financial-district");
  const beforePan = await state();
  await page.mouse.move(600, 320);
  await page.mouse.down();
  await page.mouse.move(840, 770, { steps: 25 });
  await page.mouse.up();
  await settle("waterfront");
  check((await state()).transform.left - beforePan.transform.left > 100, "City drag did not cross the district boundary");
  await shot("financial-chinatown-join");
  await jump("telegraph-hill");
  await shot("telegraph-hill-clear");
  await button("Coastal fog").click();
  await ack();
  await frames(25);
  await shot("telegraph-hill-coastal-fog");
  await button("Clear").click();
  await jump("chinatown");
  await button("Rain").click();
  await appearance("rainDayLayer");
  await shot("chinatown-rain-day");
  await page.locator(".atmosphere").evaluate(element => element.style.visibility = "hidden");
  await page.screenshot({ path: "output/v5-city-wet.png" });
  await button("Clear").click();
  await ack();
  await frames(25);
  await page.screenshot({ path: "output/v5-city-dry.png" });
  await page.locator(".atmosphere").evaluate(element => element.style.visibility = "");
  await button("Rain").click();
  await button("Night").click();
  await appearance("rainNightLayer");
  await shot("chinatown-rain-night");
  await jump("union-square");
  await appearance("rainNightLayer");
  await shot("union-square-rain-night");
  await button("Clear").click();
  await appearance("nightLayer");
  await shot("union-square-night");
  const transfer = (await state()).frame;
  await button("Bay Area").click();
  await settle("bay");
  await appearance("nightLayer");
  const bay = (await state()).frame;
  check(JSON.stringify(bay.clock) === JSON.stringify(transfer.clock), "Overview reset the clock");
  check(JSON.stringify(bay.controls) === JSON.stringify(transfer.controls), "Overview reset controls");
  await button("Day").click();
  await button("Close environment panel").click();
  await frames(25);
  await shot("bay-overview");
  await button("City").click();
  await settle("waterfront");
  check((await state()).location === "union-square" && await page.locator(".base-map").count() === 1, "City return lost the saved view or leaked a map");
  await jump("golden-gate-bridge");
  check(requests.some(request => request.region === "golden-gate"), "Bridge region did not load after navigation");
  const bridge = await painted("golden-gate-car-");
  check(bridge.pixels > 20, "Existing bridge vehicles lost visibility");
  await shot("bridge-clear");
  await jump("chase-center");
  check(requests.some(request => request.region === "south-waterfront"), "Southern region did not load");
  await shot("mission-bay-clear");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await settle("waterfront");
  await jump("union-square");
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "Mobile interface overflows");
  await shot("mobile-union-square");
  await button("Environment").click();
  await button("Rain").click();
  await appearance("rainDayLayer");
  await shot("mobile-rain");
  await button("Hide").click();
  await button("Bay Area").click();
  await settle("bay");
  check(await page.locator(".base-map").count() === 1, "Mobile scene switch leaked a map");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await settle("waterfront");
  check((await state()).frame.controls.paused, "Reduced-motion startup is running");
  check(errors.length === 0, "Application errors " + JSON.stringify(errors));
  check(failed.length === 0, "Failed resources " + JSON.stringify(failed));
  return {
    passed: true, initialRequests: initialRequests.length, initialRegions,
    cityRequests, counts, movedKinds, flight, bridge, sharedClock: true, mobile390: true, errors, failed,
  };
}
