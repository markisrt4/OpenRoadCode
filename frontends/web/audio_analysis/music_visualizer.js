(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  const button=document.getElementById('music-visualizer-toggle');
  const status=document.getElementById('music-visualizer-status');
  const lightingButton=document.getElementById('music-lighting-toggle');
  const lightingStatus=document.getElementById('music-lighting-status');
  const songButton=document.getElementById('music-song-identify');
  const songStatus=document.getElementById('music-song-status');
  const songTitle=document.getElementById('music-song-title');
  const songArtist=document.getElementById('music-song-artist');
  const songAlbum=document.getElementById('music-song-album');
  const meters={bass:document.getElementById('music-bass'),mid:document.getElementById('music-mid'),treble:document.getElementById('music-treble')};
  if(!button||!root.BrowserPcmCapture)return;

  const capture=new root.BrowserPcmCapture();
  let state={level:0,bass:0,mid:0,treble:0,spectrum:Array(24).fill(0)};

  function render(next){
    state=next||state;
    for(const [name,element] of Object.entries(meters)){
      if(element)element.style.width=`${Math.max(0,Math.min(1,state[name]||0))*100}%`;
    }
    root.KickMode?.detect(state.percussion?.kick||0);
    root.WebGLMusicVisualizer?.render(state);
  }

  function renderLighting(next){
    if(!lightingButton||!lightingStatus)return;
    if(!next.available){
      lightingButton.disabled=true;
      lightingButton.textContent='MUSIC LIGHTING UNAVAILABLE';
      lightingStatus.textContent='No lighting controller is attached to this WebUI runtime.';
      return;
    }
    lightingButton.disabled=false;
    lightingButton.textContent=next.enabled?'DISABLE MUSIC LIGHTING':'ENABLE MUSIC LIGHTING';
    lightingStatus.textContent=next.connected
      ?(next.enabled?'Music-reactive lighting enabled.':'Lighting connected · manual control retained.')
      :(next.enabled?'Music lighting enabled, waiting for hardware connection.':'Lighting backend available · hardware disconnected.');
  }

  async function refreshLighting(){
    if(!lightingButton)return;
    try{
      const response=await fetch('/api/audio-analysis/lighting');
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      renderLighting(await response.json());
    }catch(error){
      lightingButton.disabled=true;
      if(lightingStatus)lightingStatus.textContent=`Lighting status error: ${error.message}`;
    }
  }

  async function refreshSongRecognition(){
    if(!songButton)return;
    try{
      const response=await fetch('/api/song-recognition/config');
      const config=await response.json();
      songButton.disabled=!config.configured;
      if(songStatus) songStatus.textContent=config.configured
        ?`${config.provider||'Song recognition'} ready. Start the microphone, then identify.`
        :'No song recognition provider configured.';
    }catch(error){
      songButton.disabled=true;
      if(songStatus)songStatus.textContent=`Recognition status error: ${error.message}`;
    }
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

  if(lightingButton){
    lightingButton.onclick=async()=>{
      try{
        const current=await fetch('/api/audio-analysis/lighting').then(response=>response.json());
        const response=await fetch('/api/audio-analysis/lighting',{
          method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:!current.enabled}),
        });
        const next=await response.json();
        if(!response.ok)throw new Error(next.error||`HTTP ${response.status}`);
        renderLighting(next);
      }catch(error){if(lightingStatus)lightingStatus.textContent=`Lighting control error: ${error.message}`;}
    };
  }

  if(songButton){
    songButton.onclick=async()=>{
      songButton.disabled=true;
      try{
        if(songStatus)songStatus.textContent='Listening for 8 seconds…';
        const clip=await capture.recordClip(8000);
        if(songStatus)songStatus.textContent='Identifying…';
        const response=await fetch('/api/song-recognition/identify',{
          method:'POST',headers:{'Content-Type':'application/octet-stream'},body:clip,
        });
        const result=await response.json();
        if(!response.ok)throw new Error(result.error||`HTTP ${response.status}`);
        if(!result.matched){
          if(songStatus)songStatus.textContent='No song match found.';
        }else{
          const song=result.song;
          if(songTitle)songTitle.textContent=song.title||'Unknown title';
          if(songArtist)songArtist.textContent=(song.artists||[]).join(', ')||'Unknown artist';
          if(songAlbum)songAlbum.textContent=song.album||'';
          if(songStatus)songStatus.textContent=`Identified by ${result.provider||'song recognition'}.`;
        }
      }catch(error){if(songStatus)songStatus.textContent=`Recognition error: ${error.message}`;}
      finally{songButton.disabled=false;}
    };
  }

  render(state);
  refreshLighting();
  refreshSongRecognition();
})();
