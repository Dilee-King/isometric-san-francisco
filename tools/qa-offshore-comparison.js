async page => {
  const sameView=async(url,path)=>{
    await page.goto(url);
    await page.waitForFunction(()=>window.__sf?.ready);
    await page.evaluate(()=>{
      const m=window.__sf;
      const [ox,oy]=m.data.projection.origin, w=m.data.width;
      const v=m.viewer.viewport;
      const ref=v.getBounds();
      ref.x=(-3520+ox)/w;ref.y=(-3100+oy)/w;
      ref.width=5310/w;ref.height=3540/w;
      v.fitBounds(ref,true);
      m.setControls({paused:true,cars:false,boats:false,planes:false});
    });
    await page.getByRole('button',{name:'Close environment panel',exact:true}).click();
    await page.waitForFunction(()=>window.__sf.viewer.world.getItemAt(0).getFullyLoaded());
    await page.evaluate(()=>new Promise(r=>{
      let n=0;const f=()=>++n>26?r(true):requestAnimationFrame(f);requestAnimationFrame(f);
    }));
    await page.mouse.move(1437,957);
    await page.screenshot({path,quality:96});
    return page.evaluate(()=>{
      const m=window.__sf,t=m.transform,[x,y]=m.data.projection.origin;
      return {release:m.data.release,scale:t.scale,x:t.left+x*t.scale,y:t.top+y*t.scale};
    });
  };
  await page.setViewportSize({width:1440,height:960});
  await page.emulateMedia({reducedMotion:'reduce'});
  const before=await sameView('http://127.0.0.1:4187/','docs/screenshots/v0.4/offshore-v03.jpg');
  const after=await sameView('http://127.0.0.1:4186/','docs/screenshots/v0.4/offshore-v04.jpg');
  if(before.release!=='waterfront-v3'||after.release!=='waterfront-v4'||Math.abs(before.x-after.x)>1||Math.abs(before.y-after.y)>1||Math.abs(before.scale-after.scale)>.0001)
    throw new Error('Camera mismatch: '+JSON.stringify({before,after}));
  return {matched:true,before,after};
}
