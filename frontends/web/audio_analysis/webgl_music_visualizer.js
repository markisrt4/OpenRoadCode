(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let canvas,gl,program,mode='tunnel',time0=performance.now(),bins=new Float32Array(24),level=0,bass=0,mid=0,treble=0,raf=0;

  const VS=`attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}`;
  const FS=`precision highp float;
uniform vec2 r;uniform float t,level,bass,mid,treble;uniform float bins[24];uniform int mode;
#define PI 3.14159265
float band(float x){float i=clamp(floor(x*24.0),0.0,23.0);if(i<1.)return bins[0];if(i<2.)return bins[1];if(i<3.)return bins[2];if(i<4.)return bins[3];if(i<5.)return bins[4];if(i<6.)return bins[5];if(i<7.)return bins[6];if(i<8.)return bins[7];if(i<9.)return bins[8];if(i<10.)return bins[9];if(i<11.)return bins[10];if(i<12.)return bins[11];if(i<13.)return bins[12];if(i<14.)return bins[13];if(i<15.)return bins[14];if(i<16.)return bins[15];if(i<17.)return bins[16];if(i<18.)return bins[17];if(i<19.)return bins[18];if(i<20.)return bins[19];if(i<21.)return bins[20];if(i<22.)return bins[21];if(i<23.)return bins[22];return bins[23];}
vec3 pal(float x){return .55+.45*cos(6.28318*(vec3(.02,.31,.58)+x));}
void main(){
 vec2 uv=(2.*gl_FragCoord.xy-r.xy)/min(r.x,r.y);float tt=t*.45;vec3 col=vec3(0.);
 if(mode==0){
   float a=atan(uv.y,uv.x);float rad=length(uv);float z=1./max(.08,rad);float lanes=abs(fract(a/PI*7.+tt*.16)-.5);float ring=abs(fract(z*.42-tt*.55)-.5);float b=band(fract((a+PI)/(2.*PI)));
   float glow=.018/(lanes+.012)+.025/(ring+.015);glow*=.18+.9*b;col=pal(a/6.283+tt*.08)*glow;col+=pal(z*.08)*bass*.10/max(.05,abs(rad-(.32+.10*sin(a*3.+tt))));
 } else if(mode==1){
   float z=uv.y+sin(uv.x*7.+tt*3.)*(.05+.18*mid);float b=band(clamp(uv.x*.5+.5,0.,.999));float ribbon=.025/max(.01,abs(z-(b-.45)*.9));float echo=.012/max(.015,abs(z+.32-sin(uv.x*4.-tt*2.)*.12));col=pal(uv.x*.15+tt*.08)*(ribbon+echo*(.3+treble));
   col+=vec3(.02,.03,.05)/(abs(fract((uv.y+1.)*5.-tt*.35)-.5)*20.+1.);
 } else {
   vec2 q=uv;float perspective=1./max(.12,1.15-q.y);float x=q.x*perspective;float z=perspective+tt*.28;float gx=abs(fract(x*5.)-.5);float gz=abs(fract(z*3.)-.5);float grid=.018/min(gx+.02,gz+.02);float b=band(clamp(abs(q.x)*.65,0.,.999));float ridge=.025/max(.012,abs(q.y+.35-b*.65+.08*sin(q.x*9.+tt*3.)));col=pal(z*.08+q.x*.1)*(grid*(.14+.55*b)+ridge);
 }
 float vign=1.-smoothstep(.75,1.55,length(uv));col*=vign*(.65+level*.75);col=1.-exp(-col*1.25);gl_FragColor=vec4(col,1.);
}`;

  function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
  function initGl(){gl=canvas.getContext('webgl',{antialias:false,alpha:false,powerPreference:'high-performance'});if(!gl)throw Error('WebGL is unavailable');program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,VS));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,FS));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0)}
  function install(){if(document.getElementById('mv-webgl-stage'))return true;const spectrum=document.getElementById('music-spectrum')?.closest('.card');if(!spectrum)return false;const card=document.createElement('div');card.id='mv-webgl-stage';card.className='card';card.style.cssText='padding:16px;overflow:hidden';card.innerHTML=`<div style="display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap"><div><b style="font-size:18px">3D VISUALIZER</b><small style="color:#8fa0ad;margin-left:8px">WebGL</small></div><select id="mv-webgl-mode" class="search" style="width:auto;min-width:170px"><option value="tunnel">Frequency Tunnel</option><option value="ribbon">Neon Ribbon</option><option value="field">Spectrum Field</option></select></div><canvas id="mv-webgl-canvas" style="display:block;width:100%;height:330px;margin-top:12px;border-radius:16px;background:#030509"></canvas><div id="mv-webgl-status" style="font-size:11px;color:#82909d;margin-top:8px">GPU visualization ready.</div>`;spectrum.before(card);canvas=card.querySelector('#mv-webgl-canvas');card.querySelector('#mv-webgl-mode').onchange=e=>mode=e.target.value;try{initGl();animate()}catch(e){card.querySelector('#mv-webgl-status').textContent='WebGL unavailable: '+e.message;return false}return true}
  function resize(){const d=Math.min(2,window.devicePixelRatio||1),w=Math.max(2,Math.floor(canvas.clientWidth*d)),h=Math.max(2,Math.floor(canvas.clientHeight*d));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h)}}
  function animate(){if(!gl)return;resize();gl.useProgram(program);gl.uniform2f(gl.getUniformLocation(program,'r'),canvas.width,canvas.height);gl.uniform1f(gl.getUniformLocation(program,'t'),(performance.now()-time0)/1000);gl.uniform1f(gl.getUniformLocation(program,'level'),level);gl.uniform1f(gl.getUniformLocation(program,'bass'),bass);gl.uniform1f(gl.getUniformLocation(program,'mid'),mid);gl.uniform1f(gl.getUniformLocation(program,'treble'),treble);gl.uniform1fv(gl.getUniformLocation(program,'bins[0]'),bins);gl.uniform1i(gl.getUniformLocation(program,'mode'),mode==='ribbon'?1:mode==='field'?2:0);gl.drawArrays(gl.TRIANGLES,0,6);raf=requestAnimationFrame(animate)}
  function render(state){if(!canvas)install();if(!state)return;level=state.level||0;bass=state.bass||0;mid=state.mid||0;treble=state.treble||0;const s=state.spectrum||[];for(let i=0;i<24;i++)bins[i]+=((s[i]||0)-bins[i])*.24}
  let tries=0;const boot=()=>{if(install())return;if(tries++<50)setTimeout(boot,50)};setTimeout(boot,0);root.WebGLMusicVisualizer={install,render};
})();
