async page => {
  const errors = [], bad = [], tiles = new Set();
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', r => {
    if (r.status() >= 400) bad.push([r.status(), r.url()]);
    if (r.url().includes('/map/v3/') && r.url().endsWith('.webp')) tiles.add(r.url());
  });
  const check = (ok, why) => { if (!ok) throw new Error(why); };
  const button = name => page.getByRole('button', {name, exact:true});
  const state = () => page.evaluate(() => window.__sf.snapshot());
  const frames = async (n=18) => page.evaluate(n => new Promise(resolve => {
    let i=0; const next = () => ++i >= n ? resolve(true) : requestAnimationFrame(next); requestAnimationFrame(next);
  }), n);
  const ready = async kind => {
    await page.waitForFunction(k => window.__sf?.ready && window.__sf.data.kind === k, kind);
    await page.waitForFunction(() => window.__sf.viewer.world.getItemAt(0).getFullyLoaded());
    await frames();
  };
  const ack = () => page.waitForFunction(() => window.__sf.frame.sequence === window.__sf.sequence);
  const appearance = async layer => {
    await ack();
    await page.waitForFunction(layer => window.__sf[layer]?.getOpacity() > .99 && window.__sf[layer].getFullyLoaded(), layer);
    await frames();
  };
  const shot = async name => {
    await page.mouse.move(1428,947);
    await page.screenshot({path:'docs/screenshots/v0.3/'+name+'.jpg',quality:93});
  };
  const jump = async id => {
    await page.getByRole('combobox',{name:'Jump to waterfront location'}).selectOption(id);
    await page.waitForFunction(id => {
      const map=window.__sf, v=map.viewer.viewport;
      return map.location===id && v.getCenter(true).distanceTo(v.getCenter())<.0005 &&
        Math.abs(v.getZoom(true)-v.getZoom())<.002;
    }, id);
    await page.waitForFunction(() => window.__sf.viewer.world.getItemAt(0).getFullyLoaded());
    await frames();
  };
  await page.setViewportSize({width:1440,height:960});
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.goto('http://127.0.0.1:4186/');
  await ready('waterfront');
  const first = await state(), firstTiles = tiles.size;
  check(first.release==='waterfront-v3' && first.vehicleRenderer==='webgl2-world-mesh','wrong runtime');
  check(first.maskSize[0]===1343 && first.maskSize[1]===1850,'incorrect bounded mask');
  check(firstTiles>0 && firstTiles<80,'whole atlas loaded on initial view');
  check(await page.evaluate(() => !/\p{Script=Han}/u.test(document.body.innerText)),'English interface required');
  check(await page.locator('.location-caption').count()===0,'obsolete lower-left caption');
  await page.waitForFunction(t => window.__sf.frame.clock.transportTime > t+.38, first.frame.clock.transportTime);
  const moved = await state();
  for (const kind of ['car','ferry','cargo','plane'])
    check(moved.frame.poses.some(p => p.kind===kind && first.frame.poses.some(q => p.id===q.id && Math.hypot(...p.point.map((n,i)=>n-q.point[i]))>.1)),kind+' did not move');
  await button('Pause animation').click(); await ack(); await frames();
  const frozen=(await state()).frame.clock;
  await frames(30);
  check(JSON.stringify((await state()).frame.clock)===JSON.stringify(frozen),'pause advanced time');
  for (const [name,kind] of [['Cars','car'],['Boats','ferry'],['Aircraft','plane']]) {
    await button('Show '+name).click(); await ack();
    check(!(await state()).frame.poses.some(p=>p.kind===kind),'failed '+name+' switch');
    await button('Show '+name).click(); await ack();
  }
  await shot('ferry-clear');
  await jump('wharf'); await shot('wharf-clear');
  await jump('pier-39'); await shot('pier-39-clear');
  await jump('exploratorium');
  const beforePan=await state();
  await page.mouse.move(870,670); await page.mouse.down();
  await page.mouse.move(780,390,{steps:12}); await page.mouse.up();
  await frames(32);
  check(Math.abs((await state()).transform.top-beforePan.transform.top)>50,'continuous drag did not pan');
  await shot('northern-join');
  await jump('bay-bridge'); await shot('bay-bridge-clear');
  await jump('oracle-park'); await shot('oracle-clear');
  await button('Rain').click(); await appearance('rainDayLayer'); await shot('oracle-rain-day');
  await page.locator('.atmosphere').evaluate(el=>el.style.visibility='hidden');
  await page.screenshot({path:'output/v3-wet-surfaces.png'});
  await button('Clear').click(); await ack(); await frames();
  await page.screenshot({path:'output/v3-dry-surfaces.png'});
  await page.locator('.atmosphere').evaluate(el=>el.style.visibility='');
  await button('Rain').click(); await button('Night').click(); await appearance('rainNightLayer');
  await shot('oracle-rain-night');
  await jump('chase-center'); await appearance('rainNightLayer'); await shot('mission-bay-rain-night');
  const southern = await page.evaluate(() => {
    const map=window.__sf, gl=map.vehicles.gl;
    map.vehicles.draw(map.frame,map.transform);
    const pixels=new Uint8Array(gl.drawingBufferWidth*gl.drawingBufferHeight*4);
    gl.readPixels(0,0,gl.drawingBufferWidth,gl.drawingBufferHeight,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    let painted=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]>0)painted++;
    return {painted, visible:map.snapshot().visible};
  });
  check(southern.painted>100 && southern.visible.cars>0,'southern vehicles clipped or absent');
  await page.getByRole('checkbox',{name:'Auto day/night',exact:false}).check(); await ack();
  const transfer=(await state()).frame;
  await button('Bay Area').click(); await ready('bay'); await appearance('rainNightLayer');
  check(await page.locator('.base-map').count()===1,'regional transition leaked a base map element');
  let current=(await state()).frame;
  check(JSON.stringify(current.clock)===JSON.stringify(transfer.clock),'regional switch reset clocks');
  check(JSON.stringify(current.controls)===JSON.stringify(transfer.controls),'regional switch reset controls');
  await shot('bay-rain-night');
  await button('Day').click(); await button('Clear').click(); await ack(); await frames(); await shot('bay-overview');
  const bayState=await state();
  await button('Zoom in').click();
  await page.waitForFunction(s=>window.__sf.transform.scale>s*1.1,bayState.transform.scale);
  await button('Reset view').click(); await frames(30);
  await button('Waterfront').click(); await ready('waterfront');
  check(await page.locator('.base-map').count()===1,'waterfront transition leaked a base map element');
  check((await state()).location==='chase-center','waterfront did not restore last location');
  await button('Coastal fog').click(); await ack(); await frames(); await shot('mission-bay-fog');
  await button('Clear').click(); await ack(); await frames(); await shot('mission-bay-clear');
  await page.setViewportSize({width:390,height:844}); await page.reload(); await ready('waterfront');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile overflow');
  check(await page.getByRole('combobox',{name:'Jump to waterfront location'}).isVisible(),'mobile location selector hidden');
  await page.screenshot({path:'docs/screenshots/v0.3/mobile.jpg',quality:92});
  await button('Environment').click(); await button('Rain').click(); await appearance('rainDayLayer');
  check(await button('Show Aircraft').isVisible(),'mobile traffic controls hidden');
  await page.screenshot({path:'docs/screenshots/v0.3/mobile-rain.jpg',quality:92});
  await button('Hide').click();
  await button('Bay Area').click(); await ready('bay'); await appearance('rainDayLayer');
  check(await page.locator('.base-map').count()===1,'mobile scene transition leaked a base map element');
  await page.screenshot({path:'docs/screenshots/v0.3/mobile-bay.jpg',quality:92});
  await page.emulateMedia({reducedMotion:'reduce'}); await page.reload(); await ready('waterfront');
  check((await state()).frame.controls.paused,'reduced-motion pause missing');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.setViewportSize({width:1440,height:960}); await page.reload(); await ready('waterfront');
  check(errors.length===0,'page errors: '+JSON.stringify(errors));
  check(bad.length===0,'failed requests: '+JSON.stringify(bad));
  return {passed:true,firstTiles,visibleInitial:first.visible,southern,sceneTransfer:true,mobile390:true,errors,bad};
}
