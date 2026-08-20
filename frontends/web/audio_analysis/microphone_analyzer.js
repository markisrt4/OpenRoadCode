(() => {
  const root = (window.OpenRoadCodeWeb = window.OpenRoadCodeWeb || {});

  class MicrophoneMusicAnalyzer {
    constructor({ fftSize = 2048, bandCount = 24 } = {}) {
      this.fftSize = fftSize;
      this.bandCount = bandCount;
      this.audioContext = null;
      this.analyser = null;
      this.stream = null;
      this.source = null;
      this.frequencyData = null;
      this.timeData = null;
      this.running = false;
      this.animationFrame = null;
      this.onState = null;
      this.bandPeaks = new Float32Array(bandCount).fill(1);
      this.summaryPeaks = { bass: 1, mid: 1, treble: 1 };
    }

    async start(onState) {
      if (this.running) return;
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Microphone capture is not available in this browser.');
      }

      this.onState = onState;
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          channelCount: 1,
        },
        video: false,
      });

      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContextClass({ latencyHint: 'interactive' });
      await this.audioContext.resume();

      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = this.fftSize;
      this.analyser.smoothingTimeConstant = 0.18;
      this.analyser.minDecibels = -100;
      this.analyser.maxDecibels = -20;

      this.source = this.audioContext.createMediaStreamSource(this.stream);
      this.source.connect(this.analyser);

      this.frequencyData = new Float32Array(this.analyser.frequencyBinCount);
      this.timeData = new Float32Array(this.analyser.fftSize);
      this.running = true;
      this._tick();
    }

    async stop() {
      this.running = false;
      if (this.animationFrame !== null) cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
      this.source?.disconnect();
      this.stream?.getTracks().forEach((track) => track.stop());
      if (this.audioContext) await this.audioContext.close();
      this.source = null;
      this.stream = null;
      this.audioContext = null;
      this.analyser = null;
    }

    _normalizedBand(lowHz, highHz, peakKey = null, index = null) {
      const sampleRate = this.audioContext.sampleRate;
      const binHz = sampleRate / this.fftSize;
      const lowBin = Math.max(1, Math.floor(lowHz / binHz));
      const highBin = Math.min(this.frequencyData.length, Math.ceil(highHz / binHz));
      if (highBin <= lowBin) return 0;

      let sumPower = 0;
      let count = 0;
      for (let i = lowBin; i < highBin; i += 1) {
        const db = this.frequencyData[i];
        if (!Number.isFinite(db)) continue;
        const linear = Math.pow(10, db / 20);
        sumPower += linear * linear;
        count += 1;
      }
      if (!count) return 0;

      const raw = Math.sqrt(sumPower / count);
      if (peakKey) {
        this.summaryPeaks[peakKey] = Math.max(raw, this.summaryPeaks[peakKey] * 0.992, 1e-6);
        return Math.min(1, raw / this.summaryPeaks[peakKey]);
      }
      if (index !== null) {
        this.bandPeaks[index] = Math.max(raw, this.bandPeaks[index] * 0.992, 1e-6);
        return Math.min(1, raw / this.bandPeaks[index]);
      }
      return raw;
    }

    _spectrum() {
      const minHz = 31.25;
      const maxHz = Math.min(16000, this.audioContext.sampleRate / 2);
      const ratio = Math.pow(maxHz / minHz, 1 / this.bandCount);
      const bands = [];
      let low = minHz;
      for (let i = 0; i < this.bandCount; i += 1) {
        const high = low * ratio;
        bands.push(this._normalizedBand(low, high, null, i));
        low = high;
      }
      return bands;
    }

    _tick() {
      if (!this.running || !this.analyser) return;

      this.analyser.getFloatFrequencyData(this.frequencyData);
      this.analyser.getFloatTimeDomainData(this.timeData);

      let sumSquares = 0;
      let peak = 0;
      for (const sample of this.timeData) {
        sumSquares += sample * sample;
        peak = Math.max(peak, Math.abs(sample));
      }
      const rms = Math.sqrt(sumSquares / this.timeData.length);

      const state = {
        level: Math.min(1, rms * 4),
        peak: Math.min(1, peak),
        bass: this._normalizedBand(20, 250, 'bass'),
        mid: this._normalizedBand(250, 4000, 'mid'),
        treble: this._normalizedBand(4000, 16000, 'treble'),
        spectrum: this._spectrum(),
        sampleRateHz: this.audioContext.sampleRate,
        fftSize: this.fftSize,
      };

      this.onState?.(state);
      this.animationFrame = requestAnimationFrame(() => this._tick());
    }
  }

  root.MicrophoneMusicAnalyzer = MicrophoneMusicAnalyzer;
})();
