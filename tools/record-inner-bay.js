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
  const layer = key => page.waitForFunction(key => window.__sf[key].getOpacity() > .99 && window.__sf[key].getFullyLoaded(), key);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto(base.origin + base.pathname + "?v=0.8.0");
  await settle();
  await hold(2);
  await page.evaluate(() => {
    const map = window.__sf, viewport = map.viewer.viewport;
    const [x, y] = map.data.projection.origin, width = map.data.width;
    const bounds = viewport.getBounds();
    Object.assign(bounds, { x: (x - 26900) / width, y: (y - 9000) / width, width: 29400 / width, height: 21600 / width });
    viewport.fitBoundsWithConstraints(bounds);
  });
  await settle();
  await hold(2.7);
  for (const id of ["ocean-beach", "golden-gate-park", "alamo-square", "mission-dolores", "bayview", "bay-bridge-west", "yerba-buena", "bay-bridge-east", "oakland-port", "jack-london"]) {
    await jump(id);
    await hold(2.2);
    if (id === "bay-bridge-west") {
      await page.mouse.move(810, 430);
      await page.mouse.down();
      await page.mouse.move(440, 560, { steps: 30 });
      await page.mouse.up();
      await settle();
      await hold(1.2);
    }
  }
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
  await jump("sausalito");
  await hold(3.3);
  await button("Close environment panel").click();
  await button("Bay Area").click();
  await settle();
  await hold(4);
  return { recorded: "Citywide San Francisco, Bay Bridge, Oakland and Alameda, Fort Baker and Sausalito, and the regional overview" };
}
