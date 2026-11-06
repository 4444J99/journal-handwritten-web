/* Private T09 pilot controller. No reader wiring or automatic playback. */
(function (root) {
  'use strict';
  class T09Playback {
    constructor(options = {}) {
      this.createContext = options.createContext || (() => new (root.AudioContext || root.webkitAudioContext)());
      this.readBytes = options.readBytes || (async (url, signal) => {
        const response = await fetch(url, { signal, cache: 'no-store' });
        if (!response.ok) throw new Error(`Audio request failed (${response.status}).`);
        if (Number(response.headers.get('Content-Length')) > 40 * 1024 * 1024) throw new Error('Audio exceeds the 40 MiB pilot limit.');
        return response.arrayBuffer();
      });
      this.onChange = options.onChange || (() => {});
      this.context = null;
      this.source = null;
      this.buffer = null;
      this.sample = null;
      this.generation = 0;
      this.abort = null;
      this.state = 'off';
      this.reason = 'Sound is off. Load a sample, then press Start.';
      this.error = null;
      this.volume = 0.25;
      this.destroyed = false;
      this.document = options.document === undefined ? root.document : options.document;
      this.pageTarget = options.pageTarget === undefined ? root : options.pageTarget;
      this.hidden = () => { if (this.document?.hidden) this.stop('Page hidden; press Start again when ready.'); };
      this.pagehide = () => this.stop('Page left; playback stopped.');
      this.document?.addEventListener('visibilitychange', this.hidden);
      this.pageTarget?.addEventListener?.('pagehide', this.pagehide);
    }
    snapshot() {
      return { state: this.state, reason: this.reason, error: this.error, sampleId: this.sample?.id || null, loaded: !!this.buffer, generation: this.generation };
    }
    notify() { this.onChange(this.snapshot()); }
    ensureContext() {
      if (!this.context) {
        this.context = this.createContext();
        this.context.onstatechange = () => {
          if (['starting', 'playing'].includes(this.state) && this.context.state !== 'running') {
            this.stop(`Audio context ${this.context.state}; press Start again when ready.`);
          }
        };
      }
      return this.context;
    }
    stop(reason = 'Stopped. Press Start to listen again.') {
      this.generation += 1;
      this.abort?.abort();
      this.abort = null;
      const source = this.source;
      this.source = null;
      if (source) {
        source.onended = null;
        try { source.stop(); } catch (_) { /* Already ended. */ }
        source.disconnect();
      }
      this.gain?.disconnect();
      this.gain = null;
      this.state = this.buffer ? 'ready' : 'off';
      this.reason = reason;
      this.error = null;
      this.notify();
    }
    invalidate(reason = 'Source context changed; load a sample again.') {
      this.stop(reason);
      this.buffer = null;
      this.sample = null;
      this.state = 'off';
      this.notify();
    }
    async load(sample, source) {
      if (this.destroyed) return false;
      this.invalidate('Loading the selected sample; sound remains off.');
      const generation = this.generation;
      this.sample = sample;
      this.state = 'loading';
      this.abort = new AbortController();
      this.notify();
      try {
        const bytes = await this.readBytes(source, this.abort.signal, sample);
        if (generation !== this.generation) return false;
        if (!(bytes instanceof ArrayBuffer) || bytes.byteLength > 40 * 1024 * 1024) throw new Error('Audio is invalid or exceeds the 40 MiB pilot limit.');
        const buffer = await this.ensureContext().decodeAudioData(bytes);
        if (generation !== this.generation) return false;
        if (buffer.length * buffer.numberOfChannels * 4 > 40 * 1024 * 1024) throw new Error('Decoded audio exceeds the 40 MiB pilot limit.');
        this.buffer = buffer;
        this.abort = null;
        this.state = 'ready';
        this.reason = 'Loaded. Sound is off until you press Start.';
        this.notify();
        return true;
      } catch (error) {
        if (generation !== this.generation) return false;
        this.state = 'error';
        this.error = error.message || String(error);
        this.reason = 'Could not load the sample.';
        this.notify();
        return false;
      }
    }
    async start() {
      if (this.destroyed || !this.buffer || this.document?.hidden) return false;
      this.stop('Starting after your playback request.');
      const generation = this.generation;
      this.state = 'starting';
      this.notify();
      try {
        const context = this.ensureContext();
        await context.resume();
        if (generation !== this.generation || this.document?.hidden) return false;
        if (context.state !== 'running') throw new Error(`Audio context is ${context.state}; playback was not started.`);
        this.gain = context.createGain();
        if (this.gain.gain.setValueAtTime && this.gain.gain.linearRampToValueAtTime) {
          this.gain.gain.setValueAtTime(0, context.currentTime);
          this.gain.gain.linearRampToValueAtTime(this.volume, context.currentTime + 0.008);
        } else this.gain.gain.value = this.volume;
        this.gain.connect(context.destination);
        this.source = context.createBufferSource();
        this.source.buffer = this.buffer;
        this.source.loop = false;
        this.source.connect(this.gain);
        this.source.onended = () => { if (generation === this.generation) this.stop('Sample finished. Press Start to listen again.'); };
        this.source.start();
        this.state = 'playing';
        this.reason = 'Playing one sample. Stop is always available.';
        this.notify();
        return true;
      } catch (error) {
        if (generation !== this.generation) return false;
        this.stop('Playback could not start.');
        this.state = 'error';
        this.error = error.message || String(error);
        this.notify();
        return false;
      }
    }
    setVolume(value) {
      this.volume = Math.max(0, Math.min(1, Number(value) || 0));
      if (this.gain) {
        if (this.gain.gain.setTargetAtTime) this.gain.gain.setTargetAtTime(this.volume, this.context.currentTime, 0.008);
        else this.gain.gain.value = this.volume;
      }
    }
    destroy() {
      this.invalidate('Controller closed.');
      this.destroyed = true;
      this.document?.removeEventListener('visibilitychange', this.hidden);
      this.pageTarget?.removeEventListener?.('pagehide', this.pagehide);
      if (this.context) {
        this.context.onstatechange = null;
        this.context.close()?.catch?.(() => {});
      }
    }
  }
  root.T09Playback = T09Playback;
})(globalThis);
