(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const canvas=document.getElementById('music-visualizer-canvas');
  const button=document.getElementById('music-visualizer-toggle');
  const status=document.getElementById('music-visualizer-status');
  const modeSelect=document.getElementById('music-visualizer-mode');
  const meters={
    bass:document.getElementById('music-bass'),
    mid:document.getElementById('music-mid'),
    treble:document.getElementById('music-treble')
  };
  if(!canvas||!button||!root.BrowserPcmCapture)return;

  const context=canvas.getContext('2d');
  const capture=new root.BrowserPcmCapture();
  let state={level:0,bass:0,mid:0,treble:0,spectrum:Array(24).fill(0)};
  let phase=0;

  function resize(){
    const ratio=Math.min(window.devicePixelRatio||1,2);
    const width=Math.max(320,canvas.clientWidth);
    const height=Math.max(220,canvas.clientHeight);
    if(canvas.width!==Math.floor(width*ratio)||canvas.height!==Math.floor(height*ratio)){
      canvas.width=Math.floor(width*ratio);
      canvas.height=Math.floor(height*ratio);
    }
    context.setTransform(ratio,0,0,ratio,0,0);
    return {width,height};
  }

  function renderMeters(){
    for(const [name,element] of Object.entries(meters)){
      if(element)element.style.width=`${Math.max(0,Math.min(1,state[name]||0))*100}%`;
    }
  }

  function renderBars(width,height){
    const bins=state.spectrum||[];
    const gap=4;
    const barWidth=Math.max(3,(width-gap*(bins.length-1))/Math.max(1,bins.length));
    bins.forEach((value,index)=>{
      const normalized=Math.max(0,Math.min(1,value||0));
      const barHeight=Math.max(2,normalized*(height-24));
      const hue=195+index*5+phase*.12;
      context.fillStyle=`hsl(${hue%360} 88% ${48+normalized*18}%)`;
      context.fillRect(index*(barWidth+gap),height-barHeight,barWidth,barHeight);
    });
  }

  function renderRings(width,height){
    const cx=width/2,cy=height/2;
    const bins=state.spectrum||[];
    bins.forEach((value,index)=>{
      const normalized=Math.max(0,Math.min(1,value||0));
      const radius=20+index*Math.min(width,height)/62+normalized*28;
      context.beginPath();
      context.arc(cx,cy,radius,0,Math.PI*2);
      context.strokeStyle=`hsla(${(190+index*7+phase*.1)%360} 90% 60% / ${.12+normalized*.72})`;
      context.lineWidth=1+normalized*4;
      context.stroke();
    });
  }

  function renderTunnel(width,height){
    const bins=state.spectrum||[];
    const cx=width/2,cy=height/2;
    for(let ring=0;ring<18;ring++){
      const index=(ring+Math.floor(phase/5))%Math.max(1,bins.length);
      const energy=bins[index]||0;
      const radius=((ring*28+phase*2)%Math.max(width,height));
      context.beginPath();
      context.arc(cx,cy,radius,0,Math.PI*2);
      context.strokeStyle=`hsla(${(205+ring*9+phase*.15)%360} 92% 60% / ${.08+energy*.7})`;
      context.lineWidth=1+energy*5;
      context.stroke();
    }
  }

  function draw(){
    const {width,height}=resize();
    phase+=.8+.8*(state.level||0);
    context.fillStyle='rgba(3,7,12,.24)';
    context.fillRect(0,0,width,height);
    const mode=modeSelect?.value||'bars';
    if(mode==='rings')renderRings(width,height);
    else if(mode==='tunnel')renderTunnel(width,height);
    else renderBars(width,height);
    renderMeters();
    requestAnimationFrame(draw);
  }

  button.onclick=async()=>{
    try {
      if(capture.running){
        await capture.stop();
        button.textContent='START MICROPHONE';
        status.textContent='Microphone stopped.';
      }else{
        await capture.start(next=>{state=next;});
        button.textContent='STOP MICROPHONE';
        status.textContent='Microphone active · browser PCM → shared MusicAnalyzer';
      }
    }catch(error){status.textContent=`Microphone error: ${error.message}`;}
  };

  window.addEventListener('resize',resize);
  draw();
})();
