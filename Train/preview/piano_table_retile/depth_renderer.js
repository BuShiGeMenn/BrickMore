// Opaque rectangular bodies use a per-pixel depth buffer. Whole-face painter
// sorting cannot represent occlusion between long faces and small nearer parts.
const previewGpuStates=new WeakMap();
const previewFaces=[
 {n:[1,0,0],v:[[1,0,0],[1,0,1],[1,1,1],[1,1,0]],shade:.80},
 {n:[-1,0,0],v:[[0,0,1],[0,0,0],[0,1,0],[0,1,1]],shade:.80},
 {n:[0,1,0],v:[[0,1,0],[1,1,0],[1,1,1],[0,1,1]],shade:1},
 {n:[0,-1,0],v:[[0,0,1],[1,0,1],[1,0,0],[0,0,0]],shade:.62},
 {n:[0,0,1],v:[[1,0,1],[0,0,1],[0,1,1],[1,1,1]],shade:.67},
 {n:[0,0,-1],v:[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],shade:.67}
];
function key(x,y,z){return `${x},${y},${z}`}
function projection(x,y,z){
 const height=Number($('proportion').value),s=Math.sin(yaw),c=Math.cos(yaw),sp=Math.sin(pitch),cp=Math.cos(pitch);
 y*=height;return [x*c-z*s,-y*cp+(x*s+z*c)*sp,(x*s+z*c)*cp+y*sp];
}
function previewGpu(canvas){
 if(previewGpuStates.has(canvas))return previewGpuStates.get(canvas);
 const gl=canvas.getContext('webgl',{alpha:false,antialias:true,depth:true,preserveDrawingBuffer:true});
 if(!gl)throw Error('浏览器无法启用三维预览，请使用支持 WebGL 的浏览器。');
 function shader(type,text){const s=gl.createShader(type);gl.shaderSource(s,text);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
 const vertex=shader(gl.VERTEX_SHADER,`
 attribute vec3 aPosition;attribute vec3 aColor;
 uniform vec2 uAngles,uViewport,uCenter,uDepth;uniform float uScale,uHeight;
 varying vec3 vColor;
 void main(){
  float s=sin(uAngles.x),c=cos(uAngles.x),sp=sin(uAngles.y),cp=cos(uAngles.y);
  vec3 p=aPosition;p.y*=uHeight;
  float x=p.x*c-p.z*s,z=p.x*s+p.z*c;
  float y=-p.y*cp+z*sp,d=z*cp+p.y*sp;
  gl_Position=vec4((x-uCenter.x)*uScale*2.0/uViewport.x,-(y-uCenter.y)*uScale*2.0/uViewport.y,-(d-uDepth.x)/uDepth.y,1.0);
  vColor=aColor;
 }`);
 const fragment=shader(gl.FRAGMENT_SHADER,`
 precision mediump float;varying vec3 vColor;uniform float uOpacity;
 void main(){gl_FragColor=vec4(vColor,uOpacity);}`);
 const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
 if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
 gl.deleteShader(vertex);gl.deleteShader(fragment);
 const uniforms=Object.fromEntries(['Angles','Viewport','Center','Depth','Scale','Height','Opacity'].map(n=>[n,gl.getUniformLocation(program,'u'+n)]));
 const state={gl,program,uniforms,position:gl.getAttribLocation(program,'aPosition'),color:gl.getAttribLocation(program,'aColor'),model:null,mode:null,studs:null,mesh:null};
 previewGpuStates.set(canvas,state);canvas.dataset.renderer='webgl-depth-v2';
 canvas.addEventListener('webglcontextlost',e=>e.preventDefault());
 canvas.addEventListener('webglcontextrestored',()=>{previewGpuStates.delete(canvas);schedule()});
 return state;
}
function previewRgb(c,shade=1){return [c>>16&255,c>>8&255,c&255].map(v=>Math.min(1,Math.max(0,v*shade/255)))}
function previewMesh(model,mode,studs){
 const source=mode==='source'||mode==='target',cells=mode==='source'?model.source:model.target;
 const objects=source?cells.map(p=>[...p.slice(0,3),1,1,1,p[3],0]):mode==='before'?model.beforeBricks:model.bricks;
 const occupied=new Set(cells.map(p=>key(...p.slice(0,3)))),owner=new Set();
 if(!source)for(const b of objects)for(let x=b[0];x<b[0]+b[3];x++)for(let z=b[2];z<b[2]+b[5];z++)owner.add(key(x,b[1],z));
 const fill=[],lines=[];let faceCount=0;
 function vertex(array,p,c){array.push(...p,...c)}
 function triangle(a,b,c,rgb){vertex(fill,a,rgb);vertex(fill,b,rgb);vertex(fill,c,rgb)}
 function line(a,b,rgb=[.075,.105,.13]){vertex(lines,a,rgb);vertex(lines,b,rgb)}
 function face(vertices,rgb){triangle(vertices[0],vertices[1],vertices[2],rgb);triangle(vertices[0],vertices[2],vertices[3],rgb);faceCount++}
 for(const b of objects){
  const [x,y,z,dx,dy,dz,c,bad]=b,paint=(mode==='risk'||mode==='before')&&bad?0xdf6372:c;
  for(const f of previewFaces){
   if(source&&occupied.has(key(x+f.n[0],y+f.n[1],z+f.n[2])))continue;
   const points=f.v.map(p=>[x+p[0]*dx,y+p[1]*dy,z+p[2]*dz]);face(points,previewRgb(paint,f.shade));
   if(source)for(let i=0;i<4;i++)line(points[i],points[(i+1)%4]);
  }
  if(!source){
   const corners=[];for(let i=0;i<8;i++)corners.push([x+(i&1?dx:0),y+(i&2?dy:0),z+(i&4?dz:0)]);
   for(let i=0;i<8;i++)for(const bit of [1,2,4])if(!(i&bit))line(corners[i],corners[i|bit]);
  }
  if(!source&&studs){
   for(let sx=x;sx<x+dx;sx++)for(let sz=z;sz<z+dz;sz++){
    if(owner.has(key(sx,y+dy,sz)))continue;
    const top=[],bottom=[],segments=16,center=[sx+.5,y+dy+.16,sz+.5];
    for(let i=0;i<segments;i++){const a=i*2*Math.PI/segments,px=sx+.5+Math.cos(a)*.24,pz=sz+.5+Math.sin(a)*.24;top.push([px,center[1],pz]);bottom.push([px,y+dy,pz])}
    for(let i=0;i<segments;i++){
     const j=(i+1)%segments;triangle(center,top[i],top[j],previewRgb(paint,1.08));
     face([bottom[i],bottom[j],top[j],top[i]],previewRgb(paint,.75+.12*Math.cos((i+.5)*2*Math.PI/segments)));
     line(top[i],top[j]);
    }
    faceCount++;
   }
  }
 }
 return {fill:new Float32Array(fill),lines:new Float32Array(lines),faceCount,source};
}
function previewUpload(gl,values){const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,values,gl.STATIC_DRAW);return {buffer,count:values.length/6}}
function clearPreviewCanvas(canvas){
 const state=previewGpuStates.get(canvas);if(!state)return;
 state.gl.clearColor(243/255,246/255,249/255,1);state.gl.clear(state.gl.COLOR_BUFFER_BIT|state.gl.DEPTH_BUFFER_BIT);
}
function render(canvas,model,mode,options={}){
 const box=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,w=box.width,h=box.height;
 const width=Math.round(w*dpr),height=Math.round(h*dpr);if(canvas.width!==width)canvas.width=width;if(canvas.height!==height)canvas.height=height;
 const state=previewGpu(canvas),gl=state.gl;if(gl.isContextLost())return 0;
 const all=model.source.concat(model.target),lo=[0,1,2].map(i=>Math.min(...all.map(p=>p[i]))),hi=[0,1,2].map(i=>Math.max(...all.map(p=>p[i]))+1),bounds=[];
 for(const x of [lo[0],hi[0]])for(const y of [lo[1],hi[1]+.2])for(const z of [lo[2],hi[2]])bounds.push(projection(x,y,z));
 const left=Math.min(...bounds.map(p=>p[0])),right=Math.max(...bounds.map(p=>p[0])),top=Math.min(...bounds.map(p=>p[1])),bottom=Math.max(...bounds.map(p=>p[1]));
 const scale=Math.min((w-58)/(right-left+1),(h-55)/(bottom-top+1))*zoom,cx=(left+right)/2,cy=(top+bottom)/2;
 const near=Math.max(...bounds.map(p=>p[2])),far=Math.min(...bounds.map(p=>p[2])),depthCenter=(near+far)/2,depthRadius=(near-far)/2+2;
 const studs=options.studs??$('studs').checked;
 if(state.model!==model||state.mode!==mode||state.studs!==studs){
  if(state.mesh){gl.deleteBuffer(state.mesh.fill.buffer);gl.deleteBuffer(state.mesh.lines.buffer)}
  const mesh=previewMesh(model,mode,studs);state.mesh={fill:previewUpload(gl,mesh.fill),lines:previewUpload(gl,mesh.lines),faceCount:mesh.faceCount,source:mesh.source};
  state.model=model;state.mode=mode;state.studs=studs;
 }
 gl.viewport(0,0,width,height);gl.clearColor(243/255,246/255,249/255,1);gl.clearDepth(1);gl.depthMask(true);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);gl.disable(gl.BLEND);gl.useProgram(state.program);
 const u=state.uniforms;gl.uniform2f(u.Angles,yaw,pitch);gl.uniform2f(u.Viewport,w,h);gl.uniform2f(u.Center,cx,cy);gl.uniform2f(u.Depth,depthCenter,depthRadius);
 gl.uniform1f(u.Scale,scale);gl.uniform1f(u.Height,Number($('proportion').value));gl.uniform1f(u.Opacity,1);
 function draw(buffer,type){
  gl.bindBuffer(gl.ARRAY_BUFFER,buffer.buffer);gl.enableVertexAttribArray(state.position);gl.enableVertexAttribArray(state.color);
  gl.vertexAttribPointer(state.position,3,gl.FLOAT,false,24,0);gl.vertexAttribPointer(state.color,3,gl.FLOAT,false,24,12);gl.drawArrays(type,0,buffer.count);
 }
 const outlines=options.outlines!==false;
 // A slope-scaled offset can move a grazing face behind hidden edges. Use
 // only one fixed depth unit so coplanar seams remain visible without x-ray
 // outlines when the camera is almost parallel to a brick face.
 if(outlines){gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(0,1)}else gl.disable(gl.POLYGON_OFFSET_FILL);
 draw(state.mesh.fill,gl.TRIANGLES);gl.disable(gl.POLYGON_OFFSET_FILL);
 gl.depthMask(false);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
 if(options.grid!==false){
  const lines=[],rgb=[.86,.90,.93];
  for(let n=0;n<=12;n++){const x=lo[0]+n*(hi[0]-lo[0])/12,z=lo[2]+n*(hi[2]-lo[2])/12;
   for(const p of [[x,0,lo[2]],[x,0,hi[2]],[lo[0],0,z],[hi[0],0,z]])lines.push(...p,...rgb);
  }
  const grid=previewUpload(gl,new Float32Array(lines));gl.uniform1f(u.Opacity,1);draw(grid,gl.LINES);gl.deleteBuffer(grid.buffer);
 }
 if(outlines){gl.uniform1f(u.Opacity,state.mesh.source?.13:.65);gl.lineWidth(1);draw(state.mesh.lines,gl.LINES)}
 gl.depthMask(true);gl.disable(gl.BLEND);
 window.previewRenderDiagnostics??={};window.previewRenderDiagnostics[canvas.id]={renderer:'webgl_per_pixel_depth_v2',depthTestEnabled:gl.isEnabled(gl.DEPTH_TEST),depthBits:gl.getParameter(gl.DEPTH_BITS),outlineSlopeOffset:0,outlineDepthUnits:1,faceCount:state.mesh.faceCount,glError:gl.getError()};
 state.view={scale,cx,cy,width:w,height:h,depthCenter,depthRadius,proportion:Number($('proportion').value)};
 return state.mesh.faceCount;
}
