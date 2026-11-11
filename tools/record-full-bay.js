async page => {
  const button = name => page.getByRole("button", { name, exact: true });
  const place = page.getByRole("combobox", { name: "Jump to a place" });
  const hold = seconds => page.waitForTimeout(seconds * 1000);
  const settle = (key = "scene") => page.waitForFunction(key => {
    const m = window.__sf;
    if (!m?.ready) return false;
    const layer = key === "scene" ? m.viewer.world.getItemAt(0) : m[key];
    const view = m.viewer.viewport;
    return layer?.getFullyLoaded() && layer.getOpacity() > .99
      && Math.abs(view.getZoom(true) - view.getZoom()) < .001;
  }, key);
  const drag = async (x, y, nx, ny) => {
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(nx, ny, { steps: 35 });
    await page.mouse.up();
  };
  await settle();
  await hold(1.4);
  await page.mouse.move(766, 570);
  for (let i = 0; i < 9; i++) {
    await page.mouse.wheel(0, -210);
    await hold(.12);
  }
  await settle();
  await drag(788, 550, 683, 465);
  await hold(.65);
  await place.selectOption("sfo");
  await settle();
  await hold(1.4);
  await drag(762, 521, 900, 480);
  await hold(.5);
  await button("Rain").click();
  await settle("rainDayLayer");
  await hold(1.25);
  await button("Night").click();
  await settle("rainNightLayer");
  await hold(1.6);
  await place.selectOption("vallejo");
  await settle("rainNightLayer");
  await hold(1.6);
  await button("Day").click();
  await button("Clear").click();
  await place.selectOption("alviso");
  await settle();
  await hold(1.55);
  await button("Reset view").click();
  await settle();
  await hold(1.4);
}
