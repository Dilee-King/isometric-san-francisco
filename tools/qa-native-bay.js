async page => {
  const out = ".local/native-bay";
  const url = new URL(page.url());
  const setPlace = async id => {
    await page.getByLabel("Jump to a place").selectOption(id);
    await page.waitForFunction(id => {
      const m = window.__sf;
      const v = m.viewer.viewport;
      return m.location === id && Math.abs(v.getZoom() - v.getZoom(true)) < .025 &&
        Math.abs(v.getCenter().x - v.getCenter(true).x) < 1e-5 &&
        Math.abs(v.getCenter().y - v.getCenter(true).y) < 1e-5;
    }, id);
  };
  const report = async (layer, appearance, group, minLevel) => {
    const handle = await page.waitForFunction(({layer, appearance, group, minLevel}) => {
      const m = window.__sf;
      const i = m.details.layers[layer].images[appearance];
      if (i.getOpacity() !== 1 || !i.getFullyLoaded()) return;
      const tile = i.getTilesToDraw().map(({tile}) => [tile.level, tile.getUrl()]).find(([level, u]) =>
        level >= minLevel && u.includes(group));
      if (tile) return {
        tile, density: m.transform.scale * m.data.projection.scale,
        weather: m.frame.controls.weather, hour: m.frame.clock.hour, place: m.location,
      };
    }, {layer, appearance, group, minLevel}, {timeout:20000});
    return handle.jsonValue();
  };
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("console", e => { if (e.type() === "error") errors.push(e.text()); });
  page.on("response", r => {
    if (r.status() >= 400 && new URL(r.url()).pathname.includes("/map/")) errors.push(r.status() + " " + r.url());
  });
  const press = name => page.getByRole("button", {name, exact:true}).click();
  const screenshot = name => page.screenshot({path:out + "/" + name + ".jpg",quality:94});
  const waitReady = () => page.waitForFunction(() => window.__sf?.ready && window.__sf.viewer.world.getItemAt(0).getFullyLoaded());

  await page.setViewportSize({width:1440,height:960});
  await page.emulateMedia({reducedMotion:"no-preference"});
  url.search = new URLSearchParams({v:"0.9.1",p:"ferry-building"});
  await page.goto(url.href);
  await waitReady();
  const city = [await report(0,0,"/illustrated-bay/",15)];
  await screenshot("ferry-day");
  await press("Night");
  city.push(await report(0,1,"/night_files/",15));
  await screenshot("ferry-night");
  await press("Rain");
  city.push(await report(0,3,"/rain-night_files/",15));
  await screenshot("ferry-rain-night");
  await press("Day");
  city.push(await report(0,2,"/rain-day_files/",15));
  await screenshot("ferry-rain-day");
  await press("Coastal fog");
  city.push(await report(0,0,"/scene_files/",15));
  await screenshot("ferry-fog");
  await press("Clear");
  const traffic = await page.evaluate(() => {
    const {frame} = window.__sf;
    return {mode: [...new Set(frame.poses.map(p => p.kind))], hour:frame.clock.hour, time:frame.clock.transportTime};
  });
  if (!["car", "ferry", "plane"].every(mode => traffic.mode.includes(mode))) throw new Error("Missing transport mode");
  await page.waitForFunction(time => window.__sf.frame.clock.transportTime > time + 0.2, traffic.time);
  for (const button of ["Cars","Boats","Aircraft"]) {
    const b = page.getByRole("button",{name:`Show ${button}`,exact:true});
    await b.click();
    if (await b.getAttribute("aria-pressed") !== "false") throw new Error(button + " failed to disable");
    await b.click();
  }

  const stops = await page.locator('optgroup[label="Closer views"] option').evaluateAll(options => options.map(option => option.value));
  if (stops.length !== 16) throw new Error("Expected 16 native close-ups");
  const closeups = [];
  for (const id of stops) {
    await setPlace(id);
    closeups.push(await report(1,0,"/detail/regions/" + id + "/",19));
    if (["sfo","san-jose","berkeley-marina","point-reyes"].includes(id)) await screenshot(id + "-day");
  }
  await setPlace("sfo");
  await press("Night");
  await press("Rain");
  const airportRain = await report(1,3,"/detail/regions/sfo/rain-night_files/",19);
  await screenshot("sfo-rain-night");
  await press("Day");
  await press("Clear");
  await setPlace("livermore");
  for (let k=0;k<15;k++) {
    await page.mouse.move(720,480);
    await page.mouse.wheel(0,-180);
    await page.waitForTimeout(85);
  }
  const coarse = await (await page.waitForFunction(() => {
    const m = window.__sf, v=m.viewer.viewport, ppm=m.transform.scale*m.data.projection.scale;
    if (Math.abs(ppm - .0425) < .0001 && Math.abs(v.getZoom()-v.getZoom(true)) < .025) return {ppm, zoom:v.getZoom(true), cap:v.getMaxZoom()};
  }, null, {timeout:10000})).jsonValue();
  await press("City");
  await page.waitForFunction(() => window.__sf?.ready && window.__sf.data.kind === "waterfront");
  const citySwitch = await page.evaluate(() => ({release: window.__sf.data.release, scale:window.__sf.data.projection.scale,weather:window.__sf.frame.controls.weather}));
  await press("Bay Area");
  await waitReady();

  await page.setViewportSize({width:390,height:844});
  url.search = new URLSearchParams({v:"0.9.1",p:"sfo"});
  await page.goto(url.href);
  await waitReady();
  const mobile = await report(1,0,"/detail/regions/sfo/scene_files/",19);
  await screenshot("sfo-mobile");
  await press("Environment");
  await press("Night");
  await press("Rain");
  const mobileRain = await report(1,3,"/detail/regions/sfo/rain-night_files/",19);
  await screenshot("sfo-mobile-rain");
  if (errors.length) throw new Error(errors.join("\n"));
  return {city,traffic,closeups,airportRain,coarse,citySwitch,mobile,mobileRain,errors};
}
