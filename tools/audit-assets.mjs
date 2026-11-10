import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=new URL('../',import.meta.url);
const manifest=JSON.parse(await readFile(new URL('public/map/v1/manifest.json',root),'utf8'));
const scene=JSON.parse(await readFile(new URL('public/map/v1/scene.json',root),'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const item of manifest.files){
  const bytes=await readFile(new URL('public/map/v1/'+item.path,root));
  if(sha(bytes)!==item.sha256)throw new Error('Tile checksum mismatch: '+item.path);
}
for(const [name,expected] of [['day',manifest.originalArtworkSHA256],['night',manifest.nightArtworkSHA256]]){
  const bytes=await readFile(new URL(`assets/waterfront-${name}.png`,root));
  if(sha(bytes)!==expected)throw new Error(name+' artwork checksum mismatch');
  if(bytes.readUInt32BE(16)!==scene.width||bytes.readUInt32BE(20)!==scene.height)throw new Error(name+' image dimensions differ from projection');
}
if(scene.routes.filter(r=>r.kind==='plane').length!==1||scene.routes.filter(r=>r.kind==='ferry').length!==2)throw new Error('Transport scene incomplete');
console.log(`Asset audit passed: ${manifest.files.length} DZI tiles, two original appearances, shared ${scene.width}×${scene.height} projection.`);
