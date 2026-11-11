async page => {
  const url = new URL(page.url());
  const output = `.local/weather-alignment/${url.hostname.endsWith("github.io") ? "online" : "local"}`;
  const errors = [], requests = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("response", response => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
  });
  page.on("request", request => requests.push(request.url()));
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  const button = name => page.getByRole("button", { name, exact: true });
  const settle = async (appearance = "scene") => {
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await page.waitForFunction(appearance => {
      const map = window.__sf, viewport = map.viewer.viewport;
      const layer = appearance === "scene" ? map.viewer.world.getItemAt(0) : map[appearance];
      return map.frame.sequence === map.sequence && layer.getFullyLoaded() && layer.getOpacity() > .99
        && viewport.getCenter(true).distanceTo(viewport.getCenter()) < .0001
        && Math.abs(viewport.getZoom(true) - viewport.getZoom()) < .0001;
    }, appearance);
  };
  const jump = async id => {
    await page.getByRole("combobox", { name: "Jump to a place" }).selectOption(id);
    await page.waitForFunction(id => window.__sf.location === id, id);
    await settle();
  };
  const readLegacyLights = () => page.evaluate(() => {
    const map = window.__sf;
    const frame = { ...map.frame, poses: [] };
    map.sprites.draw(frame, map.transform, false);
    const pixels = map.sprites.ctx.getImageData(250, 154, 720, 530).data;
    let litPixels = 0, alpha = 0;
    for (let offset = 3; offset < pixels.length; offset += 4) {
      if (pixels[offset] > 0) litPixels++;
      alpha += pixels[offset];
    }
    return { litPixels, alpha };
  });
  const capture = (version, id, appearance) => page.screenshot({
    path: `${output}/${version}-${id}-${appearance}.png`,
  });

  await page.setViewportSize({ width: 1280, height: 800 });
  const lights = {};
  for (const [version, release, anchor, neighbor] of [
    ["0.5.0", "city-core-v5", "wharf", null],
    ["0.6.1", "inner-bay-v6", "civic-center", "sunset"],
    ["0.7.1", "inner-bay-v7", "jack-london", "alameda-main"],
    ["0.8.1", "inner-bay-v8", "sausalito", "fort-baker"],
  ]) {
    const requestStart = requests.length;
    url.searchParams.set("v", version);
    await page.goto(url.href);
    await page.waitForFunction(release => window.__sf?.ready && window.__sf.data.release === release, release);
    await button("Pause animation").click();
    if (!(await button("Night").isVisible())) await button("Environment").click();
    await jump("union-square");
    await button("Night").click();
    await settle("nightLayer");
    lights[version] = await readLegacyLights();
    const original = lights["0.5.0"];
    check(original.litPixels > 100, "Reference lighting could not be captured");
    check(Math.abs(lights[version].litPixels / original.litPixels - 1) < .015
      && Math.abs(lights[version].alpha / original.alpha - 1) < .015,
    `Union Square lamp and window coverage differs from v0.5 in ${version}`);
    for (const id of [anchor, neighbor].filter(Boolean)) {
      await button("Clear").click();
      await button("Day").click();
      await jump(id);
      await capture(version, id, "day");
      await button("Night").click();
      await settle("nightLayer");
      await capture(version, id, "night");
      await button("Rain").click();
      await settle("rainNightLayer");
      await capture(version, id, "rain-night");
      await button("Day").click();
      await settle("rainDayLayer");
      await capture(version, id, "rain-day");
      await page.evaluate(() => { window.__sf.atmosphere.canvas.style.visibility = "hidden"; });
      await capture(version, id, "rain-material");
      await page.evaluate(() => { window.__sf.atmosphere.canvas.style.visibility = ""; });
    }
    if (version !== "0.5.0") {
      const revision = await page.evaluate(() => window.__sf.data.appearanceRevision);
      check(revision && requests.slice(requestStart).some(url => /\/rain-day_files\//.test(url) && url.endsWith(`?rev=${revision}`)),
        `The revised wet tiles were not requested in ${version}`);
    }
  }
  check(errors.length === 0, JSON.stringify(errors));
  return { passed: true, lights, errors };
}
