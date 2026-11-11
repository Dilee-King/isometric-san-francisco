async page => {
  const errors=[], failures=[], tiles=new Set();
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',e=>{if(e.type()==='error')errors.push(e.text());});
  page.on('response',r=>{
    if(r.status()>=400)failures.push([r.status(),r.url()]);
    if(r.url().includes('/map/v4/')&&r.url().endsWith('.webp'))tiles.add(r.url());
  });
  const check=(yes,why)=>{if(!yes)throw new Error(why);};
  const button=name=>page.getByRole('button',{name,exact:true});
  const state=()=>page.evaluate(()=>window.__sf.snapshot());
  const frames=(n=14)=>page.evaluate(n=>new Promise(resolve=>{
    let count=0;const tick=()=>++count>=n?resolve(true):requestAnimationFrame(tick);requestAnimationFrame(tick);
  }),n);
  const settled=async()=>{
    await page.waitForFunction(()=>{
      const m=window.__sf,v=m?.viewer.viewport;
      return m?.ready&&v.getCenter(true).distanceTo(v.getCenter())<.0003
        &&Math.abs(v.getZoom(true)-v.getZoom())<.001&&m.viewer.world.getItemAt(0).getFullyLoaded();
    });
    await frames();
  };
  const ready=async kind=>{
    await page.waitForFunction(k=>window.__sf?.ready&&window.__sf.data.kind===k,kind);
    await settled();
  };
  const ack=()=>page.waitForFunction(()=>window.__sf.frame.sequence===window.__sf.sequence);
  const appearance=async layer=>{
    await ack();
    await page.waitForFunction(k=>window.__sf[k]?.getOpacity()>.99&&window.__sf[k].getFullyLoaded(),layer);
    await frames();
  };
  const jump=async id=>{
    await page.getByRole('combobox',{name:'Jump to waterfront location'}).selectOption(id);
    await page.waitForFunction(i=>window.__sf.location===i,id);
    await settled();
  };
  const shot=async name=>{
    const v=page.viewportSize();
    await page.mouse.move(v.width-4,v.height-4);
    await page.screenshot({path:'docs/screenshots/v0.4/'+name+'.jpg',quality:94});
  };
  const measure=async id=>page.evaluate(prefix=>{
    const m=window.__sf, gl=m.vehicles.gl;
    const poses=m.frame.poses.filter(p=>p.id.startsWith(prefix));
    m.vehicles.draw({...m.frame,poses},m.transform);
    const pixels=new Uint8Array(gl.drawingBufferWidth*gl.drawingBufferHeight*4);
    gl.readPixels(0,0,gl.drawingBufferWidth,gl.drawingBufferHeight,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    let count=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]>0)count++;
    m.vehicles.draw(m.frame,m.transform);
    return {poses:poses.length,painted:count};
  },id);
  await page.setViewportSize({width:1440,height:960});
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.goto('http://127.0.0.1:4186/');
  await ready('waterfront');
  const initial=await state(),firstTiles=tiles.size;
  check(initial.release==='waterfront-v4'&&initial.vehicleRenderer==='webgl2-world-mesh','incorrect release or transport renderer');
  check(firstTiles>0&&firstTiles<100,'initial view requested too many tiles');
  check(initial.landmarks.length===22,'missing waterfront landmarks');
  check(await page.evaluate(()=>!(/\p{Script=Han}/u.test(document.body.innerText))),'interface is not English');
  await jump('wharf');
  const edge=await state();
  await page.mouse.move(630,510);await page.mouse.down();
  await page.mouse.move(1190,690,{steps:23});await page.mouse.up();await settled();
  check((await state()).transform.left-edge.transform.left>140,'could not drag west from the old waterfront');
  await shot('wharf-aquatic-join');
  for (const id of ['aquatic-park','fort-mason','marina-green','palace-of-fine-arts','crissy-east','tunnel-tops','crissy-field','west-bluff','fort-point']) {
    await jump(id);
    if (['fort-mason','marina-green','palace-of-fine-arts','crissy-field','fort-point'].includes(id))
      await shot(id+'-clear');
  }
  await jump('golden-gate-bridge');
  await button('Close environment panel').click();await frames();
  await shot('bridge-clear');
  await page.waitForFunction(()=>{
    const m=window.__sf,p=m.frame.poses.find(p=>p.id==='golden-gate-overflight');
    if(!p)return false;
    const q=m.data.projection,t=m.transform,[e,n,z]=p.point;
    const x=t.left+t.scale*(q.origin[0]+q.scale*(.8*e+.6*n));
    const y=t.top+t.scale*(q.origin[1]+q.scale*((.6*e-.8*n)*q.sinElevation-z*q.cosElevation));
    return x>125&&x<innerWidth-175&&y>65&&y<innerHeight-65;
  });
  const motion0=await state();
  await page.waitForFunction(t=>window.__sf.frame.clock.transportTime>t+.65,motion0.frame.clock.transportTime);
  const motion1=await state();
  for(const id of ['golden-gate-car-2','golden-gate-cargo','golden-gate-overflight']){
    const a=motion0.frame.poses.find(p=>p.id===id),b=motion1.frame.poses.find(p=>p.id===id);
    check(a&&b&&Math.hypot(...a.point.map((x,i)=>x-b.point[i]))>.8,id+' did not move');
  }
  const bridgeCars=await measure('golden-gate-car-');
  check(bridgeCars.poses===48&&bridgeCars.painted>25,'bridge vehicles were clipped or absent');
  const bridgeShip=await measure('golden-gate-cargo');
  const bridgePlane=await measure('golden-gate-overflight');
  check(bridgeShip.painted>30&&bridgePlane.painted>10,'western ship or aircraft layer was empty');
  await button('Open environment panel').click();await button('Pause animation').click();await ack();
  await button('Coastal fog').click();await ack();await frames(22);await shot('bridge-coastal-fog');
  await button('Rain').click();await appearance('rainDayLayer');await shot('bridge-rain-day');
  await button('Night').click();await appearance('rainNightLayer');await shot('bridge-rain-night');
  await jump('marina-green');await appearance('rainNightLayer');await shot('marina-rain-night');
  await button('Day').click();await appearance('rainDayLayer');
  await page.locator('.atmosphere').evaluate(el=>el.style.visibility='hidden');
  await page.screenshot({path:'output/v4-wet-materials.png'});
  await button('Clear').click();await ack();await frames(26);
  await page.screenshot({path:'output/v4-dry-materials.png'});
  await page.locator('.atmosphere').evaluate(el=>el.style.visibility='');
  await button('Night').click();await appearance('nightLayer');await shot('marina-clear-night');
  for(const [name,kind] of [['Cars','car'],['Boats','ferry'],['Aircraft','plane']]){
    await button('Show '+name).click();await ack();
    check(!(await state()).frame.poses.some(p=>p.kind===kind),name+' did not toggle');
    await button('Show '+name).click();await ack();
  }
  await button('Rain').click();await appearance('rainNightLayer');
  const transfer=(await state()).frame;
  await button('Bay Area').click();await ready('bay');await appearance('rainNightLayer');
  const bay=(await state()).frame;
  check(JSON.stringify(transfer.clock)===JSON.stringify(bay.clock),'regional switch reset the paused clocks');
  check(JSON.stringify(transfer.controls)===JSON.stringify(bay.controls),'regional switch reset controls');
  await button('Day').click();await button('Clear').click();await ack();
  await button('Close environment panel').click();await frames(22);await shot('bay-overview');
  await button('Waterfront').click();await ready('waterfront');
  check((await state()).location==='marina-green'&&await page.locator('.base-map').count()===1,'return did not restore location or leaked base layer');
  await jump('chase-center');await shot('mission-bay-clear');
  const east=await measure('mission-bay-car-');
  check(east.painted>20,'old southern car routes were lost');
  await page.setViewportSize({width:390,height:844});await page.reload();await ready('waterfront');
  await jump('golden-gate-bridge');await shot('mobile-bridge');
  const mobile=await state();
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile overflow');
  check(mobile.transform.scale*3150<=396,'bridge jump is cropped horizontally on mobile');
  await button('Environment').click();await button('Rain').click();await appearance('rainDayLayer');await shot('mobile-rain');
  await button('Hide').click();await button('Bay Area').click();await ready('bay');await appearance('rainDayLayer');
  check(await page.locator('.base-map').count()===1,'mobile switch leaked base map');
  await page.emulateMedia({reducedMotion:'reduce'});await page.reload();await ready('waterfront');
  check((await state()).frame.controls.paused,'reduced-motion startup did not pause');
  check(!errors.length,'page or console errors: '+JSON.stringify(errors));
  check(!failures.length,'failed resources: '+JSON.stringify(failures));
  return {passed:true,firstTiles,bridgeCars,bridgeShip,bridgePlane,east,sceneTransfer:true,mobile390:true,errors,failures};
}
