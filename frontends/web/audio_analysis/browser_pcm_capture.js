(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};

  class BrowserPcmCapture {
    constructor({frameSamples=2048}={}) {
      this.frameSamples=frameSamples;
      this.audioContext=null;
      this.stream=null;
      this.source=null;
      this.processor=null;
      this.sink=null;
      this.running=false;
      this.inFlight=false;
      this.onState=null;
    }

    async start(callback) {
      if(this.running)return;
      if(!navigator.mediaDevices?.getUserMedia)throw Error('Microphone capture is unavailable in this browser.');
      this.onState=callback;
      this.stream=await navigator.mediaDevices.getUserMedia({
        audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false,channelCount:1},
        video:false
      });
      const AudioContext=window.AudioContext||window.webkitAudioContext;
      this.audioContext=new AudioContext({latencyHint:'interactive'});
      await this.audioContext.resume();
      this.source=this.audioContext.createMediaStreamSource(this.stream);
      this.processor=this.audioContext.createScriptProcessor(this.frameSamples,1,1);
      this.sink=this.audioContext.createGain();
      this.sink.gain.value=0;
      this.processor.onaudioprocess=event=>{
        if(this.running&&!this.inFlight)this._send(event.inputBuffer.getChannelData(0));
      };
      this.source.connect(this.processor);
      this.processor.connect(this.sink);
      this.sink.connect(this.audioContext.destination);
      this.running=true;
    }

    async stop() {
      this.running=false;
      if(this.processor)this.processor.onaudioprocess=null;
      this.source?.disconnect();
      this.processor?.disconnect();
      this.sink?.disconnect();
      this.stream?.getTracks().forEach(track=>track.stop());
      if(this.audioContext)await this.audioContext.close();
      this.audioContext=this.stream=this.source=this.processor=this.sink=null;
    }

    async recordClip(durationMs=8000) {
      if(!this.running||!this.stream)throw Error('Start the microphone before identifying a song.');
      if(!window.MediaRecorder)throw Error('Encoded audio recording is unavailable in this browser.');
      const chunks=[];
      const recorder=new MediaRecorder(this.stream);
      return new Promise((resolve,reject)=>{
        recorder.ondataavailable=event=>{if(event.data?.size)chunks.push(event.data);};
        recorder.onerror=event=>reject(event.error||Error('Audio clip recording failed.'));
        recorder.onstop=async()=>{
          try{
            const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});
            resolve(await blob.arrayBuffer());
          }catch(error){reject(error);}
        };
        recorder.start();
        setTimeout(()=>{if(recorder.state!=='inactive')recorder.stop();},durationMs);
      });
    }

    async _send(samples) {
      this.inFlight=true;
      try {
        const pcm=new Int16Array(samples.length);
        for(let index=0;index<samples.length;index++){
          const sample=Math.max(-1,Math.min(1,samples[index]));
          pcm[index]=sample<0?sample*32768:sample*32767;
        }
        const response=await fetch('/api/audio-analysis/browser/frame',{
          method:'POST',
          headers:{'Content-Type':'application/octet-stream','X-Sample-Rate':String(this.audioContext.sampleRate)},
          body:pcm.buffer
        });
        const state=await response.json();
        if(!response.ok)throw Error(state.error||'Audio analysis failed');
        this.onState?.(state);
      } catch(error) {
        console.warn('OpenRoadCode browser PCM transport:',error);
      } finally {
        this.inFlight=false;
      }
    }
  }

  root.BrowserPcmCapture=BrowserPcmCapture;
})();
