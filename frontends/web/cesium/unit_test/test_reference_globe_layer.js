'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const draw=[];
const canvasContext={fillStyle:null,fillRect(...args){draw.push(['fill',this.fillStyle,...args]);},
  beginPath(){},moveTo(){},lineTo(){},closePath(){},fill(rule){draw.push(['land',this.fillStyle,rule]);}};
const context={window:{},fetch:async()=>({ok:true,json:async()=>({features:[{geometry:{type:'Polygon',
  coordinates:[[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]]]}}]})}),document:{createElement:()=>({
  width:0,height:0,getContext:()=>canvasContext,toDataURL:()=> 'data:image/png;base64,reference'})}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../reference_globe_layer.js'),'utf8'),context);

test('blue base does not attach after viewer closes during image load',async()=>{
  let resolve,attached=0,destroyed=false;
  const C={Rectangle:{fromRadians:(...values)=>values},SingleTileImageryProvider:{
    fromUrl:()=>new Promise(done=>{resolve=done;})
  }};
  const viewer={isDestroyed:()=>destroyed,imageryLayers:{addImageryProvider(){attached++;}}};
  const pending=context.window.ORCReferenceGlobeLayer(viewer,C);
  // The offline land/lake reads complete before the image-provider load starts.
  await new Promise(done=>setImmediate(done));
  assert.equal(typeof resolve,'function');
  destroyed=true;
  resolve({url:'base'});
  assert.equal(await pending,null);
  assert.equal(attached,0);
  assert.deepEqual(draw[0],['fill','#174963',0,0,2048,1024]);
  assert.deepEqual(draw.at(-2),['land','#456f4e','evenodd']);
  assert.deepEqual(draw.at(-1),['land','#174963','evenodd']);
});


test('bundled land/lakes paint US interiors as land, independent of installed packs',async()=>{
  const probes=[[-105,39],[-98,38],[-110,47],[-100,20],[-60,-10],[-140,0]];
  const colors=new Map();let rings=[];
  function contains(ring,x,y){
    let hit=false;
    for(let i=0,j=ring.length-1;i<ring.length;j=i++){
      const [a,b]=ring[i],[c,d]=ring[j];
      if((b>y)!==(d>y)&&x<(c-a)*(y-b)/(d-b)+a)hit=!hit;
    }
    return hit;
  }
  const drawing={fillStyle:null,fillRect(){probes.forEach(p=>colors.set(p,this.fillStyle));},
    beginPath(){rings=[];},moveTo(x,y){rings.push([[x,y]]);},
    lineTo(x,y){rings.at(-1).push([x,y]);},closePath(){},
    fill(){for(const point of probes){
      const x=(point[0]+180)*2048/360,y=(90-point[1])*1024/180;
      if(rings.filter(ring=>contains(ring,x,y)).length%2)colors.set(point,this.fillStyle);
    }}};
  let attached;
  const context={window:{},fetch:async url=>({ok:true,json:async()=>JSON.parse(
    fs.readFileSync(path.join(__dirname,'../../../../resources/maps',
      url.includes('lakes')?'world_lakes.geojson':'world_land.geojson'),'utf8'))}),
    document:{createElement:()=>({getContext:()=>drawing,toDataURL:()=> 'data:image/png;base64,test'})}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../reference_globe_layer.js'),'utf8'),context);
  const C={Rectangle:{fromRadians:()=>({})},SingleTileImageryProvider:{fromUrl:async()=>({})}};
  const viewer={isDestroyed:()=>false,imageryLayers:{addImageryProvider(provider){attached=provider;return {};}}};
  await context.window.ORCReferenceGlobeLayer(viewer,C);
  for(const point of probes.slice(0,5))assert.equal(colors.get(point),'#456f4e',String(point));
  assert.equal(colors.get(probes[5]),'#174963');
  assert.equal(attached.orcLayerRole,'reference-globe');
});
