async page => {
  const button = name => page.getByRole('button',{name,exact:true});
  const settle = async () => {
    await page.waitForFunction(() => window.__sf?.ready && window.__sf.viewer.world.getItemAt(0).getFullyLoaded());
  };
  const hold = async seconds => {
    const start=await page.evaluate(()=>window.__sf.frame.clock.environmentTime);
    await page.waitForFunction(([start,seconds])=>window.__sf.frame.clock.environmentTime>=start+seconds,[start,seconds]);
  };
  const jump = async id => {
    await page.getByRole('combobox',{name:'Jump to waterfront location'}).selectOption(id);
    await page.waitForFunction(id=>{
      const m=window.__sf,v=m.viewer.viewport;
      return m.location===id&&v.getCenter(true).distanceTo(v.getCenter())<.0005;
    },id);
    await settle();
    await page.mouse.move(1432,945);
  };
  await page.setViewportSize({width:1440,height:960});
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.goto('http://127.0.0.1:4186/');
  await settle(); await jump('wharf'); await hold(4);
  await jump('pier-39'); await hold(3);
  await button('Coastal fog').click(); await hold(3);
  await button('Clear').click(); await jump('exploratorium');
  await page.mouse.move(880,700); await page.mouse.down(); await page.mouse.move(890,410,{steps:20}); await page.mouse.up();
  await page.mouse.move(1432,945); await hold(3);
  await jump('ferry-building'); await hold(3);
  await jump('bay-bridge'); await hold(3);
  await jump('oracle-park'); await button('Rain').click();
  await page.waitForFunction(()=>window.__sf.rainDayLayer.getOpacity()>.99&&window.__sf.rainDayLayer.getFullyLoaded());
  await page.mouse.move(1432,945); await hold(4);
  await button('Night').click(); await page.waitForFunction(()=>window.__sf.rainNightLayer.getOpacity()>.99&&window.__sf.rainNightLayer.getFullyLoaded());
  await page.mouse.move(1432,945); await hold(4);
  await jump('chase-center'); await page.waitForFunction(()=>window.__sf.rainNightLayer.getFullyLoaded()); await hold(4);
  await button('Day').click(); await button('Clear').click();
  await button('Bay Area').click(); await page.waitForFunction(()=>window.__sf?.ready&&window.__sf.data.kind==='bay');
  await settle(); await button('Close environment panel').click(); await page.mouse.move(1432,945); await hold(5);
  return {recorded:'Actual corridor and Bay Area app: moving transport, continuous pan, place jumps, fog, wet day/night and regional overview.'};
}
