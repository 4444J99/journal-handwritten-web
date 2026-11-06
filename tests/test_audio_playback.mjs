import test from 'node:test';
import assert from 'node:assert/strict';
import '../audio_pilot/playback.js';

const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
const tick = () => new Promise(resolve => setImmediate(resolve));
class Surface extends EventTarget { hidden = false; }
class FakeContext {
  state = 'suspended'; currentTime = 0; sources = []; destination = {};
  async decodeAudioData() { return { length: 48000, numberOfChannels: 1 }; }
  async resume() { this.state = 'running'; }
  async close() { this.state = 'closed'; }
  createGain() { return { gain: { value: 0 }, connect() {}, disconnect() {} }; }
  createBufferSource() {
    const source = { starts: 0, stops: 0, disconnects: 0, start() { this.starts++; }, stop() { this.stops++; }, connect() {}, disconnect() { this.disconnects++; } };
    this.sources.push(source);
    return source;
  }
  interrupt(state = 'interrupted') { this.state = state; this.onstatechange?.(); }
}
function setup(options = {}) {
  const context = new FakeContext(), document = new Surface(), pageTarget = new Surface();
  let reads = 0;
  const player = new globalThis.T09Playback({ createContext: () => context, readBytes: async () => { reads++; return new ArrayBuffer(8); }, document, pageTarget, ...options });
  return { player, context, document, pageTarget, reads: () => reads };
}
const sample = { id: 'fixture-forward' };

test('initially off: no reads, context, source or implicit start', async () => {
  const { player, context, reads } = setup();
  assert.equal(player.snapshot().state, 'off');
  assert.equal(player.context, null);
  assert.equal(reads(), 0);
  assert.equal(await player.start(), false);
  assert.equal(context.sources.length, 0);
});
test('load stays silent; explicit start plays one source once; stop disconnects', async () => {
  const { player, context } = setup();
  assert.equal(await player.load(sample, 'fixture.wav'), true);
  assert.equal(player.snapshot().state, 'ready');
  assert.equal(context.sources.length, 0);
  assert.equal(await player.start(), true);
  assert.equal(context.sources[0].loop, false);
  assert.equal(context.sources[0].starts, 1);
  player.stop();
  assert.equal(context.sources[0].stops, 1);
  assert.equal(context.sources[0].disconnects, 1);
  assert.equal(player.snapshot().state, 'ready');
});
test('stop while a fetch is pending cannot load or start later', async () => {
  const read = deferred();
  const { player, context } = setup({ readBytes: () => read.promise });
  const result = player.load(sample, 'fixture.wav');
  player.stop();
  read.resolve(new ArrayBuffer(8));
  assert.equal(await result, false);
  assert.equal(player.snapshot().loaded, false);
  assert.equal(context.sources.length, 0);
});
test('stop while decode is pending invalidates its result', async () => {
  const { player, context } = setup();
  const decode = deferred();
  context.decodeAudioData = () => decode.promise;
  const result = player.load(sample, 'fixture.wav');
  await tick();
  player.stop();
  decode.resolve({ length: 48000, numberOfChannels: 1 });
  assert.equal(await result, false);
  assert.equal(player.snapshot().state, 'off');
});
test('stop during pending context resume prevents late startup', async () => {
  const { player, context } = setup();
  await player.load(sample, 'fixture.wav');
  const resumed = deferred();
  context.resume = () => resumed.promise;
  const result = player.start();
  player.stop();
  context.state = 'running';
  resumed.resolve();
  assert.equal(await result, false);
  assert.equal(context.sources.length, 0);
});
test('a newer sample supersedes an older pending decode', async () => {
  const { player, context } = setup();
  const decode = deferred();
  context.decodeAudioData = () => decode.promise;
  const first = player.load(sample, 'old.wav');
  await tick();
  context.decodeAudioData = async () => ({ length: 24000, numberOfChannels: 1 });
  assert.equal(await player.load({ id: 'new' }, 'new.wav'), true);
  decode.resolve({ length: 48000, numberOfChannels: 1 });
  assert.equal(await first, false);
  assert.equal(player.snapshot().sampleId, 'new');
  assert.equal(player.buffer.length, 24000);
});
test('repeated starts stop the previous source and never loop', async () => {
  const { player, context } = setup();
  await player.load(sample, 'fixture.wav');
  await player.start();
  await player.start();
  assert.equal(context.sources[0].stops, 1);
  assert.equal(context.sources[1].starts, 1);
  assert.equal(context.sources[1].loop, false);
});
test('hidden and pagehide stop; returning does not resume', async () => {
  const { player, context, document, pageTarget } = setup();
  await player.load(sample, 'fixture.wav');
  await player.start();
  document.hidden = true;
  document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(player.snapshot().state, 'ready');
  assert.equal(await player.start(), false);
  document.hidden = false;
  document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(context.sources.length, 1);
  await player.start();
  pageTarget.dispatchEvent(new Event('pagehide'));
  assert.equal(context.sources[1].stops, 1);
  assert.equal(player.snapshot().state, 'ready');
});
test('audio context interruption stops and cannot auto-resume', async () => {
  const { player, context } = setup();
  await player.load(sample, 'fixture.wav');
  await player.start();
  context.interrupt();
  assert.match(player.snapshot().reason, /interrupted/);
  assert.equal(context.sources[0].stops, 1);
  context.interrupt('running');
  assert.equal(context.sources.length, 1);
  assert.equal(player.snapshot().state, 'ready');
});
test('context identity invalidation clears old sample and buffer', async () => {
  const { player, context } = setup();
  await player.load(sample, 'fixture.wav');
  await player.start();
  player.invalidate('Source version changed');
  assert.equal(player.snapshot().state, 'off');
  assert.equal(player.snapshot().sampleId, null);
  assert.equal(await player.start(), false);
  assert.equal(context.sources[0].stops, 1);
});
test('read and decode failures are visible and silent', async () => {
  const first = setup({ readBytes: async () => { throw new Error('Missing pronunciation diagnostic'); } });
  assert.equal(await first.player.load(sample, 'missing.wav'), false);
  assert.match(first.player.snapshot().error, /Missing pronunciation/);
  const second = setup();
  second.context.decodeAudioData = async () => { throw new Error('Invalid WAV'); };
  assert.equal(await second.player.load(sample, 'bad.wav'), false);
  assert.match(second.player.snapshot().error, /Invalid WAV/);
  assert.equal(second.context.sources.length, 0);
});
test('blocked resume is visible; oversized decoded memory is rejected', async () => {
  const { player, context } = setup();
  await player.load(sample, 'fixture.wav');
  context.resume = async () => { throw new Error('NotAllowedError'); };
  assert.equal(await player.start(), false);
  assert.match(player.snapshot().error, /NotAllowedError/);
  context.decodeAudioData = async () => ({ length: 11 * 1024 * 1024, numberOfChannels: 1 });
  assert.equal(await player.load(sample, 'large.wav'), false);
  assert.match(player.snapshot().error, /40 MiB/);
});
test('destroy cancels and detaches the controller', async () => {
  const { player, context, document } = setup();
  await player.load(sample, 'fixture.wav');
  await player.start();
  player.destroy();
  assert.equal(context.sources[0].stops, 1);
  assert.equal(context.state, 'closed');
  const generation = player.generation;
  document.hidden = true;
  document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(player.generation, generation);
  assert.equal(await player.load(sample, 'fixture.wav'), false);
});
