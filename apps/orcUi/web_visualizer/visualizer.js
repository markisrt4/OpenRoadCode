(()=>{
'use strict';
const canvas=document.getElementById('gl'),status=document.getElementById('status'),picker=document.getElementById('mode');
const gl=canvas.getContext('webgl',{antialias:false,alpha:false,powerPreference:'high-performance'});
if(!gl){status.textContent='WEBGL UNAVAILABLE';throw Error('WebGL unavailable');}
const VS='attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
const FS=`precision highp float;
uniform vec2 r;uniform float t,level,bass,mid,treble;uniform float bins[24];uniform int mode;
#define PI 3.14159265
float band(float x){float i=clamp(floor(x*24.0),0.0,23.0);if(i<1.)return bins[0];if(i<2.)return bins[1];if(i<3.)return bins[2];if(i<4.)return bins[3];if(i<5.)return bins[4];if(i<6.)return bins[5];if(i<7.)return bins[6];if(i<8.)return bins[7];if(i<9.)return bins[8];if(i<10.)return bins[9];if(i<11.)return bins[10];if(i<12.)return bins[11];if(i<13.)return bins[12];if(i<14.)return bins[13];if(i<15.)return bins[14];if(i<16.)return bins[15];if(i<17.)return bins[16];if(i<18.)return bins[17];if(i<19.)return bins[18];if(i<20.)return bins[19];if(i<21.)return bins[20];if(i<22.)return bins[21];if(i<23.)return bins[22];return bins[23];}
vec3 pal(float x){return .55+.45*cos(6.28318*(vec3(.02,.31,.58)+x));}
float glow(float d,float w){return w/max(.004,abs(d));}
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
void main(){vec2 uv=(2.*gl_FragCoord.xy-r.xy)/min(r.x,r.y);float tt=t*.45;vec3 col=vec3(0.);
if(mode==0){float x=clamp(uv.x*.5+.5,0.,.999),b=band(x),base=-.72,ridge=base+b*1.22+.035*sin(uv.x*34.+tt*4.)*(.25+treble);float edge=glow(uv.y-ridge,.012),fill=smoothstep(base,ridge,uv.y)*smoothstep(ridge+.035,ridge-.18,uv.y);col=pal(.04+x*.84)*(edge*(.36+b*.8)+fill*.38);}
else if(mode==1){float a=atan(uv.y,uv.x),rad=length(uv);float stars=.003/max(.003,abs(sin(uv.x*73.+uv.y*91.)));col+=vec3(stars)*(.08+treble*.18);for(int i=0;i<3;i++){float fi=float(i),rr=.28+fi*.23,ang=tt*(.8+fi*.33)*(mod(fi,2.)<1.?1.:-1.);vec2 c=rr*vec2(cos(ang+fi*2.),sin(ang+fi*2.)*.55);float d=length(uv-c)-(.06+.035*band(fi*.31));col+=pal(fi*.28+tt*.04)*glow(d,.018);}col+=vec3(1.,.65,.18)*.035/max(.025,rad);}
else if(mode==2){float horizon=-.18,persp=1./max(.15,1.12-uv.y),x=uv.x*persp,z=persp+tt*.34,gx=abs(fract(x*4.)-.5),gz=abs(fract(z*3.)-.5),grid=.015/min(gx+.025,gz+.025),b=band(clamp(abs(uv.x)*.7,0.,.999));float road=smoothstep(1.1,.15,abs(uv.x)/(1.2-uv.y))*smoothstep(-.95,horizon,uv.y);col=pal(z*.08+uv.x*.08)*(grid*(.10+.5*b))*road;col+=vec3(.08,.5,1.)*glow(abs(uv.x/(1.1-uv.y))-.24,.01)*road;}
else if(mode==3){float rad=length(uv),a=atan(uv.y,uv.x),b=band(fract((a+PI)/(2.*PI))),shock=glow(rad-fract(tt*.36)*(.25+.5*bass),.014),rays=.012/max(.008,abs(fract(a/PI*11.+tt*.08)-.5));col=vec3(1.,.18,.03)*rays*b*(1.-smoothstep(.1,1.2,rad))+vec3(1.,.72,.12)*shock*(.25+level);}
else if(mode==4){float s=0.;for(int i=0;i<42;i++){float fi=float(i);vec2 q=vec2(hash(vec2(fi,4.))*2.-1.,hash(vec2(fi,9.))*2.-1.);q+=.04*vec2(sin(tt*(1.+mod(fi,5.))+fi),cos(tt*(1.2+mod(fi,7.))-fi))*(.4+treble);s+=.0035/max(.002,length(uv-q));}col=pal(tt*.08+uv.x*.04)*s*(.28+treble*.8);}
else if(mode==5){float rad=length(uv),a=atan(uv.y,uv.x),b=band(fract((a+PI)/(2.*PI))),target=.34+.22*(b-.5)+.06*sin(a*6.-tt*5.);col=pal(a/6.283+tt*.1)*(glow(rad-target,.014)+glow(rad-(.63+.08*sin(a*3.+tt*3.)),.009)*(mid+.15)+glow(rad-(.15+.08*bass),.012));}
else if(mode==6){float z=uv.y+sin(uv.x*7.+tt*3.)*(.05+.18*mid),b=band(clamp(uv.x*.5+.5,0.,.999)),ribbon=.025/max(.01,abs(z-(b-.45)*.9)),echo=.012/max(.015,abs(z+.32-sin(uv.x*4.-tt*2.)*.12));col=pal(uv.x*.15+tt*.08)*(ribbon+echo*(.3+treble));}
else{float a=atan(uv.y,uv.x),rad=length(uv);a=abs(mod(a+PI/6.,PI/3.)-PI/6.);vec2 k=vec2(cos(a),sin(a))*rad;float b=band(clamp(rad*.8,0.,.999)),petals=sin(k.x*15.-tt*5.+sin(k.y*12.+tt*2.)*2.5),rings=sin(rad*28.-tt*7.),g=.018/max(.012,abs(petals*.55+rings*.45-(b-.5)));col=pal(a*.4+rad*.18+tt*.1)*g*(.45+b*.9);}
float vign=1.-smoothstep(.78,1.62,length(uv));col*=vign*(.62+level*.82);col=1.-exp(-col*1.18);gl_FragColor=vec4(col,1.);}`;
function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,VS));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,FS));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const pos=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);
const u={r:gl.getUniformLocation(program,'r'),t:gl.getUniformLocation(program,'t'),level:gl.getUniformLocation(program,'level'),bass:gl.getUniformLocation(program,'bass'),mid:gl.getUniformLocation(program,'mid'),treble:gl.getUniformLocation(program,'treble'),bins:gl.getUniformLocation(program,'bins'),mode:gl.getUniformLocation(program,'mode')};
const start=performance.now(),bins=new Float32Array(24);let phase=0;
function resize(){const dpr=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.floor(innerWidth*dpr)),h=Math.max(1,Math.floor(innerHeight*dpr));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}gl.viewport(0,0,w,h);}
function clamp(v){return Math.max(0,Math.min(1,v));}
function render(now){resize();phase+=.045;const bass=clamp(.5+.32*Math.sin(phase*1.17)+.08*Math.sin(phase*5.1)),mid=clamp(.44+.28*Math.sin(phase*1.71+1.3)),treble=clamp(.4+.3*Math.sin(phase*2.37+2.1)),level=clamp(bass*.42+mid*.36+treble*.22);for(let i=0;i<24;i++)bins[i]=clamp(level*.34+.3*Math.sin(phase*(.8+i*.025)+i*.47)+.24*Math.sin(phase*1.9+i*.23));gl.uniform2f(u.r,canvas.width,canvas.height);gl.uniform1f(u.t,(now-start)/1000);gl.uniform1f(u.level,level);gl.uniform1f(u.bass,bass);gl.uniform1f(u.mid,mid);gl.uniform1f(u.treble,treble);gl.uniform1fv(u.bins,bins);gl.uniform1i(u.mode,Number(picker.value));gl.drawArrays(gl.TRIANGLES,0,6);status.textContent=`SIMULATED AUDIO · WEBGL · LEVEL ${level.toFixed(2)} · BASS ${bass.toFixed(2)} · MID ${mid.toFixed(2)} · TREBLE ${treble.toFixed(2)}`;requestAnimationFrame(render);}
document.getElementById('fullscreen').onclick=async()=>{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();};
requestAnimationFrame(render);
})();
