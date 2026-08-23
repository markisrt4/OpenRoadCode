(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const status=document.getElementById('fullscreen-audio-status');
  const exit=document.getElementById('fullscreen-exit');
  let active=true,timer=null;
  function normalize(payload){
    const audio=payload?.audio||payload||{};
    return {level:audio.level||0,bass:audio.bass||0,mid:audio.mid||0,treble:audio.treble||0,spectrum:audio.spectrum||[]};
  }
  async function poll(){
    if(!active)return;
    try{
      const response=await fetch('/api/audio-analysis/linux/state',{cache:'no-store'}),payload=await response.json();
      if(!response.ok||payload.error)throw Error(payload.error||`HTTP ${response.status}`);
      root.WebGLMusicVisualizer?.render(normalize(payload));
      if(status)status.textContent='PIPEWIRE · LIVE';
    }catch(error){if(status)status.textContent='PIPEWIRE · '+error.message;}
    timer=setTimeout(poll,35);
  }
  async function start(){
    try{
      const response=await fetch('/api/audio-analysis/linux/start',{method:'POST'}),payload=await response.json();
      if(!response.ok)throw Error(payload.error||`HTTP ${response.status}`);
      poll();
    }catch(error){if(status)status.textContent='PIPEWIRE · '+error.message;}
  }
  addEventListener('pagehide',()=>{active=false;if(timer)clearTimeout(timer);navigator.sendBeacon('/api/audio-analysis/linux/stop');});
  if(exit)exit.onclick=async()=>{exit.disabled=true;exit.textContent='EXITING…';try{await fetch('/api/visualizer/exit',{method:'POST'})}catch(error){exit.disabled=false;exit.textContent='EXIT FAILED';if(status)status.textContent=error.message}};
  start();
})();
