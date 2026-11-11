async page => {
  const url = new URL(page.url());
  url.searchParams.set("v", "0.9.0");
  url.searchParams.delete("p");
  url.searchParams.delete("view");
  const errors = [], requests = [], verified = [];
  const output = ".local/full-bay/browser";
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("response", response => {
    if (response.status() >= 400) errors.push([response.status(), response.url()]);
  });
  page.on("request", request => {
    if (/\/regions\/[^/]+\/[^/]+_files\/\d+\/.+\.webp/.test(request.url())) requests.push(request.url());
  });
  const check = (value, message) => { if (!value) throw new Error(message); };
  const button = name => page.getByRole("button", { name, exact: true });
  const menu = page.getByRole("combobox", { name: "Jump to a place" });
  const settle = (appearance = "scene") => page.waitForFunction(appearance => {
    const m = window.__sf, viewport = m?.viewer.viewport;
    if (!m?.ready || m.frame.sequence !== m.sequence) return false;
    const layer = appearance === "scene" ? m.viewer.world.getItemAt(0) : m[appearance];
    return layer?.getFullyLoaded() && layer.getOpacity() > .99
      && viewport.getCenter(true).distanceTo(viewport.getCenter()) < .0002
      && Math.abs(viewport.getZoom(true) - viewport.getZoom()) < .001;
  }, appearance);
  const shot = async name => {
    const size = page.viewportSize();
    await page.mouse.move(size.width - 2, size.height - 2);
    await page.screenshot({ path: `${output}/${name}.jpg`, quality: 93 });
  };
  const jump = async (id, appearance = "scene") => {
    await menu.selectOption(id);
    await page.waitForFunction(id => window.__sf?.location === id, id);
    await settle(appearance);
  };

  await page.setViewportSize({ width: 1440, height: 960 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(url.href);
  await page.waitForFunction(() => window.__sf?.data.release === "full-bay-v9");
  await settle();
  const startup = requests.filter(path => path.includes("/v9-art/"));
  check(startup.length > 0 && startup.length < 24, `Unexpected startup requests: ${startup.length}`);
  check(startup.every(path => path.includes("/scene_files/") && !path.includes("/detail-")),
    "Overview requested close-ups or inactive appearances");
  await shot("whole-bay");

  await page.mouse.move(778, 567);
  const startZoom = await page.evaluate(() => window.__sf.viewer.viewport.getZoom());
  for (let i = 0; i < 5; i++) {
    await page.mouse.wheel(0, -200);
    await page.waitForTimeout(80);
  }
  await settle();
  const zoom = await page.evaluate(() => window.__sf.viewer.viewport.getZoom());
  check(zoom > startZoom * 1.5, "Wheel did not zoom the overview");
  const startLeft = await page.evaluate(() => window.__sf.transform.left);
  await page.mouse.move(766, 542);
  await page.mouse.down();
  await page.mouse.move(514, 516, { steps: 18 });
  await page.mouse.up();
  await settle();
  check(Math.abs(await page.evaluate(() => window.__sf.transform.left) - startLeft) > 100, "Pointer drag did not move the atlas");

  const details = await page.evaluate(() => window.__sf.data.landmarks.filter(mark => mark.detail).map(mark => mark.id));
  check(details.length === 16, "The closer views are incomplete");
  for (const id of details) {
    await jump(id);
    const levels = await page.evaluate(() => window.__sf.viewer.world.getItemAt(0)
      .getTilesToDraw().map(info => info.tile.level));
    check(Math.max(...levels) >= 15, `Only regional-scale tiles drawn at ${id}: ${levels}`);
    verified.push(id);
    if (["sfo", "alviso", "vallejo", "napa", "point-reyes", "dumbarton-bridge"].includes(id)) await shot(id);
  }
  await jump("sfo");
  await button("Day").click();
  await button("Rain").click();
  await settle("rainDayLayer");
  await shot("sfo-rain-day");
  await button("Night").click();
  await settle("rainNightLayer");
  await shot("sfo-rain-night");
  await jump("vallejo", "rainNightLayer");
  await shot("vallejo-rain-night");
  await button("Clear").click();
  await settle("nightLayer");
  await jump("san-jose", "nightLayer");
  await shot("san-jose-night");
  await button("Coastal fog").click();
  await page.waitForFunction(() => window.__sf.frame.controls.weather === "fog"
    && window.__sf.frame.sequence === window.__sf.sequence);
  await shot("san-jose-fog");
  await button("Day").click();
  await button("Clear").click();
  await button("Reset view").click();
  await settle();
  const fleet = await page.evaluate(() => window.__sf.snapshot().visible);
  check(fleet.cars > 0 && fleet.boats > 0 && fleet.planes > 0, `Incomplete Bay traffic: ${JSON.stringify(fleet)}`);
  await page.evaluate(() => window.__sf.setControls({ paused: false }));
  const start = await page.evaluate(() => window.__sf.frame.clock.transportTime);
  await page.waitForFunction(start => window.__sf.frame.clock.transportTime > start + .15, start);
  await page.evaluate(() => window.__sf.setControls({ paused: true }));
  await settle();
  const paused = await page.evaluate(() => window.__sf.frame.clock);
  await button("City").click();
  await page.waitForFunction(() => window.__sf?.ready && window.__sf.data.release === "inner-bay-v8");
  await settle();
  check(JSON.stringify(await page.evaluate(() => window.__sf.frame.clock)) === JSON.stringify(paused), "Scene switch reset the clocks");
  await jump("fort-baker");
  await shot("retained-city");
  await button("Bay Area").click();
  await page.waitForFunction(() => window.__sf?.ready && window.__sf.data.release === "full-bay-v9");
  await settle();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(url.href);
  await page.waitForFunction(() => window.__sf?.ready && window.__sf.data.release === "full-bay-v9");
  await jump("dumbarton-bridge");
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "Mobile view overflows");
  await button("Environment").click();
  await button("Rain").click();
  await settle("rainDayLayer");
  await shot("mobile-rain");
  check(!errors.length, JSON.stringify(errors));
  return { passed: true, startup: startup.length, closerViews: verified, fleet, errors };
}
