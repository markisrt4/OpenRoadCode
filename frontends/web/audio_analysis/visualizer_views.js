// SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
// SPDX-License-Identifier: MIT
// Presentation-only switching: both views consume the existing audio session.
(()=>{
  const root=window.OpenRoadCodeWeb||{};
  const buttons=[...document.querySelectorAll('[data-visualizer-view]')];
  if(!buttons.length)return;
  root.WebGLMusicVisualizer?.install();
  root.PercussionDisplay?.install();
  const panels={visualization:document.getElementById('mv-webgl-stage'),drums:document.getElementById('music-drum-kit')};
  const toggle=document.getElementById('mv-toggle-drums');
  if(toggle)toggle.hidden=true;
  function show(view){
    for(const[name,panel]of Object.entries(panels)){
      if(!panel)continue;
      panel.hidden=name!==view;
      panel.setAttribute('role','tabpanel');
      panel.setAttribute('aria-labelledby',`music-view-${name}`);
    }
    for(const button of buttons){
      const active=button.dataset.visualizerView===view;
      button.setAttribute('aria-selected',String(active));
      button.tabIndex=active?0:-1;
      button.classList.toggle('primary',active);
    }
    window.dispatchEvent(new Event('resize'));
  }
  buttons.forEach((button,index)=>{
    button.onclick=()=>show(button.dataset.visualizerView);
    button.onkeydown=event=>{
      if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
        event.preventDefault();
        const next=buttons[(index+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length];
        show(next.dataset.visualizerView);next.focus();
      }
    };
  });
  show('visualization');
})();
