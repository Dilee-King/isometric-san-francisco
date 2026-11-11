async page => {
  const base = new URL(page.url());
  const button = name => page.getByRole("button", { name, exact: true });
  const settle = () => page.waitForFunction(() => {
    const map = window.__sf;
    if (!map?.ready) return false;
    const viewport = map.viewer.viewport;
    return viewport.getCenter(true).distanceTo(viewport.getCenter()) < .0001
      && Math.abs(viewport.getZoom(true) - viewport.getZoom()) < .001
      && map.viewer.world.getItemAt(0).getFullyLoaded();
  });
  const hold = async seconds => {
    const start = await page.evaluate(() => window.__sf.frame.clock.environmentTime);
    await page.waitForFunction(([start, seconds]) => window.__sf.frame.clock.environmentTime > start + seconds, [start, seconds]);
  };
  const jump = async identity => {
    await page.getByRole("combobox", { name: "Jump to a place" }).selectOption(identity);
    await page.waitForFunction(identity => window.__sf.location === identity, identity);
    await settle();
    await page.mouse.move(1436, 956);
  };
  const drag = async (x, y) => {
    await page.mouse.move(692 - x / 2, 495 - y / 2);
    await page.mouse.down();
    await page.mouse.move(692 + x / 2, 495 + y / 2, { steps: 34 });
    await page.mouse.up();
    await settle();
  };
  const dragTo = async identity => {
    for (let step = 0; step < 8; step++) {
      const offset = await page.evaluate(id => {
        const { data, transform } = window.__sf;
        const { scale, origin, east, north, sinElevation, cosElevation } = data.projection;
        const [x, n, z] = data.landmarks.find(mark => mark.id === id).p;
        const u = x * east[0] + n * north[0];
        const q = x * east[1] + n * north[1];
        const targetX = transform.left + transform.scale * (origin[0] + scale * u);
        const targetY = transform.top + transform.scale * (origin[1] + scale * (q * sinElevation - z * cosElevation));
        return [transform.width / 2 - targetX, transform.height / 2 - targetY];
      }, identity);
      if (Math.hypot(...offset) < 100) return;
      const factor = Math.max(1, Math.abs(offset[0]) / 610, Math.abs(offset[1]) / 395);
      await drag(offset[0] / factor, offset[1] / factor);
    }
  };
  const layer = key => page.waitForFunction(key => window.__sf[key].getOpacity() > .99 && window.__sf[key].getFullyLoaded(), key);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto(base.origin + base.pathname + "?v=0.8.1");
  await settle();
  await hold(2);
  await jump("union-square");
  await hold(1.4);
  await dragTo("civic-center");
  await hold(2.2);
  await page.evaluate(() => {
    const map = window.__sf, viewport = map.viewer.viewport;
    const [x, y] = map.data.projection.origin, width = map.data.width;
    const bounds = viewport.getBounds();
    Object.assign(bounds, { x: (x - 26900) / width, y: (y - 9000) / width, width: 29400 / width, height: 21600 / width });
    viewport.fitBoundsWithConstraints(bounds);
  });
  await settle();
  await hold(2.7);
  await drag(-185, 65);
  await hold(1.2);
  for (const id of ["ocean-beach", "golden-gate-park", "alamo-square", "mission-dolores", "bayview", "bay-bridge-west"]) {
    await jump(id);
    await hold(2.2);
  }
  for (const id of ["yerba-buena", "bay-bridge-east", "oakland-port"]) {
    await dragTo(id);
    await hold(2.2);
  }
  await jump("jack-london");
  await hold(2.2);
  await button("Rain").click();
  await layer("rainDayLayer");
  await hold(2.8);
  await button("Night").click();
  await layer("rainNightLayer");
  await hold(3);
  await jump("alameda-main");
  await layer("rainNightLayer");
  await hold(2.8);
  await button("Day").click();
  await button("Coastal fog").click();
  await jump("golden-gate-bridge");
  await hold(2.7);
  await button("Clear").click();
  await jump("fort-baker");
  await hold(2.5);
  await dragTo("sausalito-shore");
  await dragTo("sausalito");
  await hold(2.2);
  await button("Rain").click();
  await button("Night").click();
  await layer("rainNightLayer");
  await hold(3);
  await button("Day").click();
  await button("Clear").click();
  await button("Close environment panel").click();
  await button("Bay Area").click();
  await settle();
  await hold(4);
  return { recorded: "Citywide San Francisco, Bay Bridge, Oakland and Alameda, Fort Baker and Sausalito, and the regional overview" };
}
