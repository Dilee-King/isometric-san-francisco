async page => {
  const hold=async seconds=>{const start=await page.evaluate(()=>window.__sf.frame.clock.environmentTime);await page.waitForFunction(([start,seconds])=>window.__sf.frame.clock.environmentTime>=start+seconds,[start,seconds]);};
  await page.setViewportSize({width:1440,height:960});
  await page.goto('http://127.0.0.1:4186/');
  await page.waitForFunction(()=>window.__sf?.ready&&window.__sf.rainNightLayer);
  await page.mouse.move(1430,940);
  await hold(4);
  await page.getByRole('button',{name:'Rain',exact:true}).click();
  await page.waitForFunction(()=>window.__sf.rainDayLayer.getFullyLoaded());
  await page.mouse.move(1430,940);await hold(5);
  await page.getByRole('button',{name:'Night',exact:true}).click();
  await page.waitForFunction(()=>window.__sf.rainNightLayer.getFullyLoaded());
  await page.mouse.move(1430,940);await hold(5);
  await page.getByRole('button',{name:'Clear',exact:true}).click();
  await page.mouse.move(1430,940);await hold(3);
  await page.getByRole('button',{name:'Day',exact:true}).click();
  await page.getByRole('button',{name:'Coastal fog',exact:true}).click();await page.mouse.move(1430,940);await hold(4);
  await page.getByRole('button',{name:'Clear',exact:true}).click();
  return {recorded:'Actual v0.2 production application: moving world-space transport, wet day, wet night, dry night and retained coastal fog.'};
}
