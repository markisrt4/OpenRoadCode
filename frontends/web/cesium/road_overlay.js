'use strict';
window.ORCRoadOverlay = function(viewer,C,heightAt=()=>0,onError=()=>{},maxZoom=14) {
  const entries=new Map();
  let disposed=false,roadsVisible=true,placesVisible=false,lastCheck=0;
  function remove(entry) {
    entry.abort.abort();
    if(entry.roads)viewer.dataSources.remove(entry.roads,true);
    if(entry.places)viewer.dataSources.remove(entry.places,true);
  }
  async function attachPlaces(entry) {
    if(disposed || !placesVisible || entry.places || entry.placesPending || !entry.state)return;
    entry.placesPending=true;
    try {
      const places=new C.CustomDataSource('places-'+entry.key);
      for(const place of entry.state.places) {
        const point=place.position;
        const entity=places.entities.add({position:C.Cartesian3.fromRadians(point[0],point[1],heightAt(...point)+15),
          label:{text:place.name,font:'bold 15px sans-serif',fillColor:C.Color.WHITE,
            outlineColor:C.Color.BLACK,outlineWidth:3,style:C.LabelStyle.FILL_AND_OUTLINE,
            disableDepthTestDistance:Infinity,showBackground:true,
            backgroundColor:C.Color.BLACK.withAlpha(.65)}});
        entry.labels.push({entity,point});
      }
      places.show=placesVisible;
      await viewer.dataSources.add(places);
      if(disposed || entries.get(entry.key)!==entry){viewer.dataSources.remove(places,true);return;}
      places.show=placesVisible;entry.places=places;viewer.scene.requestRender();
    } catch(error) {
      if(!disposed)onError(error);
    } finally {
      entry.placesPending=false;
    }
  }
  async function load(entry,z,x,y) {
    try {
      const response=await fetch(`/data/roads/${z}/${x}/${y}`,{signal:entry.abort.signal});
      if(!response.ok)throw Error('Offline road tile unavailable');
      const state=await response.json();
      if(disposed || entries.get(entry.key)!==entry)return;
      const roads=new C.CustomDataSource('roads-'+entry.key);
      entry.labels=[];entry.state=state;
      function label(text,point,freeway=false) {
        const entity=roads.entities.add({position:C.Cartesian3.fromRadians(point[0],point[1],heightAt(...point)+15),
          label:{text,font:'11px sans-serif',fillColor:C.Color.WHITE,
            outlineColor:C.Color.BLACK,outlineWidth:3,style:C.LabelStyle.FILL_AND_OUTLINE,
            disableDepthTestDistance:Infinity,
            distanceDisplayCondition:freeway?undefined:new C.DistanceDisplayCondition(0,1000),
            showBackground:true,backgroundColor:C.Color.BLACK.withAlpha(.65)}});
        entry.labels.push({entity,point});
      }
      let names=0;const labeled=new Set();
      for(const road of state.roads) {
        const coordinates=road.points.flatMap(point=>[point[0],point[1]]);
        const freeway=road.kind==='motorway'||road.kind==='trunk';
        if(road.geometry_visible!==false && !['minor','residential','unclassified','service'].includes(road.kind))roads.entities.add({polyline:{positions:C.Cartesian3.fromRadiansArray(coordinates),clampToGround:true,
          width:freeway?3:1.5,material:C.Color.fromCssColorString(freeway?'#ffd166':'#e7eff6').withAlpha(.8)}});
        if(road.label && !labeled.has(road.label) && names<8) {
          labeled.add(road.label);names++;label(road.label,road.points[Math.floor(road.points.length/2)],freeway);
        }
      }
      roads.show=roadsVisible;
      await viewer.dataSources.add(roads);
      if(disposed || entries.get(entry.key)!==entry){
        viewer.dataSources.remove(roads,true);return;
      }
      entry.roads=roads;
      if(placesVisible)attachPlaces(entry);
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
    let z=Math.max(8,Math.min(maxZoom,13,Math.floor(Math.log2(20000000/height))));
    let n=2**z;
    const tileX=(position.longitude+Math.PI)/(2*Math.PI)*n;
    const x=Math.floor(tileX);
    const latitude=Math.max(-1.48,Math.min(1.48,position.latitude));
    const tileY=(1-Math.asinh(Math.tan(latitude))/Math.PI)/2*n;
    const y=Math.floor(tileY);
    const wanted=new Set();
    const view=viewer.camera.computeViewRectangle?.(viewer.scene.globe.ellipsoid);
    let xFirst,xLast,yFirst,yLast;
    if(view && view.east>=view.west) {
      function range(level) {
        const count=2**level;
        return [Math.floor((view.west+Math.PI)/(2*Math.PI)*count),
          Math.floor((view.east+Math.PI)/(2*Math.PI)*count),
          Math.floor((1-Math.asinh(Math.tan(Math.min(1.48,view.north)))/Math.PI)/2*count),
          Math.floor((1-Math.asinh(Math.tan(Math.max(-1.48,view.south)))/Math.PI)/2*count)];
      }
      [xFirst,xLast,yFirst,yLast]=range(z);
      while((xLast-xFirst+1)*(yLast-yFirst+1)>6 && z>8) {
        z--;n=2**z;[xFirst,xLast,yFirst,yLast]=range(z);
      }
      if((xLast-xFirst+1)*(yLast-yFirst+1)>6) {
        const centreX=(position.longitude+Math.PI)/(2*Math.PI)*n;
        const centreY=(1-Math.asinh(Math.tan(latitude))/Math.PI)/2*n;
        const baseX=Math.floor(centreX),baseY=Math.floor(centreY);
        const xDirection=centreX-baseX>=.5?1:-1,yDirection=centreY-baseY>=.5?1:-1;
        xFirst=Math.min(baseX,baseX+xDirection);xLast=Math.max(baseX,baseX+xDirection);
        yFirst=Math.min(baseY,baseY+yDirection);yLast=Math.max(baseY,baseY+yDirection);
      }
    } else {
      const xDirection=tileX-x>=.5?1:-1,yDirection=tileY-y>=.5?1:-1;
      xFirst=Math.min(x,x+xDirection);xLast=Math.max(x,x+xDirection);
      yFirst=Math.min(y,y+yDirection);yLast=Math.max(y,y+yDirection);
    }
    for(let xx=xFirst;xx<=xLast;xx++)for(let yy=yFirst;yy<=yLast;yy++) {
      const wrappedX=(xx+n)%n;if(yy<0||yy>=n)continue;
      const key=`${z}/${wrappedX}/${yy}`;wanted.add(key);
      if(!entries.has(key)) {const entry={key,abort:new AbortController(),roads:null,places:null,placesPending:false,state:null,labels:[]};entries.set(key,entry);load(entry,z,wrappedX,yy);}
    }
    for(const [key,entry] of entries)if(!wanted.has(key)){remove(entry);entries.delete(key);}
  }
  const unsubscribe=viewer.scene.postRender.addEventListener(update);
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit('© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · ODbL 1.0',true));
  return {
    set roadsVisible(value){roadsVisible=Boolean(value);lastCheck=0;entries.forEach(entry=>{if(entry.roads)entry.roads.show=roadsVisible;});viewer.scene.requestRender();},
    get roadsVisible(){return roadsVisible;},
    set placesVisible(value){placesVisible=Boolean(value);lastCheck=0;entries.forEach(entry=>{
      if(entry.places)entry.places.show=placesVisible;else if(placesVisible)attachPlaces(entry);
    });viewer.scene.requestRender();},
    get placesVisible(){return placesVisible;},
    refreshGround(){entries.forEach(entry=>(entry.labels||[]).forEach(({entity,point})=>{
      entity.position=C.Cartesian3.fromRadians(point[0],point[1],heightAt(...point)+15);
    }));},destroy(){disposed=true;unsubscribe();entries.forEach(remove);entries.clear();}};
};
