(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const byId=id=>document.getElementById(id);
  const button=byId('music-visualizer-toggle'),linuxButton=byId('music-visualizer-linux-toggle'),status=byId('music-visualizer-status'),lightingButton=byId('music-lighting-toggle'),lightingStatus=byId('music-lighting-status'),songButton=byId('music-song-identify'),songStatus=byId('music-song-status'),songTitle=byId('music-song-title'),songArtist=byId('music-song-artist'),songAlbum=byId('music-song-album'),sensitivity=byId('music-visualizer-sensitivity'),sensitivityValue=byId('music-visualizer-sensitivity-value'),zeroizeStart=byId('music-zeroize-start'),zeroizeFinish=byId('music-zeroize-finish'),zeroizeClear=byId('music-zeroize-clear'),zeroizeStatus=byId('music-zeroize-status');
  if(!button||!root.BrowserPcmCapture)return;
  const capture=new root.BrowserPcmCapture();
  const sourceSelect=document.createElement('select');
  sourceSelect.id='music-visualizer-source';sourceSelect.className='search';sourceSelect.setAttribute('aria-label','Audio source');
  button.before(sourceSelect);linuxButton?.remove();
  const labels={browser:'Browser Microphone','linux-pipewire':'Linux System Audio (PipeWire)'};
  const meters={bass:byId('music-bass'),mid:byId('music-mid'),treble:byId('music-treble')};
  let state={level:0,bass:0,mid:0,treble:0,spectrum:Array(24).fill(0),percussion:{},source:null,running:false,zeroized:false,calibrating:false};
  let activeSource=null,pollTimer=null,epoch=0,busy=false,available=[];
  const clamp01=value=>Math.max(0,Math.min(1,Number(value)||0));
  const response=(value,gain)=>1-Math.exp(-clamp01(value)*gain);
  function visualGain(){return Math.max(1,Number(sensitivity?.value)||10)}
  function visualState(raw){
    const gain=visualGain(),percussionGain=gain*4,percussion=raw?.percussion||{};
    return {...raw,level:response(raw?.level,gain),bass:response(raw?.bass,gain),mid:response(raw?.mid,gain),treble:response(raw?.treble,gain),spectrum:(raw?.spectrum||[]).map(value=>response(value,gain)),percussion:{...percussion,kick:response(percussion.kick,percussionGain),bass:response(percussion.bass,percussionGain),snare:response(percussion.snare,percussionGain),tom_low:response(percussion.tom_low??percussion.tomLow,percussionGain),tom_mid:response(percussion.tom_mid??percussion.tomMid,percussionGain),tom_high:response(percussion.tom_high??percussion.tomHigh,percussionGain),cymbal:response(percussion.cymbal,percussionGain)}};
  }
  function syncControls(){
    const running=!!state.running,calibrating=!!state.calibrating;
    button.disabled=busy||!available.length;button.textContent=running?'STOP AUDIO':'START AUDIO';
    sourceSelect.disabled=busy||!available.length;
    if(zeroizeStatus)zeroizeStatus.textContent=calibrating?'Collecting ambient noise… keep music paused.':state.zeroized?'Ambient-noise calibration active.':'No ambient-noise calibration.';
    if(zeroizeStart)zeroizeStart.disabled=busy||!running||calibrating;
    if(zeroizeFinish)zeroizeFinish.disabled=busy||!running||!calibrating;
    if(zeroizeClear)zeroizeClear.disabled=busy||(!state.zeroized&&!calibrating);
  }
  function render(next){
    state=next||state;activeSource=state.source||null;
    const shown=visualState(state);
    for(const[name,element]of Object.entries(meters))if(element)element.style.width=`${clamp01(shown[name])*100}%`;
    root.PercussionDisplay?.render(shown.percussion||{});root.WebGLMusicVisualizer?.render(shown);syncControls();
  }
  async function api(path,options){
    const response=await fetch(`/api/audio-analysis/${path}`,options);
    const data=await response.json();if(!response.ok)throw Error(data.error||`HTTP ${response.status}`);return data;
  }
  async function command(task){
    if(busy)return;busy=true;syncControls();
    try{await task()}catch(error){if(status)status.textContent=`Audio error: ${error.message}`}
    finally{busy=false;syncControls()}
  }
  function cancelPoll(){epoch++;if(pollTimer){clearTimeout(pollTimer);pollTimer=null}}
  function schedulePoll(token,delay=100){if(token===epoch)pollTimer=setTimeout(()=>poll(token),delay)}
  async function poll(token){
    if(token!==epoch)return;
    try{
      const next=await api('session/state',{cache:'no-store'});
      if(token!==epoch)return;
      render(next);
      if(!next.running){
        if(capture.running)await capture.stop();
        if(status)status.textContent='Audio source stopped.';
        return;
      }
      schedulePoll(token);
    }catch(error){
      if(token!==epoch)return;
      if(status)status.textContent=`Audio state error: ${error.message}`;
      schedulePoll(token,500);
    }
  }
  async function stopSource(){
    cancelPoll();await capture.stop();
    render(await api('session/stop',{method:'POST'}));
    if(status)status.textContent='Audio stopped.';
  }
  async function startSource(source){
    if(!available.includes(source))throw Error(`Audio source unavailable: ${source}`);
    cancelPoll();await capture.stop();
    const token=epoch;
    const next=await api('source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source,running:true})});
    render(next);sourceSelect.value=source;
    try{
      if(source==='browser')await capture.start(frame=>{if(token===epoch&&activeSource==='browser')render(frame)});
    }catch(error){
      render(await api('session/stop',{method:'POST'}));
      throw error;
    }
    if(token!==epoch)return;
    if(status)status.textContent=`${labels[source]||source} active · shared MusicAnalyzer → WebGL`;
    schedulePoll(token);
  }
  async function discover(){
    try{
      const result=await api('sources');available=result.sources||[];
      sourceSelect.replaceChildren();
      for(const source of available){const option=document.createElement('option');option.value=source;option.textContent=labels[source]||source;sourceSelect.append(option)}
      render(result.state);sourceSelect.value=available.includes(state.source)?state.source:(available[0]||'');
      if(!available.length){if(status)status.textContent='No audio capture sources are available.';return}
      if(state.running){
        if(state.source==='browser'){
          // Browser capture belongs to this page. Reattach explicitly after reload.
          render(await api('session/stop',{method:'POST'}));
          if(status)status.textContent='Browser microphone stopped after page reload. Start it again to grant capture.';
        }else{if(status)status.textContent=`${labels[state.source]||state.source} active.`;schedulePoll(epoch)}
      }
    }catch(error){if(status)status.textContent=`Audio discovery error: ${error.message}`}
    syncControls();
  }
  button.onclick=()=>command(async()=>{if(state.running)await stopSource();else await startSource(sourceSelect.value)});
  sourceSelect.onchange=()=>command(async()=>{const source=sourceSelect.value;if(state.running)await startSource(source);else{render(await api('source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source,running:false})}));if(status)status.textContent=`Selected ${labels[source]||source}.`}});
  async function calibrate(action){
    await command(async()=>{
      const next=await api(`zeroize/${action}`,{method:'POST'});
      render(next);
      if(status)status.textContent=action==='start'?'Collecting ambient noise. Pause music during calibration.':action==='finish'?'Ambient calibration saved.':'Ambient calibration cleared.';
    });
  }
  if(zeroizeStart)zeroizeStart.onclick=()=>calibrate('start');
  if(zeroizeFinish)zeroizeFinish.onclick=()=>calibrate('finish');
  if(zeroizeClear)zeroizeClear.onclick=()=>calibrate('clear');
  if(sensitivity){const syncSensitivity=()=>{if(sensitivityValue)sensitivityValue.textContent=`${visualGain().toFixed(0)}×`;render(state)};sensitivity.addEventListener('input',syncSensitivity);syncSensitivity()}
  function renderLighting(next){if(!lightingButton||!lightingStatus)return;if(!next.available){lightingButton.disabled=true;lightingButton.textContent='MUSIC LIGHTING UNAVAILABLE';lightingStatus.textContent='No lighting controller is attached to this WebUI runtime.';return}lightingButton.disabled=false;lightingButton.textContent=next.enabled?'DISABLE MUSIC LIGHTING':'ENABLE MUSIC LIGHTING';lightingStatus.textContent=next.connected?(next.enabled?'Music-reactive lighting enabled.':'Lighting connected · manual control retained.'):(next.enabled?'Music lighting enabled, waiting for hardware connection.':'Lighting backend available · hardware disconnected.')}
  async function refreshLighting(){if(!lightingButton)return;try{const next=await api('lighting');renderLighting(next)}catch(error){lightingButton.disabled=true;if(lightingStatus)lightingStatus.textContent=`Lighting status error: ${error.message}`}}
  async function refreshSongRecognition(){if(!songButton)return;try{const response=await fetch('/api/song-recognition/config'),config=await response.json();songButton.disabled=!config.configured;if(songStatus)songStatus.textContent=config.configured?`${config.provider||'Song recognition'} ready. Start the microphone, then identify.`:'No song recognition provider configured.'}catch(error){songButton.disabled=true;if(songStatus)songStatus.textContent=`Recognition status error: ${error.message}`}}
  if(lightingButton)lightingButton.onclick=async()=>{try{const current=await api('lighting'),next=await api('lighting',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:!current.enabled})});renderLighting(next)}catch(error){if(lightingStatus)lightingStatus.textContent=`Lighting control error: ${error.message}`}};
  if(songButton)songButton.onclick=async()=>{songButton.disabled=true;try{if(songStatus)songStatus.textContent='Listening for 8 seconds…';const clip=await capture.recordClip(8000);if(songStatus)songStatus.textContent='Identifying…';const response=await fetch('/api/song-recognition/identify',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:clip}),result=await response.json();if(!response.ok)throw Error(result.error||`HTTP ${response.status}`);if(!result.matched){if(songStatus)songStatus.textContent='No song match found.'}else{const song=result.song;if(songTitle)songTitle.textContent=song.title||'Unknown title';if(songArtist)songArtist.textContent=(song.artists||[]).join(', ')||'Unknown artist';if(songAlbum)songAlbum.textContent=song.album||'';if(songStatus)songStatus.textContent=`Identified by ${result.provider||'song recognition'}.`}}catch(error){if(songStatus)songStatus.textContent=`Recognition error: ${error.message}`}finally{songButton.disabled=false}};
  root.WebGLMusicVisualizer?.install();root.PercussionDisplay?.install();render(state);refreshLighting();refreshSongRecognition();discover();
})();
