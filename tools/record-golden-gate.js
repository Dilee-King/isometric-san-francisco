async page => {
  const button=name=>page.getByRole('button',{name,exact:true});
  const settle=()=>page.waitForFunction(()=>{
    const m=window.__sf,v=m?.viewer.viewport;
    return m?.ready&&v.getCenter(true).distanceTo(v.getCenter())<.0003&&m.viewer.world.getItemAt(0).getFullyLoaded();
  });
  const hold=async(seconds)=>{
    const time=await page.evaluate(()=>window.__sf.frame.clock.environmentTime);
    await page.waitForFunction(([t,d])=>window.__sf.frame.clock.environmentTime>t+d,[time,seconds]);
  };
  const jump=async id=>{
    await page.getByRole('combobox',{name:'Jump to waterfront location'}).selectOption(id);
    await page.waitForFunction(k=>window.__sf.location===k,id);await settle();
    await page.mouse.move(1437,953);
  };
  const appearance=name=>page.waitForFunction(k=>window.__sf[k].getOpacity()>.99&&window.__sf[k].getFullyLoaded(),name);
  await page.setViewportSize({width:1440,height:960});await page.emulateMedia({reducedMotion:'no-preference'});
  await page.goto('http://127.0.0.1:4186/');await settle();
  await jump('wharf');await hold(2);
  await page.mouse.move(600,460);await page.mouse.down();
  await page.mouse.move(1215,643,{steps:30});await page.mouse.up();await settle();await hold(2.8);
  await jump('fort-mason');await hold(3);
  await jump('marina-green');await hold(3.2);
  await jump('crissy-field');await hold(3.5);
  await jump('fort-point');await hold(3);
  await jump('golden-gate-bridge');await button('Close environment panel').click();await hold(5);
  await button('Open environment panel').click();await button('Coastal fog').click();await hold(4);
  await button('Rain').click();await appearance('rainDayLayer');await hold(2.5);
  await button('Night').click();await appearance('rainNightLayer');await hold(3.5);
  await jump('marina-green');await appearance('rainNightLayer');await hold(3.7);
  await button('Day').click();await button('Clear').click();
  await button('Bay Area').click();await page.waitForFunction(()=>window.__sf?.data.kind==='bay');await settle();
  await button('Close environment panel').click();await hold(4.5);
  return {recorded:'Actual v0.4 waterfront pan, Golden Gate Bridge, moving transport, coastal fog, wet day/night and Bay Area overview'};
}
