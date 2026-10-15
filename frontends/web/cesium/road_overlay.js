'use strict';
window.ORCRoadOverlay = function(viewer,C,heightAt=()=>0,onError=()=>{},maxZoom=14) {
  const entries=new Map();
  let disposed=false,roadsVisible=true,placesVisible=false,lastCheck=0;
  function remove(entry) {
    entry.abort.abort();
    if(entry.roads)viewer.dataSources.remove(entry.roads,true);
    if(entry.places)viewer.dataSources.remove(entry.places,true);
  }
  async function load(entry,z,x,y) {
    try {
      const response=await fetch(`/data/roads/${z}/${x}/${y}`,{signal:entry.abort.signal});
      if(!response.ok)throw Error('Offline road tile unavailable');
      const state=await response.json();
      if(disposed || entries.get(entry.key)!==entry)return;
      const roads=new C.CustomDataSource('roads-'+entry.key);
      const places=new C.CustomDataSource('places-'+entry.key);
      entry.labels=[];
      function label(source,text,point,city,freeway=false) {
        const entity=source.entities.add({position:C.Cartesian3.fromRadians(point[0],point[1],heightAt(...point)+15),
          label:{text,font:city?'bold 15px sans-serif':'11px sans-serif',fillColor:C.Color.WHITE,
            outlineColor:C.Color.BLACK,outlineWidth:3,style:C.LabelStyle.FILL_AND_OUTLINE,
            disableDepthTestDistance:Infinity,
            distanceDisplayCondition:city||freeway?undefined:new C.DistanceDisplayCondition(0,1000),
            showBackground:true,backgroundColor:C.Color.BLACK.withAlpha(.65)}});
        entry.labels.push({entity,point});
      }
      let names=0;const labeled=new Set();
      for(const road of state.roads) {
        const coordinates=road.points.flatMap(point=>[point[0],point[1]]);
        const freeway=road.kind==='motorway'||road.kind==='trunk';
        if(!['minor','residential','unclassified','service'].includes(road.kind))roads.entities.add({polyline:{positions:C.Cartesian3.fromRadiansArray(coordinates),clampToGround:true,
          width:freeway?3:1.5,material:C.Color.fromCssColorString(freeway?'#ffd166':'#e7eff6').withAlpha(.8)}});
        if(road.label && !labeled.has(road.label) && names<8) {
          labeled.add(road.label);names++;label(roads,road.label,road.points[Math.floor(road.points.length/2)],false,freeway);
        }
      }
      for(const place of state.places)label(places,place.name,place.position,true);
      roads.show=roadsVisible;places.show=placesVisible;
      await viewer.dataSources.add(roads);
      await viewer.dataSources.add(places);
      if(disposed || entries.get(entry.key)!==entry){
        viewer.dataSources.remove(roads,true);viewer.dataSources.remove(places,true);return;
      }
      entry.roads=roads;entry.places=places;
      viewer.scene.requestRender();
    } catch(error) {if(!disposed && error.name!=='AbortError')onError(error);}
  }
  function update() {
    const now=Date.now();if(disposed || (!roadsVisible&&!placesVisible) || now-lastCheck<500)return;lastCheck=now;
    const centre=new C.Cartesian2(viewer.scene.canvas.clientWidth/2,viewer.scene.canvas.clientHeight/2);
    const ray=viewer.camera.getPickRay(centre);
    const anchor=(ray && viewer.scene.globe.pick(ray,viewer.scene)) || viewer.camera.pickEllipsoid(centre);
    if(!anchor)return;
    const position=C.Cartographic.fromCartesian(anchor);
    const height=Math.max(100,viewer.camera.positionCartographic.height);
    const z=Math.max(8,Math.min(maxZoom,Math.floor(Math.log2(20000000/height))));
    const n=2**z;
    const x=Math.floor((position.longitude+Math.PI)/(2*Math.PI)*n);
    const latitude=Math.max(-1.48,Math.min(1.48,position.latitude));
    const y=Math.floor((1-Math.asinh(Math.tan(latitude))/Math.PI)/2*n);
    const wanted=new Set();
    for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++) {
      const xx=(x+dx+n)%n,yy=y+dy;if(yy<0||yy>=n)continue;
      const key=`${z}/${xx}/${yy}`;wanted.add(key);
      if(!entries.has(key)) {const entry={key,abort:new AbortController(),roads:null,places:null};entries.set(key,entry);load(entry,z,xx,yy);}
    }
    for(const [key,entry] of entries)if(!wanted.has(key)){remove(entry);entries.delete(key);}
  }
  const unsubscribe=viewer.scene.postRender.addEventListener(update);
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit('© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · ODbL 1.0',true));
  return {
    set roadsVisible(value){roadsVisible=Boolean(value);lastCheck=0;entries.forEach(entry=>{if(entry.roads)entry.roads.show=roadsVisible;});viewer.scene.requestRender();},
    get roadsVisible(){return roadsVisible;},
    set placesVisible(value){placesVisible=Boolean(value);lastCheck=0;entries.forEach(entry=>{if(entry.places)entry.places.show=placesVisible;});viewer.scene.requestRender();},
    get placesVisible(){return placesVisible;},
    refreshGround(){entries.forEach(entry=>(entry.labels||[]).forEach(({entity,point})=>{
      entity.position=C.Cartesian3.fromRadians(point[0],point[1],heightAt(...point)+15);
    }));},destroy(){disposed=true;unsubscribe();entries.forEach(remove);entries.clear();}};
};
