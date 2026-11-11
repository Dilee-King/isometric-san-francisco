async page => {
  const button = name => page.getByRole("button", { name, exact: true });
  const settle = () => page.waitForFunction(() => {
    const map = window.__sf, viewport = map?.viewer.viewport;
    return map?.ready && viewport.getCenter(true).distanceTo(viewport.getCenter()) < .0003
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
  const appearance = layer => page.waitForFunction(layer =>
    window.__sf[layer].getOpacity() > .99 && window.__sf[layer].getFullyLoaded(), layer);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("http://127.0.0.1:4186/");
  await settle();
  await hold(2.5);
  await jump("financial-district");
  await hold(3);
  await page.mouse.move(600, 330);
  await page.mouse.down();
  await page.mouse.move(835, 755, { steps: 30 });
  await page.mouse.up();
  await settle();
  await hold(2.5);
  await jump("chinatown");
  await hold(3);
  await jump("north-beach");
  await hold(3);
  await jump("wharf");
  await hold(2.5);
  await jump("union-square");
  await hold(3);
  await button("Rain").click();
  await appearance("rainDayLayer");
  await hold(3.5);
  await button("Night").click();
  await appearance("rainNightLayer");
  await hold(3.5);
  await jump("chinatown");
  await appearance("rainNightLayer");
  await hold(3);
  await button("Day").click();
  await button("Coastal fog").click();
  await jump("telegraph-hill");
  await hold(3);
  await button("Clear").click();
  await jump("golden-gate-bridge");
  await button("Close environment panel").click();
  await hold(3);
  await button("Bay Area").click();
  await page.waitForFunction(() => window.__sf?.data.kind === "bay");
  await settle();
  await hold(3.5);
  return { recorded: "Actual v0.5 city route, district pan, Union Square, wet day/night, coastal fog, bridge and Bay Area overview" };
}
