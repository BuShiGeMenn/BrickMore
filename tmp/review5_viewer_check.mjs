
import * as THREE from 'three';
import {OrbitControls} from './static/OrbitControls.js';
const rows=await(await fetch('manifest.json')).json();
const host=document.querySelector('#viewer'),scene=new THREE.Scene();scene.background=new THREE.Color('#e9edf2');
const camera=new THREE.PerspectiveCamera(35,1,.1,10000),renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;host.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
scene.add(new THREE.HemisphereLight(0xffffff,0x8191a6,2.1));
for(const [x,y,z,p] of [[40,70,35,3],[-40,30,-15,1.2]]){let light=new THREE.DirectionalLight(0xffffff,p);light.position.set(x,y,z);scene.add(light)}
let model=null,current=null,raw=false,serial=0;
const material=new THREE.MeshStandardMaterial({color:0xe8b42b,roughness:.36,metalness:0});
const studGeo=new THREE.CylinderGeometry(.24,.24,.2,16);
function resize(){const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}
new ResizeObserver(resize).observe(host);resize();
function clean(){if(!model)return;scene.remove(model);model.traverse(o=>{if(o.geometry&&o.geometry!==studGeo)o.geometry.dispose()})}
async function show(row,reset=true){current=row;const ticket=++serial;
document.querySelector('#title').textContent=row.category+' · L'+row.level+' · Seed '+row.seed;
document.querySelector('#prompt').textContent=row.prompt;
document.querySelector('#stats').textContent=(row.validation?'几何通过 · '+row.validation.brick_count+' 块砖 · '+row.validation.occupied_voxels+' 个占用格 · 单一凸点连通':'几何检查未通过，保留原始结果')+' · 外形待人工复审';
document.querySelector('#status').textContent=raw?'原始生成排砖':'保形重铺 / 最终几何';
document.querySelector('#toggle').textContent=raw?'查看最终几何':'查看原始排砖';
document.querySelectorAll('.card').forEach(c=>c.classList.toggle('selected',c.dataset.id===row.id));
const links=document.querySelector('#links');links.replaceChildren();
for(const [file,label]of [['model.ldr','下载 LDR'],['model.glb','下载 GLB'],['model.txt','下载排砖 TXT'],['raw.txt','模型原始输出'],['validation.json','检查记录'],['raw_report.json','原始检查']]){if(!row.validation&&(file.startsWith('model')||file==='validation.json'))continue;let a=document.createElement('a');a.href=row.folder+'/'+file;a.textContent=label;a.download='';links.append(a)}
let f=raw?'raw_geometry.json':(row.validation?'model.json':'raw_geometry.json');
const {bricks}=await(await fetch(row.folder+'/'+f)).json();if(ticket!==serial)return;
clean();model=new THREE.Group();const cells=new Set();for(const b of bricks)for(let x=b.x;x<b.x+b.h;x++)for(let y=b.y;y<b.y+b.w;y++)cells.add(`${x},${y},${b.z}`);
for(const b of bricks){let body=new THREE.Mesh(new THREE.BoxGeometry(b.h-.028,1.188,b.w-.028),material);body.position.set(b.x+b.h/2,(b.z+.5)*1.2,b.y+b.w/2);model.add(body);
for(let x=b.x;x<b.x+b.h;x++)for(let y=b.y;y<b.y+b.w;y++){if(cells.has(`${x},${y},${b.z+1}`))continue;let s=new THREE.Mesh(studGeo,material);s.position.set(x+.5,(b.z+1)*1.2+.1,y+.5);model.add(s)}}
let box=new THREE.Box3().setFromObject(model),center=box.getCenter(new THREE.Vector3());model.position.sub(center);scene.add(model);
if(reset){let size=box.getSize(new THREE.Vector3()),r=Math.max(size.x,size.y,size.z);camera.position.set(r*1.7,r*1.25,r*1.9);controls.target.set(0,0,0);controls.update()}}
for(const row of rows){const button=document.createElement('button');button.className='card';button.dataset.id=row.id;const img=document.createElement('img');img.src=row.folder+'/'+(row.preview_image||'preview.png');const label=document.createElement('span'),strong=document.createElement('strong'),small=document.createElement('small');strong.textContent=row.category+' · L'+row.level;small.textContent=(row.id.endsWith('_G')?'确定性解码':'Seed '+row.seed)+(row.source_candidate_id.startsWith('reconstructed-')?' · 新构造提示词':(row.source_candidate_id.startsWith('dataset-')?' · dataset 同级文本':(row.current_prompt?' · 当前提示词':' · 原同级备选')));label.append(strong,small);button.append(img,label);button.onclick=()=>{raw=false;show(row)};document.querySelector('#cards').append(button)}
document.querySelector('#toggle').onclick=()=>{raw=!raw;show(current,false)};
if(rows.length)await show(rows[0]);
renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera)});
