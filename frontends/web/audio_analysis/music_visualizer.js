(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const button=document.getElementById('music-visualizer-toggle');
  const status=document.getElementById('music-visualizer-status');
  const meters={bass:document.getElementById('music-bass'),mid:document.getElementById('music-mid'),treble:document.getElementById('music-treble')};
  if(!button||!root.BrowserPcmCapture)return;

  const capture=new root.BrowserPcmCapture();
  let state={level:0,bass:0,mid:0,treble:0,spectrum:Array(24).fill(0)};

  function render(next){
    state=next||state;
    for(const [name,element] of Object.entries(meters)){
      if(element)element.style.width=`${Math.max(0,Math.min(1,state[name]||0))*100}%`;
    }
    root.WebGLMusicVisualizer?.render(state);
  }

  button.onclick=async()=>{
    try{
      if(capture.running){
        await capture.stop();
        button.textContent='START MICROPHONE';
        status.textContent='Microphone stopped.';
      }else{
        await capture.start(render);
        button.textContent='STOP MICROPHONE';
        status.textContent='Microphone active · browser PCM → shared MusicAnalyzer → WebGL';
      }
    }catch(error){status.textContent=`Microphone error: ${error.message}`;}
  };

  render(state);
})();
