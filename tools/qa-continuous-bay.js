async page => {
  const url = new URL(page.url());
  url.search = new URLSearchParams({v: "0.10.0-preview", p: "oakland-north-waterfront"});
  const scale = 1.8545454545454545;
  const shots = ".local/continuous-bay/browser";
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("response", response => {
    if (response.status() >= 400 && new URL(response.url()).pathname.includes("/map/")) errors.push(response.url());
  });
  await page.setViewportSize({width: 1440, height: 960});
  await page.emulateMedia({reducedMotion: "reduce"});
  await page.goto(url.href);
  await page.waitForFunction(() => window.__sf?.ready && window.__sf.data.release === "east-bay-continuous-preview");
  const press = name => page.getByRole("button", {name, exact: true}).click();
  await press("Close environment panel");
  for (let i = 0; i < 3; i++) await press("Zoom in");

  const settled = () => page.waitForFunction(() => {
    const v = window.__sf.viewer.viewport;
    return v.getCenter().distanceTo(v.getCenter(true)) < 1e-6 && Math.abs(v.getZoom() - v.getZoom(true)) < .01;
  });
  await settled();
  const camera = () => page.evaluate(scale => {
    const m = window.__sf, p = m.data.projection, at = m.viewer.viewport.getCenter(true);
    return {x: (at.x * m.data.width - p.origin[0]) * scale / p.scale,
            y: (at.y * m.data.width - p.origin[1]) * scale / p.scale,
            density: m.transform.scale * p.scale};
  }, scale);
  const drawn = async (min = 1, appearance = 0) => {
    const ref = await page.waitForFunction(({min, appearance}) => {
      const m = window.__sf;
      const layers = m.details.layers.map((layer, i) => {
        const image = layer.images[appearance], level = i === 0 ? 16 : 19;
        if (image.getOpacity() < .99 || !image.getFullyLoaded()) return [];
        return image.getTilesToDraw().filter(({tile}) => tile.level === level && tile.loaded)
          .map(({tile}) => tile.getUrl());
      });
      return layers.flat().length >= min ? layers : null;
    }, {min, appearance}, {timeout: 18000});
    return ref.jsonValue();
  };
  const dragToward = async ([x, y]) => {
    for (let step = 0; step < 12; step++) {
      const c = await camera();
      if (c.density < 2.24) throw new Error("Camera dropped below native zoom while dragging");
      const dx = (c.x-x) * c.density/scale, dy = (c.y-y) * c.density/scale;
      if (Math.hypot(dx, dy) < 24) return;
      const factor = Math.max(1, Math.abs(dx)/450, Math.abs(dy)/380);
      await page.mouse.move(720, 480);
      await page.mouse.down();
      await page.mouse.move(720 + dx/factor, 480 + dy/factor, {steps: 12});
      await page.waitForTimeout(120);
      await page.mouse.up();
      await settled();
    }
    throw new Error("Could not reach the next continuous camera position");
  };
  const route = [
    ["oakland-shore", [13700, 1330]], ["emeryville-marina", [15746, 368]],
    ["emery-cove", [16268, 638]], ["emeryville-interchange", [18180, 1100]],
    ["aquatic-park", [19725, -175]], ["berkeley-causeway", [19410, -1430]],
    ["berkeley-marina", [19315, -2320]],
  ];
  const checks = [];
  for (const [name, point] of route) {
    await dragToward(point);
    const [city, prior, east] = await drawn();
    if (name !== "berkeley-marina" && east.length === 0 && city.length === 0)
      throw new Error("Native East Bay or original City tiles did not draw at " + name);
    const c = await camera();
    checks.push({name, ...c, city: city.length, earlierCloseup: prior.length, east: east.length});
    await page.screenshot({path: shots + "/" + name + ".jpg", quality: 92});
  }

  await page.getByRole("combobox", {name: "Jump to a place"}).selectOption("emery-cove");
  await settled();
  await press("Open environment panel");
  await press("Night");
  await press("Rain");
  const rain = await drawn(1, 3);
  if (!rain[2].some(path => path.includes("east-bay-waterfront/rain-night_files/19/")))
    throw new Error("East Bay wet-night native tiles did not draw");
  await page.screenshot({path: shots + "/emery-cove-rain-night.jpg", quality: 92});
  if (errors.length) throw new Error(errors.join("\n"));
  return {checks, nativeWetNight: rain[2][0], errors};
}
