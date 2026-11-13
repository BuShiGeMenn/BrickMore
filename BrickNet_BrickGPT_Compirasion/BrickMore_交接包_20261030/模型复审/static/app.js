import * as THREE from 'three';
import { GLTFLoader } from '/assets/js/GLTFLoader.js';
import { DRACOLoader } from '/assets/js/DRACOLoader.js';
import { OrbitControls } from '/assets/js/OrbitControls.js';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const STORE = 'brickmore-review-v1';
let catalog, state, index = 0, dirty = false, saveTimer, savePromise, saveBlocked = false, changeVersion = 0;
let viewers = [], modalViewer = null, modalItem = null, modalSource = null, returnFocus = null, toastTimer;
let renderer, syncing = false;
const cache = new Map();
const brickMaterial = new THREE.MeshStandardMaterial({color:0xf2cd37,roughness:.52,metalness:0});
const shadowMaterial = new THREE.ShadowMaterial({opacity:.14});
const groundGeometry = new THREE.PlaneGeometry(1,1);
const draco = new DRACOLoader().setDecoderPath('/assets/js/draco/').setWorkerLimit(2);
const loader = new GLTFLoader().setDRACOLoader(draco);
const pad = n => String(n).padStart(2,'0');
const group = () => catalog.groups[index];

function toast(message) {
  $('#toast').textContent = message; $('#toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 3600);
}
function status(text, error = false) {
  $('#save-text').textContent = text; $('#save-status').classList.toggle('error',error);
}
function remember() {
  try { localStorage.setItem(STORE,JSON.stringify({revision:state.revision,decisions:state.decisions,dirty})); }
  catch { /* 文件保存与导出仍可使用。 */ }
}
function changed() {
  dirty = true; changeVersion++; remember(); status('正在保存…');
  clearTimeout(saveTimer); saveTimer = setTimeout(() => flushSave(),350);
}
async function flushSave() {
  if (savePromise) { await savePromise; return dirty && !saveBlocked ? flushSave() : !dirty; }
  if (!dirty || saveBlocked) return !dirty;
  const version = changeVersion;
  const payload = JSON.stringify({revision:state.revision,decisions:state.decisions});
  savePromise = (async () => {
    try {
      const response = await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:payload});
      const saved = await response.json();
      if (!response.ok) {
        if (response.status === 409) saveBlocked = true;
        throw new Error(saved.error || '保存失败');
      }
      state.revision = saved.revision; state.updated_at = saved.updated_at;
      if (version === changeVersion) dirty = false;
      remember(); status(dirty ? '正在保存…' : '已保存到本地文件');
      return true;
    } catch (error) {
      status(saveBlocked ? '保存冲突 · 请先导出备份' : '保存失败 · 可导出备份',true);
      console.error('Review save failed',error); return false;
    } finally { savePromise = null; }
  })();
  const result = await savePromise;
  return result && dirty ? flushSave() : result;
}

function decision(key = group().key) { return state.decisions[key]; }
function setDecision(kind, id = null) {
  const key = group().key;
  state.decisions[key] = {status:kind,candidate_id:id,note:decision()?.note || ''};
  changed(); updateDecisions();
}
function updateDecisions() {
  const d = decision();
  for (const card of document.querySelectorAll('.candidate-card')) {
    const selected = d?.status === 'selected' && d.candidate_id === card.dataset.id;
    card.classList.toggle('selected',selected);
    const button = card.querySelector('.choose-button');
    button.setAttribute('aria-pressed',String(selected));
    button.innerHTML = `<span class="radio-mark">${selected ? '✓' : ''}</span>${selected ? '已选为本组最佳' : '选为本组最佳'}`;
  }
  const rejected = d?.status === 'regenerate';
  $('.decision-panel').classList.toggle('rejected',rejected);
  $('#reject-group').textContent = rejected ? '✓ 已标记：需重新生成' : '全部不合格，需重生成';
  $('#reject-group').setAttribute('aria-pressed',String(rejected));
  const label = $('#decision-summary');
  label.className = d?.status === 'selected' ? 'done' : rejected ? 'rejected' : '';
  label.textContent = d?.status === 'selected' ? `✓ 已选择 ${d.candidate_id}` : rejected ? '↻ 本组全部不合格，待重新生成' : '本组尚未选择';
  $('#clear-group').disabled = !d || d.status === 'pending';
  let count = 0;
  for (const g of catalog.groups) {
    const current = state.decisions[g.key];
    const done = ['selected','regenerate'].includes(current?.status);
    if (done) count++;
    const button = document.querySelector(`.nav-group[data-key="${g.key}"]`);
    button.classList.toggle('active',g.key === group().key);
    button.setAttribute('aria-current',g.key === group().key ? 'step' : 'false');
    const mark = button.querySelector('.nav-state');
    mark.className = `nav-state ${current?.status || 'pending'}`;
    mark.textContent = current?.status === 'selected' ? '✓' : current?.status === 'regenerate' ? '↻' : '·';
    button.title = `${g.name} L${g.level} · ${current?.status === 'selected' ? '已选择' : current?.status === 'regenerate' ? '需重生成' : '待复审'}`;
  }
  $('#progress-label').textContent = `${count} / ${catalog.groups.length} 已复审`;
  $('#progress-percent').textContent = `${Math.round(count/catalog.groups.length*100)}%`;
  $('#progress-fill').style.width = `${count/catalog.groups.length*100}%`;
}

function disposeViewer(v) { v.dead = true; v.token++; v.controls.dispose(); }
function showGroup(next, scroll = true) {
  if (modalViewer) closeModal();
  viewers.forEach(disposeViewer); viewers = [];
  index = Math.max(0,Math.min(catalog.groups.length-1,next));
  const g = group();
  history.replaceState(null,'',`#${g.key}`);
  $('#group-counter').textContent = `${pad(index+1)} / ${pad(catalog.groups.length)}`;
  $('#group-title').innerHTML = `${esc(g.name)}<span class="en">${esc(g.category)}</span><span class="level">L${g.level} · ${esc(g.level_name)}</span>`;
  $('#group-subtitle').textContent = '比较已有造型，重新确认这一组的最佳模型。';
  $('#criterion').textContent = g.criterion;
  $('#candidate-count').textContent = `${g.candidates.length} 个已有候选`;
  $('#prev-group').disabled = index === 0; $('#next-group').disabled = index === catalog.groups.length-1;
  $('#continue-group').textContent = index === catalog.groups.length-1 ? '查看复审进度 ✓' : '下一组 →';
  const notice = $('#group-notice'); notice.hidden = false;
  if (g.candidates.length === 1) notice.textContent = '本包只有当前这一个模型，可确认保留，或标记“全部不合格，需重生成”。';
  else if (g.category === 'car') notice.textContent = '汽车试作在三个汽车组中共享；带有其他等级提示词的候选已单独标注，请对照本组目标判断。';
  else notice.hidden = true;
  const grid = $('#candidates');
  grid.className = `candidate-grid ${g.candidates.length === 1 ? 'one' : g.candidates.length === 2 ? 'two' : ''}`;
  grid.replaceChildren();
  for (const [n,item] of g.candidates.entries()) {
    const differentLevel = item.hint_level != null && item.hint_level !== g.level;
    const badge = item.current ? '当前采用' : differentLevel ? `原提示词 L${item.hint_level}` : item.hint_level == null ? '未标等级试作' : '已有备选';
    const card = document.createElement('article'); card.className = 'candidate-card'; card.dataset.id = item.id;
    card.setAttribute('aria-label',item.id);
    card.innerHTML = `<div class="card-top"><span class="candidate-number">CANDIDATE ${pad(n+1)}</span><span class="chip ${item.current ? 'current' : differentLevel ? 'warn' : ''}">${badge}</span></div>
      <div class="model-viewport" data-state="loading" aria-label="${esc(item.id)} 三维预览"><span class="load-status" role="status">加载模型中…</span></div>
      <div class="card-view-controls"><div class="version-tabs" aria-label="模型版本"><button data-kind="raw" class="active" aria-pressed="true">原版</button><button data-kind="stitched" aria-pressed="false" ${item.stitched_glb ? '' : 'disabled title="此模型没有重铺版"'}>重铺版</button></div><button class="expand-button" aria-label="放大查看 ${esc(item.id)}">⛶ 放大</button></div>
      <div class="card-info"><div class="card-id">${esc(item.id)}</div><div class="card-source">${esc(item.source_zh)} · ${item.stitched_glb ? '可切换重铺版' : '仅有原版'}</div>
      ${differentLevel ? `<p class="level-warning">原提示词为 L${item.hint_level}，与本组 L${g.level} 不同。</p>` : ''}
      <details><summary>查看生成提示词</summary>${item.prompt_zh ? `<p>${esc(item.prompt_zh)}</p>` : ''}<p lang="en">${esc(item.prompt || '未记录英文提示词')}</p></details>
      <button class="choose-button" aria-pressed="false"><span class="radio-mark"></span>选为本组最佳</button></div>`;
    grid.append(card);
    const v = makeViewer(card.querySelector('.model-viewport'),item);
    viewers.push(v);
    for (const button of card.querySelectorAll('button[data-kind]')) button.onclick = () => {
      const kind = button.dataset.kind;
      for (const other of card.querySelectorAll('button[data-kind]')) {
        other.classList.toggle('active',other === button); other.setAttribute('aria-pressed',String(other === button));
      }
      v.load(kind);
    };
    card.querySelector('.expand-button').onclick = () => openModal(item,v);
    card.querySelector('.choose-button').onclick = () => setDecision('selected',item.id);
  }
  $('#review-note').value = decision()?.note || '';
  updateDecisions();
  if (scroll) window.scrollTo({top:window.innerWidth <= 780 ? $('.sidebar').offsetHeight : 0,behavior:'instant'});
}

function asset(path) {
  if (!cache.has(path)) {
    const promise = loader.loadAsync('/'+path).then(gltf => gltf.scene).catch(error => {cache.delete(path);throw error;});
    cache.set(path,promise);
  }
  return cache.get(path);
}
function copyView(source,target) {
  if (!source.model || !target.model) return;
  const offset = source.camera.position.clone().sub(source.controls.target).divideScalar(source.size);
  const pan = source.controls.target.clone().sub(source.center).divideScalar(source.size);
  target.controls.target.copy(target.center).addScaledVector(pan,target.size);
  target.camera.position.copy(target.controls.target).addScaledVector(offset,target.size);
  target.controls.update();
}
function makeViewer(holder,item,kind = 'raw') {
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0xc4c6c2);
  const camera = new THREE.PerspectiveCamera(38,4/3,.1,100000);
  scene.add(new THREE.HemisphereLight(0xffffff,0xaca798,1.5));
  const key = new THREE.DirectionalLight(0xfff8e8,2.1);
  key.castShadow = true; key.shadow.mapSize.set(512,512); key.shadow.bias = -.0002;
  scene.add(key,key.target);
  const fill = new THREE.DirectionalLight(0xc8d8ed,.55); fill.position.set(-2,2,-3); scene.add(fill);
  const ground = new THREE.Mesh(groundGeometry,shadowMaterial); ground.rotation.x = -Math.PI/2; ground.receiveShadow = true; scene.add(ground);
  const controls = new OrbitControls(camera,holder); controls.enableDamping = true; controls.dampingFactor = .12;
  controls.minPolarAngle = .05; controls.maxPolarAngle = Math.PI*.91;
  const v = {holder,item,scene,camera,controls,key,ground,kind,dead:false,token:0,center:new THREE.Vector3(),size:1,model:null};
  v.fit = () => {
    if (!v.model) return;
    const box = new THREE.Box3().setFromObject(v.model); const size = box.getSize(new THREE.Vector3());
    v.center.copy(box.getCenter(new THREE.Vector3())); v.size = Math.max(size.x,size.y,size.z,.001);
    const rect = holder.getBoundingClientRect();
    const aspect = Math.max(rect.width/Math.max(rect.height,1),.5);
    const distance = v.size/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)))*1.35/Math.min(aspect,1);
    camera.near = v.size/100; camera.far = v.size*100;
    camera.position.copy(v.center).addScaledVector(new THREE.Vector3(.85,.66,1).normalize(),distance);
    controls.target.copy(v.center); camera.lookAt(v.center); camera.updateProjectionMatrix(); controls.update();
    controls.minDistance = v.size*.35; controls.maxDistance = v.size*12;
    key.position.copy(v.center).addScaledVector(new THREE.Vector3(.5,1,.65).normalize(),v.size*3);
    key.target.position.copy(v.center);
    const sc = key.shadow.camera; sc.left = sc.bottom = -v.size; sc.right = sc.top = v.size;
    sc.near = v.size*.2; sc.far = v.size*8; sc.updateProjectionMatrix();
    key.shadow.normalBias = Math.max(.01,v.size*.004);
    ground.position.set(v.center.x,box.min.y-.005*v.size,v.center.z); ground.scale.setScalar(v.size*10);
  };
  v.load = async next => {
    const path = next === 'raw' ? item.glb : item.stitched_glb;
    if (!path) return;
    const token = ++v.token; v.kind = next;
    const label = holder.querySelector('.load-status');
    label.hidden = false; label.classList.remove('failed'); label.textContent = '加载模型中…'; holder.dataset.state = 'loading';
    if (!renderer) { label.textContent = '当前浏览器无法启用三维渲染'; label.classList.add('failed'); holder.dataset.state = 'failed'; return; }
    try {
      const cached = await asset(path);
      if (v.dead || token !== v.token) return;
      if (v.model) scene.remove(v.model);
      v.model = cached.clone(true);
      v.model.traverse(o => {if (o.isMesh) {o.material = brickMaterial;o.castShadow = true;o.receiveShadow = false;}});
      scene.add(v.model); v.fit(); label.hidden = true; holder.dataset.state = 'ready'; holder.dataset.kind = next;
      if ($('#sync-views').checked && viewers[0] && viewers[0] !== v) {
        syncing = true; copyView(viewers[0],v); syncing = false;
      }
    } catch (error) {
      if (v.dead || token !== v.token) return;
      label.textContent = '模型加载失败，请重试切换或刷新'; label.classList.add('failed'); holder.dataset.state = 'failed';
      console.error('GLB load failed',path,error);
    }
  };
  controls.addEventListener('change',() => {
    if (syncing || modalViewer || !$('#sync-views').checked || !v.model) return;
    syncing = true; for (const other of viewers) if (other !== v && !other.dead) copyView(v,other); syncing = false;
  });
  v.load(kind);
  return v;
}

function render() {
  requestAnimationFrame(render);
  if (!renderer || document.hidden) return;
  const width = document.documentElement.clientWidth, height = window.innerHeight;
  renderer.setSize(width,height,false); renderer.setScissorTest(false);
  // Scene.background 会改变 clear color;每帧先恢复透明，避免盖住页面文字。
  renderer.setClearColor(0x000000,0); renderer.clear(true,true,true); renderer.setScissorTest(true);
  const topLimit = modalViewer ? 0 : $('.topbar').getBoundingClientRect().bottom;
  for (const v of modalViewer ? [modalViewer] : viewers) {
    if (v.dead) continue;
    const rect = v.holder.getBoundingClientRect();
    const top = Math.max(rect.top,topLimit), bottom = Math.min(rect.bottom,height), left = Math.max(0,rect.left), right = Math.min(width,rect.right);
    if (bottom <= top || right <= left || rect.width < 2) continue;
    renderer.setViewport(rect.left,height-rect.bottom,rect.width,rect.height);
    renderer.setScissor(left,height-bottom,right-left,bottom-top);
    v.camera.aspect = rect.width/rect.height; v.camera.updateProjectionMatrix(); v.controls.update();
    renderer.clearDepth(); renderer.render(v.scene,v.camera);
  }
}

function openModal(item,source) {
  returnFocus = document.activeElement; modalItem = item; modalSource = source;
  $('#model-modal').hidden = false; document.body.classList.add('modal-open'); $('.app-shell').inert = true;
  $('#modal-title').textContent = item.id;
  $('#modal-caption').textContent = `${item.source_zh} · 拖动旋转，滚轮缩放 · Esc 关闭`;
  modalViewer = makeViewer($('#modal-viewport'),item,source.kind);
  for (const button of $('#modal-version').querySelectorAll('button')) {
    button.disabled = button.dataset.kind === 'stitched' && !item.stitched_glb;
    button.classList.toggle('active',button.dataset.kind === source.kind);
    button.setAttribute('aria-pressed',String(button.dataset.kind === source.kind));
  }
  $('.modal-panel').focus();
}
function closeModal() {
  if (modalViewer) disposeViewer(modalViewer);
  modalViewer = null; modalItem = null; modalSource = null;
  $('#model-modal').hidden = true; document.body.classList.remove('modal-open'); $('.app-shell').inert = false;
  returnFocus?.focus();
}

function exportData() {
  const decisions = {};
  for (const g of catalog.groups) {
    const d = state.decisions[g.key] || {status:'pending',candidate_id:null,note:''};
    const item = g.candidates.find(e => e.id === d.candidate_id);
    decisions[g.key] = {...d,category:g.category,level:g.level,current_id:g.current_id,
      raw_glb:item?.glb || null,stitched_glb:item?.stitched_glb || null,
      source_level:item?.hint_level ?? null,source_zh:item?.source_zh || null};
  }
  return {schema_version:1,exported_at:new Date().toISOString(),revision:state.revision,
    complete:Object.values(decisions).every(d => d.status !== 'pending'),decisions,
    picks:Object.fromEntries(Object.entries(decisions).map(([k,d]) => [k,d.candidate_id])),
    pending_groups:Object.keys(decisions).filter(k => decisions[k].status === 'pending'),
    regenerate_groups:Object.keys(decisions).filter(k => decisions[k].status === 'regenerate')};
}
function download(name,content,type) {
  const url = URL.createObjectURL(new Blob([content],{type}));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}
function csvCell(value) { return '"'+String(value ?? '').replaceAll('"','""')+'"'; }

async function init() {
  try {
    const [catalogResponse,stateResponse] = await Promise.all([fetch('/api/catalog'),fetch('/api/review')]);
    if (!catalogResponse.ok || !stateResponse.ok) throw new Error('无法读取模型目录或复审文件');
    catalog = await catalogResponse.json(); state = await stateResponse.json();
    const local = JSON.parse(localStorage.getItem(STORE) || 'null');
    if (local?.dirty && local.revision === state.revision) {
      const allowed = new Set(catalog.groups.map(g => g.key));
      const valid = Object.entries(local.decisions || {}).every(([key,d]) => allowed.has(key) &&
        ['selected','pending','regenerate'].includes(d.status) && (d.status !== 'selected' || catalog.groups.find(g => g.key === key).candidates.some(e => e.id === d.candidate_id)));
      if (valid) {state.decisions = local.decisions;dirty = true;}
    }
  } catch (error) {
    $('#workspace').innerHTML = `<div class="fatal">无法打开复审工作台：${esc(error.message)}<br>请确认 Python 服务正在运行，并通过 http://127.0.0.1:8130/ 访问。</div>`;
    status('读取失败',true); console.error(error); return;
  }
  try {
    renderer = new THREE.WebGLRenderer({canvas:$('#renderer'),antialias:true,alpha:true});
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1,1.5)); renderer.setClearColor(0x000000,0);
    renderer.autoClear = false; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  } catch (error) {
    const message = document.createElement('p'); message.className = 'notice webgl-error';
    message.textContent = '三维渲染未能启动，请使用支持 WebGL 的浏览器，或检查浏览器图形加速。'; $('#workspace').prepend(message); console.error(error);
  }
  $('#group-nav').innerHTML = catalog.groups.map((g,i) => `<button class="nav-group" data-key="${g.key}"><span class="nav-index">${pad(i+1)}</span><span class="nav-title">${esc(g.name)} <span style="color:#7f8b9d;font-weight:400">L${g.level}</span><small>${esc(g.category)} · ${esc(g.level_name)}</small></span><span class="nav-state pending">·</span></button>`).join('');
  for (const [i,button] of [...$('#group-nav').children].entries()) button.onclick = () => showGroup(i);
  $('#prev-group').onclick = () => showGroup(index-1);
  $('#next-group').onclick = () => showGroup(index+1);
  $('#continue-group').onclick = () => {
    if (index < catalog.groups.length-1) return showGroup(index+1);
    const left = catalog.groups.filter(g => !['selected','regenerate'].includes(state.decisions[g.key]?.status));
    toast(left.length ? `还有 ${left.length} 组待复审：${left.map(g=>g.name+' L'+g.level).join('、')}` : '7 组复审已完成，可导出选择结果。');
  };
  $('#reject-group').onclick = () => setDecision('regenerate');
  $('#clear-group').onclick = () => {
    const note = decision()?.note || '';
    if (note) state.decisions[group().key] = {status:'pending',candidate_id:null,note};
    else delete state.decisions[group().key];
    changed(); updateDecisions();
  };
  $('#review-note').oninput = event => {
    const d = decision() || {status:'pending',candidate_id:null};
    state.decisions[group().key] = {...d,note:event.target.value}; changed();
  };
  $('#reset-views').onclick = () => {syncing = true;viewers.forEach(v=>v.fit());syncing = false;};
  $('#sync-views').onchange = event => {
    if (event.target.checked && viewers[0]) {syncing=true;viewers.slice(1).forEach(v=>copyView(viewers[0],v));syncing=false;}
  };
  $('#modal-close').onclick = closeModal; $('.modal-backdrop').onclick = closeModal;
  for (const button of $('#modal-version').querySelectorAll('button')) button.onclick = () => {
    for (const other of $('#modal-version').querySelectorAll('button')) {
      other.classList.toggle('active',other === button);other.setAttribute('aria-pressed',String(other === button));
    }
    modalViewer?.load(button.dataset.kind);
  };
  $('#modal-select').onclick = () => {if(modalItem){setDecision('selected',modalItem.id);closeModal();}};
  document.addEventListener('keydown',event => {
    if (!modalViewer) return;
    if (event.key === 'Escape') {event.preventDefault();closeModal();}
    if (event.key === 'Tab') {
      const buttons = [...$('.modal-panel').querySelectorAll('button:not(:disabled)')];
      const first = buttons[0], last = buttons.at(-1);
      if (event.shiftKey && (document.activeElement === first || document.activeElement === $('.modal-panel'))) {event.preventDefault();last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault();first.focus();}
    }
  });
  $('#export-json').onclick = async () => {
    await flushSave();
    download('picks_review_7组.json',JSON.stringify(exportData(),null,2)+'\n','application/json;charset=utf-8');
    toast(dirty ? '已导出当前选择备份，本地文件尚未保存成功。' : '已导出复审选择 JSON');
  };
  $('#export-csv').onclick = async () => {
    await flushSave();
    const rows = [['group','status','candidate_id','source_level','raw_glb','stitched_glb','note']];
    for (const [key,d] of Object.entries(exportData().decisions)) rows.push([key,d.status,d.candidate_id,d.source_level,d.raw_glb,d.stitched_glb,d.note]);
    download('模型复审清单.csv','\ufeff'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n'),'text/csv;charset=utf-8');toast('已导出七组复审清单');
  };
  window.addEventListener('beforeunload',event => {if(dirty){event.preventDefault();event.returnValue='';}});
  const initial = catalog.groups.findIndex(g => g.key === decodeURIComponent(location.hash.slice(1)));
  showGroup(initial < 0 ? 0 : initial,false); render();
  if (dirty) flushSave(); else status(state.revision ? '已保存到本地文件' : '选择后自动保存');
}

init();
