async (page) => {
  const failures = [];
  const frames = () =>
    page.evaluate(
      () =>
        new Promise((resolve) => {
          let n = 0;
          const next = () => {
            if (++n === 35) resolve(true);
            else requestAnimationFrame(next);
          };
          requestAnimationFrame(next);
        }),
    );
  await page.goto("http://127.0.0.1:4186/");
  await page.waitForFunction(() => window.__sf?.ready);
  await page.evaluate(() =>
    window.__sf.setControls({ paused: false, autoHour: true }),
  );
  await page.waitForFunction(
    () => window.__sf.frame.sequence === window.__sf.sequence,
  );
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", {
      configurable: true,
      value: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await frames();
  const hidden = await page.evaluate(() => window.__sf.frame.clock);
  await frames();
  const hiddenLater = await page.evaluate(() => window.__sf.frame.clock);
  if (JSON.stringify(hidden) !== JSON.stringify(hiddenLater))
    failures.push("visibility event did not suspend all worker clocks");
  if (await page.evaluate(() => window.__sf.frame.controls.paused))
    failures.push("visibility changed the user pause choice");
  await page.evaluate(() => {
    delete document.hidden;
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await page.waitForFunction(
    (t) => window.__sf.frame.clock.transportTime > t + 0.15,
    hiddenLater.transportTime,
  );
  const fallback = await page.context().newPage();
  try {
    await fallback.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type, ...args) {
        if (type === "webgl2") return null;
        return original.call(this, type, ...args);
      };
    });
    await fallback.setViewportSize({ width: 1440, height: 960 });
    await fallback.goto("http://127.0.0.1:4186/");
    await fallback.waitForFunction(() => window.__sf?.ready);
    if (
      !(await fallback
        .getByText("此浏览器暂不支持天气特效。", { exact: false })
        .count())
    )
      failures.push("missing WebGL2 capability notice");
    if (
      !(await fallback
        .getByRole("button", { name: "下雨", exact: true })
        .isDisabled())
    )
      failures.push("unavailable weather still enabled");
    if (await fallback.evaluate(() => window.__sf.snapshot().webgl2))
      failures.push("fallback did not disable WebGL2");
  } finally {
    await fallback.close();
    await page.bringToFront();
  }
  if (failures.length) throw new Error(failures.join("; "));
  return {
    pass: true,
    visibilityEventSuspendsWorker: true,
    userPauseChoicePreserved: true,
    resume: true,
    noWebGL2NoticeAndDisabledControls: true,
    visibilityMethod:
      "synthetic Page Visibility event; no real OS tab-hiding claim",
  };
}
