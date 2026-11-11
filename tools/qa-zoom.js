async page => {
  const url = new URL(page.url());
  await page.setViewportSize({ width: 1360, height: 900 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto(url.href);
  await page.waitForFunction(() => window.__sf?.ready && window.__sf.viewer.world.getItemAt(0).getFullyLoaded());
  const records = [];
  for (const name of ["clear", "night", "rain-night"]) {
    await page.evaluate(name => {
      const m = window.__sf;
      m.focusLocation(m.data.kind === "bay" ? "sfo" : "ferry-building", true);
      m.setControls({ paused: false, autoHour: false, weather: name === "rain-night" ? "rain" : "clear" }, name === "clear" ? 14.25 : 23.5);
    }, name);
    await page.waitForFunction(name => {
      const m = window.__sf;
      const layer = name === "clear" ? m.viewer.world.getItemAt(0) : name === "night" ? m.nightLayer : m.rainNightLayer;
      return m.frame.sequence === m.sequence && layer.getFullyLoaded();
    }, name);
    await page.evaluate(() => {
      const m = window.__sf;
      const q = window.__zoomBench = { intervals: [], count: {}, cost: {}, long: [], from: performance.now() };
      q.observer = new PerformanceObserver(list => q.long.push(...list.getEntries().map(e => e.duration)));
      q.observer.observe({ type: "longtask" });
      let last = performance.now();
      const sample = now => {
        q.intervals.push(now - last);
        last = now;
        q.raf = requestAnimationFrame(sample);
      };
      q.raf = requestAnimationFrame(sample);
      q.restore = Object.entries({ sprites: m.sprites, vehicles: m.vehicles, weather: m.atmosphere, atlas: m.viewer.drawer }).map(([key, layer]) => {
        const draw = layer.draw;
        layer.draw = function (...args) {
          const start = performance.now();
          try { return draw.apply(this, args); }
          finally {
            q.count[key] = (q.count[key] ?? 0) + 1;
            q.cost[key] = (q.cost[key] ?? 0) + performance.now() - start;
          }
        };
        return () => layer.draw = draw;
      });
    });
    await page.mouse.move(688, 460);
    for (const delta of [...Array(12).fill(220), ...Array(12).fill(-220)]) {
      await page.mouse.wheel(0, delta);
      await page.waitForTimeout(65);
    }
    await page.mouse.down();
    await page.mouse.move(903, 517, { steps: 14 });
    await page.mouse.up();
    await page.waitForTimeout(520);
    records.push(await page.evaluate(name => {
      const q = window.__zoomBench;
      const m = window.__sf;
      cancelAnimationFrame(q.raf);
      q.restore.forEach(f => f());
      q.observer.disconnect();
      const round = x => Math.round(x * 10) / 10;
      const values = q.intervals.slice(1).sort((a,b) => a-b);
      const p = rank => round(values[Math.min(values.length - 1, Math.floor(values.length * rank))]);
      const network = performance.getEntriesByType("resource").filter(e => e.startTime >= q.from && /_files\/\d+\/[^?]+\.webp/.test(e.name));
      return { name, frames: values.length, p50: p(.5), p95: p(.95), worst: p(1), over33: values.filter(ms => ms > 33.4).length, longTasks: q.long.length, tiles: network.length, tileLayers: [...new Set(network.map(e => e.name.match(/([^/]+)_files/)[1]))], drawer: m.viewer.drawer.constructor.name, count: q.count, cost: Object.fromEntries(Object.entries(q.cost).map(([key, total]) => [key, round(total / q.count[key])])), zoom: m.viewer.viewport.getZoom() };
    }, name));
  }
  return records;
}
