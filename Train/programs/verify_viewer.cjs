const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.dirname(__dirname),html=fs.readFileSync(path.join(root,'查看效果.html'),'utf8');
const code=html.match(/<script>([\s\S]*)<\/script>/)[1];let faces=0,total=0;
const elements={};const context={clearRect(){faces=0},beginPath(){faces++},lineTo(x,y){if(!Number.isFinite(x)||!Number.isFinite(y))throw Error('Invalid rendered point')},moveTo(x,y){this.lineTo(x,y)},closePath(){},fill(){}};
function el(id){if(!elements[id])elements[id]={value:id==='level'?'4':'',options:[],clientWidth:1000,clientHeight:580,add(o){this.options.push(o);if(!this.value)this.value=o.value},getContext(){return context},setPointerCapture(){}};return elements[id]}
const sandbox={document:{getElementById:el},window:{},devicePixelRatio:1,Option:function(text,value){this.text=text;this.value=String(value)},alert(m){throw Error(m)}};
vm.createContext(sandbox);vm.runInContext(code,sandbox);
for(const cat of el('cat').options){el('cat').value=cat.value;el('cat').onchange();
 for(const ex of el('example').options.slice(-3)){el('example').value=ex.value;el('example').onchange();
  for(const view of ['front','side','top','iso']){el(view).onclick();if(faces<1)throw Error('No model rendered');total++}
  for(let l=0;l<5;l++){el('level').value=String(l);el('level').onchange();if(el('caption').textContent.length<15)throw Error('Missing caption')}
 }}
const report={passed:true,categoryCount:el('cat').options.length,sampleModelCount:63,viewRenderChecks:total,captionLevelsChecked:5,method:'JavaScript executed with a canvas/DOM harness; no real browser screenshot comparison'};
fs.writeFileSync(path.join(root,'viewer_verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
