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
      this.activityPeaks = { kick: 1e-6, bass: 1e-6, snare: 1e-6, cymbal: 1e-6 };
      this.previousActivity = { kick: 0, bass: 0, snare: 0, cymbal: 0 };
      this.previousFluxBins = null;
      this.fluxHistory = [];
      this.lastBeatAt = -Infinity;
    }

    async start(onState) {
      if (this.running) return;
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('Microphone capture is not available in this browser.');

      this.onState = onState;
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
        video: false,
      });

      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContextClass({ latencyHint: 'interactive' });
      await this.audioContext.resume();

      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = this.fftSize;
      this.analyser.smoothingTimeConstant = 0.03;
      this.analyser.minDecibels = -100;
      this.analyser.maxDecibels = -20;
      this.source = this.audioContext.createMediaStreamSource(this.stream);
      this.source.connect(this.analyser);
      this.frequencyData = new Float32Array(this.analyser.frequencyBinCount);
      this.timeData = new Float32Array(this.analyser.fftSize);
      this.previousFluxBins = null;
      this.fluxHistory = [];
      this.lastBeatAt = -Infinity;
      this.previousActivity = { kick: 0, bass: 0, snare: 0, cymbal: 0 };
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
      this.source = this.stream = this.audioContext = this.analyser = null;
      this.previousFluxBins = null;
      this.fluxHistory = [];
    }

    _rawBand(lowHz, highHz) {
      const binHz = this.audioContext.sampleRate / this.fftSize;
      const lowBin = Math.max(1, Math.floor(lowHz / binHz));
      const highBin = Math.min(this.frequencyData.length, Math.ceil(highHz / binHz));
      if (highBin <= lowBin) return 0;
      let sumPower = 0, count = 0;
      for (let i = lowBin; i < highBin; i += 1) {
        const db = this.frequencyData[i];
        if (!Number.isFinite(db)) continue;
        const linear = Math.pow(10, db / 20);
        sumPower += linear * linear;
        count += 1;
      }
      return count ? Math.sqrt(sumPower / count) : 0;
    }

    _normalizedBand(lowHz, highHz, peakKey = null, index = null) {
      const raw = this._rawBand(lowHz, highHz);
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

    _activityValue(name, raw, transientWeight = 0.5) {
      this.activityPeaks[name] = Math.max(raw, this.activityPeaks[name] * 0.994, 1e-6);
      const normalized = Math.min(1, raw / this.activityPeaks[name]);
      const rise = Math.max(0, normalized - this.previousActivity[name]);
      this.previousActivity[name] = normalized;
      return Math.min(1, normalized * (1 - transientWeight) + rise * 2.2 * transientWeight);
    }

    _musicalActivity() {
      // Heuristics only. These are broad activity channels, not instrument recognition.
      const kickRaw = this._rawBand(45, 115);
      const bassRaw = this._rawBand(55, 260);
      const snareBody = this._rawBand(140, 280);
      const snareCrack = this._rawBand(1200, 4200);
      const cymbalRaw = this._rawBand(5000, 14000);

      return {
        kick: this._activityValue('kick', kickRaw, 0.72),
        bass: this._activityValue('bass', bassRaw, 0.18),
        snare: this._activityValue('snare', snareBody * 0.38 + snareCrack * 0.62, 0.78),
        cymbal: this._activityValue('cymbal', cymbalRaw, 0.58),
      };
    }

    _detectBeat() {
      const binHz = this.audioContext.sampleRate / this.fftSize;
      const lowBin = Math.max(1, Math.floor(45 / binHz));
      const highBin = Math.min(this.frequencyData.length, Math.ceil(220 / binHz));
      const current = new Float32Array(highBin - lowBin);
      let flux = 0;
      for (let i = lowBin; i < highBin; i += 1) {
        const linear = Math.pow(10, this.frequencyData[i] / 20);
        const j = i - lowBin;
        current[j] = linear;
        if (this.previousFluxBins) flux += Math.max(0, linear - this.previousFluxBins[j]);
      }
      this.previousFluxBins = current;

      if (this.fluxHistory.length < 10) {
        this.fluxHistory.push(flux);
        return { beat: false, strength: 0, flux };
      }

      const sorted = [...this.fluxHistory].sort((a,b) => a-b);
      const median = sorted[Math.floor(sorted.length / 2)];
      const deviations = sorted.map(v => Math.abs(v - median)).sort((a,b) => a-b);
      const mad = deviations[Math.floor(deviations.length / 2)] || 1e-6;
      const threshold = median + Math.max(mad * 3.2, median * 0.45, 1e-5);
      const now = performance.now();
      const beat = flux > threshold && now - this.lastBeatAt >= 150;

      this.fluxHistory.push(flux);
      if (this.fluxHistory.length > 30) this.fluxHistory.shift();
      if (!beat) return { beat: false, strength: 0, flux };
      this.lastBeatAt = now;
      return { beat: true, strength: Math.min(1, (flux - threshold) / Math.max(threshold, 1e-5)), flux };
    }

    _tick() {
      if (!this.running || !this.analyser) return;
      this.analyser.getFloatFrequencyData(this.frequencyData);
      this.analyser.getFloatTimeDomainData(this.timeData);
      let sumSquares = 0, peak = 0;
      for (const sample of this.timeData) { sumSquares += sample * sample; peak = Math.max(peak, Math.abs(sample)); }
      const rms = Math.sqrt(sumSquares / this.timeData.length);
      const bass = this._normalizedBand(20, 250, 'bass');
      const mid = this._normalizedBand(250, 4000, 'mid');
      const treble = this._normalizedBand(4000, 16000, 'treble');
      const beatResult = this._detectBeat();
      const activity = this._musicalActivity();
      this.onState?.({
        level: Math.min(1, rms * 4), peak: Math.min(1, peak), bass, mid, treble,
        beat: beatResult.beat, beatStrength: beatResult.strength, beatFlux: beatResult.flux,
        activity, spectrum: this._spectrum(), sampleRateHz: this.audioContext.sampleRate, fftSize: this.fftSize,
      });
      this.animationFrame = requestAnimationFrame(() => this._tick());
    }
  }

  root.MicrophoneMusicAnalyzer = MicrophoneMusicAnalyzer;
})();
