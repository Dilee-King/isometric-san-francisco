import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=new URL('../',import.meta.url);
const map=new URL('public/map/v2/',root);
const manifest=JSON.parse(await readFile(new URL('manifest.json',map),'utf8'));
const scene=JSON.parse(await readFile(new URL('scene.json',map),'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const item of manifest.files){
  const bytes=await readFile(new URL(item.path,map));
  if(sha(bytes)!==item.sha256)throw new Error('Asset checksum mismatch: '+item.path);
}
for(const appearance of manifest.appearances){
  const bytes=await readFile(new URL(appearance.asset,root));
  if(sha(bytes)!==appearance.sha256)throw new Error(appearance.stem+' artwork checksum mismatch');
  if(bytes.readUInt32BE(16)!==scene.width||bytes.readUInt32BE(20)!==scene.height)throw new Error(appearance.stem+' image dimensions differ from projection');
}
if(manifest.appearances.length!==4)throw new Error('Dry/wet day/night set incomplete');
if(scene.routes.filter(r=>r.kind==='plane').length!==1||scene.routes.filter(r=>r.kind==='ferry').length!==2)throw new Error('Transport scene incomplete');
console.log(`Asset audit passed: ${manifest.files.length} runtime assets, four appearances, shared ${scene.width}×${scene.height} projection.`);
