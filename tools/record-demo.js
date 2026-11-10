async page => {
  const hold=async seconds=>{const start=await page.evaluate(()=>window.__sf.frame.clock.environmentTime);await page.waitForFunction(([start,seconds])=>window.__sf.frame.clock.environmentTime>=start+seconds,[start,seconds]);};
  await page.goto('http://127.0.0.1:4186/');
  await page.waitForFunction(()=>window.__sf?.ready&&window.__sf.nightLayer);
  await page.mouse.move(1430,940);
  await hold(4);
  await page.getByRole('button',{name:'夜晚',exact:true}).click();
  await page.waitForFunction(()=>window.__sf.nightLayer.getFullyLoaded());
  await page.mouse.move(1430,940);await hold(4);
  await page.getByRole('button',{name:'下雨',exact:true}).click();await page.mouse.move(1430,940);await hold(4);
  await page.getByRole('button',{name:'白天',exact:true}).click();
  await page.getByRole('button',{name:'海雾',exact:true}).click();await page.mouse.move(1430,940);await hold(4);
  await page.getByRole('button',{name:'晴朗',exact:true}).click();
  return {recorded:'actual production application; moving traffic, authored night, rain and fog'};
}
