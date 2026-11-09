/* Semantic layer controls shared by standalone buttons and the ORC drawer. */
'use strict';
window.ORCMapLayers = function(viewer,snapshot,document) {
  const actions=['imagery','buildings','roads','places','terrain','terrain-scale','terrain-cues','references'];
  const labels={imagery:'Imagery',buildings:'Buildings',roads:'Roads',places:'Places',terrain:'Relief',
    'terrain-scale':'Height','terrain-cues':'Terrain cues',references:'Grid'};
  let imageryVisible=true,disposed=false;
  const imageryAvailable=Boolean(snapshot.imagery_pyramids?.length || snapshot.imagery || snapshot.imagery_layers?.length || snapshot.map_tiles?.tiles.some(t=>t.imagery_url));
  const remove=viewer.imageryLayers.layerAdded.addEventListener(layer=>{if(layer.imageryProvider?.orcLayerRole!=='terrain-cues')layer.show=imageryVisible;});
  function state() {
    return actions.map(action=>{
      const button=document.getElementById(action);
      const available=action==='imagery'?imageryAvailable:Boolean(button && !button.disabled);
      return {action,label:action==='terrain-scale'?button.textContent:labels[action],available,
        enabled:available && (action==='imagery'?imageryVisible:button.getAttribute('aria-pressed')==='true')};
    });
  }
  function request(action) {
    if(disposed || viewer.isDestroyed() || !actions.includes(action))return false;
    if(!state().find(item=>item.action===action).available)return false;
    if(action==='imagery') {
      imageryVisible=!imageryVisible;
      for(let i=0;i<viewer.imageryLayers.length;i++){const layer=viewer.imageryLayers.get(i);if(layer.imageryProvider?.orcLayerRole!=='terrain-cues')layer.show=imageryVisible;}
      viewer.scene.requestRender();
    } else {
      const button=document.getElementById(action);
      if(typeof button.onclick!=='function')return false;
      button.onclick();
    }
    return true;
  }
  return {state,request,destroy(){disposed=true;remove();}};
};
