(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let canvas,card,gl,program,mode='tunnel',time0=performance.now(),bins=new Float32Array(24),level=0,bass=0,mid=0,treble=0,raf=0;
  const VS=`attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}`;
  const FS=`precision highp float;
uniform vec2 r;uniform float t,level,bass,mid,treble;uniform float bins[24];uniform int mode;
#define PI 3.14159265
float band(float x){float i=clamp(floor(x*24.0),0.0,23.0);if(i<1.)return bins[0];if(i<2.)return bins[1];if(i<3.)return bins[2];if(i<4.)return bins[3];if(i<5.)return bins[4];if(i<6.)return bins[5];if(i<7.)return bins[6];if(i<8.)return bins[7];if(i<9.)return bins[8];if(i<10.)return bins[9];if(i<11.)return bins[10];if(i<12.)return bins[11];if(i<13.)return bins[12];if(i<14.)return bins[13];if(i<15.)return bins[14];if(i<16.)return bins[15];if(i<17.)return bins[16];if(i<18.)return bins[17];if(i<19.)return bins[18];if(i<20.)return bins[19];if(i<21.)return bins[20];if(i<22.)return bins[21];if(i<23.)return bins[22];return bins[23];}
vec3 pal(float x){return .55+.45*cos(6.28318*(vec3(.02,.31,.58)+x));}
float lineGlow(float d,float w){return w/max(.004,abs(d));}
float circle(vec2 p,vec2 c,float rad){return length(p-c)-rad;}
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
void main(){
 vec2 uv=(2.*gl_FragCoord.xy-r.xy)/min(r.x,r.y);float tt=t*.45;vec3 col=vec3(0.);
 if(mode==0){float a=atan(uv.y,uv.x),rad=length(uv),z=1./max(.08,rad),lanes=abs(fract(a/PI*7.+tt*.16)-.5),ring=abs(fract(z*.42-tt*.55)-.5),b=band(fract((a+PI)/(2.*PI)));float glow=.018/(lanes+.012)+.025/(ring+.015);glow*=.18+.9*b;col=pal(a/6.283+tt*.08)*glow;col+=pal(z*.08)*bass*.10/max(.05,abs(rad-(.32+.10*sin(a*3.+tt))));}
 else if(mode==1){float z=uv.y+sin(uv.x*7.+tt*3.)*(.05+.18*mid),b=band(clamp(uv.x*.5+.5,0.,.999)),ribbon=.025/max(.01,abs(z-(b-.45)*.9)),echo=.012/max(.015,abs(z+.32-sin(uv.x*4.-tt*2.)*.12));col=pal(uv.x*.15+tt*.08)*(ribbon+echo*(.3+treble));col+=vec3(.02,.03,.05)/(abs(fract((uv.y+1.)*5.-tt*.35)-.5)*20.+1.);}
 else if(mode==2){vec2 q=uv;float perspective=1./max(.12,1.15-q.y),x=q.x*perspective,z=perspective+tt*.28,gx=abs(fract(x*5.)-.5),gz=abs(fract(z*3.)-.5),grid=.018/min(gx+.02,gz+.02),b=band(clamp(abs(q.x)*.65,0.,.999)),ridge=.025/max(.012,abs(q.y+.35-b*.65+.08*sin(q.x*9.+tt*3.)));col=pal(z*.08+q.x*.1)*(grid*(.14+.55*b)+ridge);}
 else if(mode==3){vec2 q=uv*(1.2+.12*bass);float p=0.;for(int i=0;i<5;i++){float fi=float(i);q=abs(q)/clamp(dot(q,q),.22,2.4)-vec2(.72+.08*sin(tt+fi),.58+.06*cos(tt*1.3-fi));p+=exp(-5.5*abs(length(q)-(.32+.05*sin(tt*2.+fi))));}float waves=sin((uv.x+uv.y)*8.+tt*4.+mid*5.)*.5+.5;col=pal(p*.15+tt*.08+waves*.08)*(p*.42+.18*waves+treble*.18);}
 else if(mode==4){float a=atan(uv.y,uv.x),rad=length(uv);a=abs(mod(a+PI/6.,PI/3.)-PI/6.);vec2 k=vec2(cos(a),sin(a))*rad;float b=band(clamp(rad*.8,0.,.999)),petals=sin(k.x*15.-tt*5.+sin(k.y*12.+tt*2.)*2.5),rings=sin(rad*28.-tt*7.),g=.018/max(.012,abs(petals*.55+rings*.45-(b-.5)));col=pal(a*.4+rad*.18+tt*.1)*g*(.45+b*.9);}
 else if(mode==5){vec2 q=uv;float rad=length(q),a=atan(q.y,q.x),depth=fract(1./max(.07,rad)*.23-tt*.8),spokes=abs(fract(a/(2.*PI)*18.+tt*.08)-.5),stars=.018/(spokes+.015)*smoothstep(.72,.03,depth),b=band(fract((a+PI)/(2.*PI))),core=.035/max(.02,rad*(1.6+b)-.10-.08*bass);col=pal(a/6.283+tt*.14)*(stars*(.22+b)+core*(.4+level));}
 else if(mode==6){float rad=length(uv),a=atan(uv.y,uv.x),b=band(fract((a+PI)/(2.*PI))),target=.34+.22*(b-.5)+.06*sin(a*6.-tt*5.),ring=lineGlow(rad-target,.014),ring2=lineGlow(rad-(.63+.08*sin(a*3.+tt*3.)),.009)*(mid+.15),pulse=lineGlow(rad-(.15+.08*bass),.012);col=pal(a/6.283+tt*.1)*(ring+ring2+pulse);}
 else if(mode==7){
   vec2 p=uv;float star=0.;for(int i=0;i<32;i++){float fi=float(i);vec2 sp=vec2(hash(vec2(fi,1.))*2.-1.,hash(vec2(fi,2.))*2.-1.);sp+=.035*vec2(sin(tt*(1.+mod(fi,5.))+.7*fi),cos(tt*(1.2+mod(fi,7.))-.3*fi))*(.4+treble);star+=.004/max(.003,length(p-sp));}
   vec2 c1=.58*vec2(cos(tt*.8),sin(tt*.8)),c2=.35*vec2(cos(-tt*1.3+2.),sin(-tt*1.3+2.)),c3=.78*vec2(cos(tt*.42+4.),sin(tt*.42+4.));float d1=circle(p,c1,.11+.08*bass),d2=circle(p,c2,.07+.05*mid),d3=circle(p,c3,.055+.045*treble);col+=vec3(.25,.55,1.)*lineGlow(d1,.02)+vec3(1.,.32,.55)*lineGlow(d2,.015)+vec3(.55,1.,.45)*lineGlow(d3,.013);col+=vec3(star)*(.22+treble*.55);float sun=.04/max(.025,length(p));col+=vec3(1.,.65,.18)*sun*(.35+level);
 }
 else if(mode==8){
   vec2 p=uv;float s=0.;for(int i=0;i<48;i++){float fi=float(i),z=fract(fi*.173+tt*.18*(.35+level));vec2 q=vec2(hash(vec2(fi,4.))*2.-1.,hash(vec2(fi,9.))*2.-1.)*(.25+1.5*z);float d=length(p-q);s+=.0035/max(.002,d)*(1.-z);}
   float sweep=sin((uv.x+uv.y)*9.-tt*8.)*.5+.5;col=pal(tt*.08+uv.x*.04)*(s*(.35+treble*.9)+.08*sweep*mid);
 }
 else if(mode==9){
   vec2 p=uv;float neck=lineGlow(abs(p.x)-.11,.012)*smoothstep(.85,.05,abs(p.y+.05));float body=lineGlow(circle(p,vec2(0.,-.28),.28+.035*bass),.018);float hole=.03/max(.015,abs(circle(p,vec2(0.,-.28),.075)));float strings=.012/max(.006,abs(fract((p.x+.12)*32.)-.5))*smoothstep(.13,.11,abs(p.x))*smoothstep(.55,-.55,p.y);col=vec3(1.,.25,.75)*(body+neck*.55)+vec3(.25,.75,1.)*strings*(.18+treble)+vec3(1.,.75,.2)*hole*(.2+mid);
   float drum=lineGlow(circle(p,vec2(-.62,-.2),.18+.04*bass),.014);float cym=lineGlow(abs(p.y-.37-.05*sin(p.x*9.))-0.0,.01)*smoothstep(.42,.18,abs(p.x-.48));col+=vec3(.2,1.,.8)*drum+vec3(1.,.8,.15)*cym*(.3+treble);
 }
 else if(mode==10){
   vec2 p=uv;float horizon=-.15;float road=smoothstep(.9,.15,abs(p.x)/(1.18-p.y))*smoothstep(-.95,horizon,p.y);float lane=.012/max(.006,abs(fract((p.x/(1.12-p.y))*5.)-.5))*road;float dash=.016/max(.008,abs(fract((p.y+tt*(.9+bass))*9.)-.5))*lane;col+=vec3(.05,.18,.24)*road+vec3(.1,.65,1.)*dash*(.35+treble);
   for(int i=0;i<6;i++){float fi=float(i),z=fract(fi*.19+tt*(.18+.22*level)),yy=mix(horizon,-.82,z),xx=(hash(vec2(fi,7.))-.5)*1.35*(1.-z*.72);float car=lineGlow(abs(p.y-yy)-.025-.018*z,.01)*smoothstep(.15,.055,abs(p.x-xx));float tail=.012/max(.006,abs(p.x-xx-.045))+.012/max(.006,abs(p.x-xx+.045));col+=pal(fi*.17+tt*.05)*car*(.35+bass*.75)+vec3(1.,.08,.03)*tail*car*.25;}
 }
 else if(mode==11){
   vec2 p=uv;float burst=0.;for(int i=0;i<28;i++){float fi=float(i),a=fi/28.*2.*PI+hash(vec2(fi,3.))*0.4,speed=.18+.65*hash(vec2(fi,8.)),age=fract(tt*.42+hash(vec2(fi,11.))),rad=age*(.18+speed*(.55+bass));vec2 q=vec2(cos(a),sin(a))*rad;float d=length(p-q);burst+=.006/max(.003,d)*(1.-age);}
   float shock=lineGlow(length(p)-fract(tt*.35)*(.25+.45*bass),.015);float core=.035/max(.018,length(p)-.03-.05*bass);col=vec3(1.,.18,.03)*burst*(.35+bass)+vec3(1.,.72,.12)*shock*(.28+level)+vec3(1.,.9,.55)*core*(.3+treble);
 }
 else {
   float x=clamp(uv.x*.5+.5,0.,.999),b=band(x),base=-.72;
   float ridge=base+b*1.22+.035*sin(uv.x*34.+tt*4.)*(.25+treble);
   float edge=lineGlow(uv.y-ridge,.012),fill=smoothstep(base,ridge,uv.y)*smoothstep(ridge+.035,ridge-.18,uv.y);
   float curtain=smoothstep(base,ridge,uv.y)*(.16+.84*b),grid=.014/max(.012,abs(fract(x*12.)-.5));
   col=pal(.04+x*.84)*((edge*(.36+b*.8))+(fill+curtain)*.32);
   col+=pal(x)*grid*curtain*.12;
   col+=vec3(.03,.05,.07)*(.35+.65*smoothstep(.02,.0,abs(uv.y-base)));
 }
 float vign=1.-smoothstep(.78,1.62,length(uv));col*=vign*(.62+level*.82);col=1.-exp(-col*1.18);gl_FragColor=vec4(col,1.);
}`;
  function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
  function initGl(){gl=canvas.getContext('webgl',{antialias:false,alpha:false,powerPreference:'high-performance'});if(!gl)throw Error('WebGL is unavailable');program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,VS));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,FS));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0)}
  function modeIndex(){return({tunnel:0,ribbon:1,field:2,plasma:3,kaleidoscope:4,starwarp:5,rings:6,planets:7,stardance:8,instruments:9,freeway:10,explosions:11,prismatic:12})[mode]??0}
  async function toggleFullscreen(){try{if(document.fullscreenElement){await document.exitFullscreen()}else if(card?.requestFullscreen){await card.requestFullscreen()}else{throw Error('Fullscreen API unavailable')}}catch(e){const s=document.getElementById('mv-webgl-status');if(s)s.textContent='Fullscreen unavailable: '+e.message}}
  function syncFullscreen(){const full=document.fullscreenElement===card,button=document.getElementById('mv-webgl-fullscreen');if(button)button.textContent=full?'EXIT FULL SCREEN':'FULL SCREEN';if(!canvas)return;canvas.style.height=full?`${Math.max(260,window.innerHeight-92)}px`:'330px';if(card){card.style.background=full?'#030509':'';card.style.borderRadius=full?'0':'';card.style.padding=full?'12px':'16px'}}
  function install(){if(document.getElementById('mv-webgl-stage'))return true;const anchor=document.getElementById('music-visualizer-anchor');if(!anchor)return false;card=document.createElement('div');card.id='mv-webgl-stage';card.className='card';card.style.cssText='padding:16px;overflow:hidden';card.innerHTML=`<div style="display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap"><div><b style="font-size:18px">3D VISUALIZER</b><small style="color:#8fa0ad;margin-left:8px">WebGL</small></div><div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><select id="mv-webgl-mode" class="search" style="width:auto;min-width:185px"><option value="tunnel">Frequency Tunnel</option><option value="ribbon">Neon Ribbon</option><option value="field">Spectrum Field</option><option value="plasma">Plasma Bloom</option><option value="kaleidoscope">Kaleidoscope</option><option value="starwarp">Star Warp</option><option value="rings">Electric Rings</option><option value="planets">Dancing Planets</option><option value="stardance">Star Dance</option><option value="instruments">Neon Instruments</option><option value="freeway">Electric Freeway</option><option value="explosions">Explosion Field</option><option value="prismatic">Prismatic Spectrum</option></select><button id="mv-webgl-fullscreen" type="button" style="min-height:48px">FULL SCREEN</button></div></div><canvas id="mv-webgl-canvas" style="display:block;width:100%;height:330px;margin-top:12px;border-radius:16px;background:#030509"></canvas><div id="mv-webgl-status" style="font-size:11px;color:#82909d;margin-top:8px">GPU visualization ready · 13 reactive presets.</div>`;anchor.before(card);canvas=card.querySelector('#mv-webgl-canvas');card.querySelector('#mv-webgl-mode').onchange=e=>mode=e.target.value;card.querySelector('#mv-webgl-fullscreen').onclick=toggleFullscreen;document.addEventListener('fullscreenchange',syncFullscreen);window.addEventListener('resize',()=>{if(document.fullscreenElement===card)syncFullscreen()});try{initGl();animate()}catch(e){card.querySelector('#mv-webgl-status').textContent='WebGL unavailable: '+e.message;return false}return true}
  function resize(){const d=Math.min(2,window.devicePixelRatio||1),w=Math.max(2,Math.floor(canvas.clientWidth*d)),h=Math.max(2,Math.floor(canvas.clientHeight*d));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h)}}
  function animate(){if(!gl)return;resize();gl.useProgram(program);gl.uniform2f(gl.getUniformLocation(program,'r'),canvas.width,canvas.height);gl.uniform1f(gl.getUniformLocation(program,'t'),(performance.now()-time0)/1000);gl.uniform1f(gl.getUniformLocation(program,'level'),level);gl.uniform1f(gl.getUniformLocation(program,'bass'),bass);gl.uniform1f(gl.getUniformLocation(program,'mid'),mid);gl.uniform1f(gl.getUniformLocation(program,'treble'),treble);gl.uniform1fv(gl.getUniformLocation(program,'bins[0]'),bins);gl.uniform1i(gl.getUniformLocation(program,'mode'),modeIndex());gl.drawArrays(gl.TRIANGLES,0,6);raf=requestAnimationFrame(animate)}
  function render(state){if(!canvas)install();if(!state)return;level=state.level||0;bass=state.bass||0;mid=state.mid||0;treble=state.treble||0;const s=state.spectrum||[];for(let i=0;i<24;i++)bins[i]+=((s[i]||0)-bins[i])*.24}
  let tries=0;const boot=()=>{if(install())return;if(tries++<50)setTimeout(boot,50)};setTimeout(boot,0);root.WebGLMusicVisualizer={install,render};
})();
