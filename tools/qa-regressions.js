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
        .getByText("Weather effects are unavailable in this browser.", { exact: false })
        .count())
    )
      failures.push("missing WebGL2 capability notice");
    if (
      !(await fallback
        .getByRole("button", { name: "Rain", exact: true })
        .isDisabled())
    )
      failures.push("unavailable weather still enabled");
    if (await fallback.evaluate(() => window.__sf.snapshot().webgl2))
      failures.push("fallback did not disable WebGL2");
    if (await fallback.evaluate(() => window.__sf.snapshot().vehicleRenderer) !== "canvas-world-mesh")
      failures.push("world-space Canvas fallback unavailable");
    await fallback.getByRole("button", { name: "Night", exact: true }).click();
    await fallback.waitForFunction(() => window.__sf.nightLayer.getOpacity() > .99 && window.__sf.nightLayer.getFullyLoaded());
  } finally {
    await fallback.close();
    await page.bringToFront();
  }
  const limited = await page.context().newPage();
  try {
    await limited.addInitScript(() => {
      const gl = WebGL2RenderingContext.prototype;
      const getParameter = gl.getParameter;
      const texImage2D = gl.texImage2D;
      gl.getParameter = function (parameter) {
        if (parameter === this.MAX_TEXTURE_SIZE) return 4096;
        return getParameter.call(this, parameter);
      };
      window.maskUploads = [];
      gl.texImage2D = function (...args) {
        if (args.length === 9) {
          window.maskUploads.push([args[3], args[4]]);
          if (Math.max(args[3], args[4]) > 4096) throw new Error("Texture exceeded simulated device limit");
        }
        return texImage2D.apply(this, args);
      };
    });
    await limited.goto("http://127.0.0.1:4186/?v=0.8.0");
    await limited.waitForFunction(() => window.__sf?.ready && window.__sf.data.release === "inner-bay-v8");
    await limited.getByRole("button", { name: "Rain", exact: true }).click();
    await limited.waitForFunction(() => window.__sf.rainDayLayer.getOpacity() > .99 && window.__sf.rainDayLayer.getFullyLoaded());
    const upload = await limited.evaluate(() => {
      const { vehicles, atmosphere } = window.__sf;
      return {
        masks: window.maskUploads.filter(([width, height]) => width === 4096 && height === 2275).length,
        errors: [vehicles.gl.getError(), atmosphere.gl.getError()],
      };
    });
    if (upload.masks !== 2 || upload.errors.some(Boolean))
      failures.push("limited GPU did not upload both packed mask textures");
  } finally {
    await limited.close();
    await page.bringToFront();
  }
  if (failures.length) throw new Error(failures.join("; "));
  return {
    pass: true,
    visibilityEventSuspendsWorker: true,
    userPauseChoicePreserved: true,
    resume: true,
    noWebGL2NoticeAndDisabledControls: true,
    canvasWorldMeshAndNightFallback: true,
    simulated4096TextureLimit: true,
    visibilityMethod:
      "synthetic Page Visibility event; no real OS tab-hiding claim",
  };
}
