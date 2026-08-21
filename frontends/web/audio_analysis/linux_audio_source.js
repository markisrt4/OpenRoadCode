(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  let active=false,timer=null;

  function install(){
    const mic=document.getElementById('music-mic-toggle');
    if(!mic||document.getElementById('music-audio-source'))return false;
    const wrap=document.createElement('div');
    wrap.style.cssText='margin-top:12px';
    wrap.innerHTML=`<label for="music-audio-source" style="display:block;font-size:12px;color:#c5d0db;margin-bottom:5px">AUDIO SOURCE</label><select id="music-audio-source" class="search"><option value="browser">Browser microphone</option><option value="linux">Linux system audio (PipeWire)</option></select><div id="music-linux-audio-status" style="font-size:11px;color:#82909d;margin-top:7px">Browser microphone selected.</div>`;
    mic.before(wrap);
    document.getElementById('music-audio-source').onchange=e=>select(e.target.value);
    return true;
  }

  async function select(source){
    if(source==='linux'){
      if(micRunning())document.getElementById('music-mic-toggle')?.click();
      await start();
    }else await stop();
  }
  function micRunning(){return document.getElementById('music-mic-toggle')?.dataset.enabled==='1'}
  async function start(){
    const status=document.getElementById('music-linux-audio-status');
    try{
      const r=await fetch('/api/audio-analysis/linux/start',{method:'POST'}),j=await r.json();
      if(!r.ok)throw Error(j.error||`HTTP ${r.status}`);
      active=true;if(status)status.textContent='Listening to Linux system output via PipeWire monitor.';
      poll();
    }catch(e){active=false;if(status)status.textContent='Linux audio unavailable: '+e.message}
  }
  async function stop(){
    active=false;if(timer){clearTimeout(timer);timer=null}
    try{await fetch('/api/audio-analysis/linux/stop',{method:'POST'})}catch(_){ }
    const status=document.getElementById('music-linux-audio-status');if(status)status.textContent='Browser microphone selected.';
  }
  async function poll(){
    if(!active)return;
    try{
      const r=await fetch('/api/audio-analysis/linux/state',{cache:'no-store'}),s=await r.json();
      if(!r.ok)throw Error(s.error||`HTTP ${r.status}`);
      if(s.error)throw Error(s.error);
      root.LinuxAudioSource.latest=s;
      root.WebGLMusicVisualizer?.render(s);
      const ids={level:'music-level',bass:'music-bass',mid:'music-mid',treble:'music-treble'};
      for(const [key,id] of Object.entries(ids)){const el=document.getElementById(id);if(el)el.value=s[key]||0}
      const bars=document.querySelectorAll('#music-spectrum > *');
      if(bars.length&&s.spectrum)bars.forEach((bar,i)=>bar.style.height=`${Math.max(2,(s.spectrum[i]||0)*100)}%`);
      const dbg=document.getElementById('music-debug');if(dbg)dbg.textContent='Linux PipeWire · system output · Python AudioAnalyzer';
    }catch(e){const status=document.getElementById('music-linux-audio-status');if(status)status.textContent='Linux audio error: '+e.message}
    timer=setTimeout(poll,35);
  }
  let tries=0;const boot=()=>{if(install())return;if(tries++<50)setTimeout(boot,50)};setTimeout(boot,0);
  root.LinuxAudioSource={install,start,stop,get active(){return active},latest:null};
})();
