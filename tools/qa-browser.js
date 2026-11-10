async (page) => {
  const errors = [],
    badRequests = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("response", (r) => {
    if (r.status() >= 400) badRequests.push([r.status(), r.url()]);
  });
  const check = (condition, message) => {
    if (!condition) throw new Error(message);
  };
  const snapshot = () => page.evaluate(() => window.__sf.snapshot());
  const settle = async () => {
    await page.waitForFunction(
      () => window.__sf?.ready && window.__sf?.nightLayer,
    );
  };
  const ack = async () => {
    await page.waitForFunction(
      () => window.__sf.frame.sequence === window.__sf.sequence,
    );
  };
  const frames = async (count = 20) =>
    page.evaluate(
      (n) =>
        new Promise((resolve) => {
          let i = 0;
          const next = () => {
            if (++i >= n) resolve(true);
            else requestAnimationFrame(next);
          };
          requestAnimationFrame(next);
        }),
      count,
    );
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("http://127.0.0.1:4186/");
  await settle();
  await page.waitForFunction(
    () =>
      window.__sf.snapshot().visible.cars > 10 &&
      window.__sf.snapshot().visible.boats === 3 &&
      window.__sf.snapshot().visible.planes === 1,
  );
  const first = await snapshot();
  check(first.webgl2, "WebGL2 effects unavailable");
  const before = first.frame.poses;
  await page.waitForFunction(
    (t) => window.__sf.frame.clock.transportTime > t + 0.35,
    first.frame.clock.transportTime,
  );
  const moved = (await snapshot()).frame.poses;
  for (const kind of ["car", "ferry", "cargo", "plane"])
    check(
      moved.some(
        (p) =>
          p.kind === kind &&
          before.some(
            (q) =>
              q.id === p.id &&
              Math.hypot(...p.point.map((v, i) => v - q.point[i])) > 0.1,
          ),
      ),
      kind + " did not move",
    );
  await page.getByRole("button", { name: "暂停城市动画", exact: true }).click();
  await ack();
  await frames(3);
  await page.mouse.move(1425, 945);
  await page.screenshot({ path: "docs/screenshots/day.png" });
  const frozen = await snapshot();
  await frames();
  check(
    JSON.stringify((await snapshot()).frame.clock) ===
      JSON.stringify(frozen.frame.clock),
    "pause did not freeze all clocks",
  );
  await page.screenshot({ path: "output/frozen-a.png" });
  await frames();
  await page.screenshot({ path: "output/frozen-b.png" });
  await page.getByRole("checkbox", { name: "自动昼夜", exact: false }).check();
  await ack();
  await frames();
  check(
    JSON.stringify((await snapshot()).frame.clock) ===
      JSON.stringify(frozen.frame.clock),
    "automatic day continued while paused",
  );
  for (const [name, kind] of [
    ["显示车辆", "car"],
    ["显示船舶", "ferry"],
    ["显示飞机", "plane"],
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await ack();
    check(
      !(await snapshot()).frame.poses.some((p) => p.kind === kind),
      "toggle failed for " + kind,
    );
    await page.getByRole("button", { name, exact: true }).click();
    await ack();
  }
  check(
    JSON.stringify((await snapshot()).frame.clock) ===
      JSON.stringify(frozen.frame.clock),
    "switch reset a clock",
  );
  const unzoomed = (await snapshot()).transform;
  await page.getByRole("button", { name: "放大地图", exact: true }).click();
  await page.waitForFunction(
    (s) => window.__sf.transform.scale > s * 1.2,
    unzoomed.scale,
  );
  await page.mouse.move(750, 700);
  await page.mouse.down();
  await page.mouse.move(850, 760, { steps: 8 });
  await page.mouse.up();
  await frames(15);
  const zoomed = await snapshot();
  check(zoomed.transform.scale > unzoomed.scale, "zoom failed");
  await page.screenshot({ path: "docs/screenshots/detail.png" });
  await page.getByRole("button", { name: "地图全景", exact: true }).click();
  await frames(20);
  await page.getByRole("button", { name: "夜晚", exact: true }).click();
  await ack();
  await page.waitForFunction(
    () =>
      window.__sf.nightLayer.getFullyLoaded() &&
      window.__sf.nightLayer.getOpacity() > 0.99,
  );
  await frames(5);
  await page.mouse.move(1425, 945);
  await page.screenshot({ path: "docs/screenshots/night.png" });
  await page.getByRole("button", { name: "下雨", exact: true }).click();
  await ack();
  await frames(5);
  await page.screenshot({ path: "docs/screenshots/rain-night.png" });
  await page.getByRole("button", { name: "白天", exact: true }).click();
  await page.getByRole("button", { name: "海雾", exact: true }).click();
  await ack();
  await frames(5);
  await page.screenshot({ path: "docs/screenshots/fog.png" });
  await page.getByRole("button", { name: "多云", exact: true }).click();
  await ack();
  await frames(4);
  await page.screenshot({ path: "docs/screenshots/cloudy.png" });
  await page.getByRole("button", { name: "关于与来源", exact: true }).click();
  check(await page.getByRole("dialog").isVisible(), "About did not open");
  await page.keyboard.press("Escape");
  check(!(await page.getByRole("dialog").count()), "Escape failed");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await settle();
  await frames(3);
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "mobile horizontal overflow",
  );
  await page.screenshot({ path: "docs/screenshots/mobile.png" });
  await page.getByRole("button", { name: "环境", exact: true }).click();
  await page.getByRole("button", { name: "夜晚", exact: true }).click();
  await page.getByRole("button", { name: "下雨", exact: true }).click();
  await ack();
  await page.waitForFunction(() => window.__sf.nightLayer.getFullyLoaded());
  await frames(3);
  check(
    await page
      .getByRole("button", { name: "显示飞机", exact: true })
      .isVisible(),
    "mobile transport controls hidden",
  );
  await page.screenshot({ path: "docs/screenshots/mobile-controls.png" });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await settle();
  check(
    (await snapshot()).frame.controls.paused,
    "reduced motion did not start paused",
  );
  const reduced = (await snapshot()).frame.clock;
  await frames();
  check(
    JSON.stringify((await snapshot()).frame.clock) === JSON.stringify(reduced),
    "reduced motion advanced clocks",
  );
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.reload();
  await settle();
  check(errors.length === 0, "runtime errors: " + errors.join("; "));
  check(
    badRequests.length === 0,
    "failed resources: " + JSON.stringify(badRequests),
  );
  return {
    pass: true,
    movement: ["car", "ferry", "cargo", "plane"],
    pauseAllClocks: true,
    toggles: true,
    zoomPan: true,
    weather: ["clear", "cloudy", "fog", "rain"],
    authoredNight: true,
    mobile390: true,
    reducedMotion: true,
    visibleInitial: first.visible,
    errors,
    badRequests,
  };
}
