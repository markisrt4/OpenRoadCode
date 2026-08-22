(() => {
  const root = window.OpenRoadCodeWeb = window.OpenRoadCodeWeb || {};
  class MicrophoneMusicAnalyzer {
    constructor({frameSamples=2048}={}) { Object.assign(this,{frameSamples,audioContext:null,stream:null,source:null,processor:null,sink:null,running:false,onState:null,inFlight:false,lastState:null}); }
    async start(callback) {
      if(this.running)return;
      if(!navigator.mediaDevices?.getUserMedia)throw Error('Microphone capture is not available in this browser.');
      this.onState=callback;
      this.stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false,channelCount:1},video:false});
      const A=window.AudioContext||window.webkitAudioContext;this.audioContext=new A({latencyHint:'interactive'});await this.audioContext.resume();this.source=this.audioContext.createMediaStreamSource(this.stream);
      // Browser responsibility ends at PCM capture. Python owns the DSP.
      this.processor=this.audioContext.createScriptProcessor(this.frameSamples,1,1);this.sink=this.audioContext.createGain();this.sink.gain.value=0;
      this.processor.onaudioprocess=e=>{if(!this.running||this.inFlight)return;this._send(e.inputBuffer.getChannelData(0))};
      this.source.connect(this.processor);this.processor.connect(this.sink);this.sink.connect(this.audioContext.destination);this.running=true;
    }
    async stop(){this.running=false;if(this.processor)this.processor.onaudioprocess=null;this.source?.disconnect();this.processor?.disconnect();this.sink?.disconnect();this.stream?.getTracks().forEach(t=>t.stop());if(this.audioContext)await this.audioContext.close();this.audioContext=this.stream=this.source=this.processor=this.sink=null}
    async zeroize(){const r=await fetch('/api/audio-analysis/browser/zeroize',{method:'POST'});if(!r.ok)throw Error((await r.json()).error||'Zeroize failed');return r.json()}
    async setSensitivity(value){const r=await fetch('/api/audio-analysis/browser/sensitivity',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value})});if(!r.ok)throw Error((await r.json()).error||'Sensitivity update failed');return r.json()}
    async _send(samples){this.inFlight=true;try{const pcm=new Int16Array(samples.length);for(let i=0;i<samples.length;i++){const s=Math.max(-1,Math.min(1,samples[i]));pcm[i]=s<0?s*32768:s*32767}const r=await fetch('/api/audio-analysis/browser/frame',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Sample-Rate':String(this.audioContext.sampleRate)},body:pcm.buffer});if(!r.ok)throw Error((await r.json()).error||'Audio analysis failed');const state=await r.json();this.lastState=state;this.onState?.(state)}catch(e){console.warn('OpenRoadCode browser audio transport:',e)}finally{this.inFlight=false}}
  }
  root.MicrophoneMusicAnalyzer=MicrophoneMusicAnalyzer;
})();
