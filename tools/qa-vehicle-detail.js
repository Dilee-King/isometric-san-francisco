async page => {
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto('http://127.0.0.1:4186/');
  await page.waitForFunction(() => window.__sf?.ready && window.__sf.frame.poses.some(p => p.kind === 'plane'));
  await page.getByRole('button', { name: 'Pause animation', exact: true }).click();
  await page.waitForFunction(() => window.__sf.frame.sequence === window.__sf.sequence);
  await page.getByRole('button', { name: 'Close environment panel', exact: true }).click();
  const captured = [];
  for (const kind of ['car', 'ferry', 'plane']) {
    const pose = await page.evaluate(kind => {
      const map = window.__sf;
      const poses = map.frame.poses.filter(p => p.kind === kind && map.sprites.isVisible(p.point, kind === 'plane'));
      const pose = kind === 'car' ? poses.find(p => Math.abs(p.point[0]) < 160) ?? poses[0] : poses[0];
      if (!pose) throw new Error('Missing visible ' + kind);
      const c = map.data.projection, [x, n, z] = pose.point;
      const ix = c.origin[0] + c.scale * (c.east[0] * x + c.north[0] * n);
      const iy = c.origin[1] + c.scale * ((c.east[1] * x + c.north[1] * n) * c.sinElevation - z * c.cosElevation);
      const item = map.viewer.world.getItemAt(0);
      map.viewer.viewport.zoomTo(map.viewer.viewport.getHomeZoom() * 3, undefined, true);
      map.viewer.viewport.panTo(item.imageToViewportCoordinates(ix, iy), true);
      map.viewer.viewport.applyConstraints(true);
      return { id: pose.id, point: pose.point, direction: pose.direction };
    }, kind);
    await page.waitForFunction(() => window.__sf.viewer.world.getItemAt(0).getFullyLoaded());
    await page.evaluate(() => new Promise(resolve => {
      let n = 0; const next = () => ++n >= 20 ? resolve(true) : requestAnimationFrame(next); requestAnimationFrame(next);
    }));
    await page.mouse.move(1425, 945);
    await page.screenshot({ path: 'docs/screenshots/v0.2/' + kind + '-detail.png' });
    captured.push(pose);
  }
  return { renderer: await page.evaluate(() => window.__sf.snapshot().vehicleRenderer), actualPausedVehicleDetails: captured };
}
