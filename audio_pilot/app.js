(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const pretty = value => JSON.stringify(value, null, 2);
  let receipt = null, packet = null, packetHash = null, promptIndex = 0, localSamples = new Map(), fileMode = false;
  const inputGenerations = [0, 0];
  const progress = [], feedback = [];
  function status(message, error = false) {
    $('data-status').textContent = message;
    $('data-status').className = error ? 'error' : '';
  }
  async function bytes(source, signal, sample) {
    let data;
    if (source instanceof File) data = await source.arrayBuffer();
    else {
      const response = await fetch(source, { signal, cache: 'no-store' });
      if (!response.ok) throw new Error(`Rendered sample unavailable (${response.status}).`);
      if (Number(response.headers.get('Content-Length')) > 40 * 1024 * 1024) throw new Error('Sample exceeds the 40 MiB pilot limit.');
      data = await response.arrayBuffer();
    }
    if (data.byteLength > 40 * 1024 * 1024) throw new Error('Sample exceeds the 40 MiB pilot limit.');
    if (!/^[a-f0-9]{64}$/i.test(sample.sha256 || '')) throw new Error('Receipt has no valid sample SHA-256 identity.');
    if (!globalThis.crypto?.subtle) throw new Error('SHA-256 verification unavailable. Open this page through the loopback server.');
    const digest = await crypto.subtle.digest('SHA-256', data);
    const hash = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
    if (hash !== sample.sha256.toLowerCase()) throw new Error('Sample SHA-256 differs from its receipt. Load the matching render.');
    return data;
  }
  const player = new T09Playback({ readBytes: bytes, onChange: state => {
    $('playback-state').textContent = `${state.state.toUpperCase()} · ${state.reason}${state.error ? ` ${state.error}` : ''}`;
    $('playback-state').className = state.error ? 'error' : '';
    $('start-playback').disabled = !state.loaded || ['starting', 'playing', 'loading'].includes(state.state);
  }});
  window.t09Player = player;
  function selected() { return receipt?.samples.find(sample => sample.id === $('sample-select').value); }
  function showSample() {
    player.invalidate('Sample context changed. Load the selected sample before starting.');
    const sample = selected();
    $('sample-details').textContent = sample ? pretty(sample) : 'No sample selected.';
    $('load-sample').disabled = !sample;
    $('export-feedback').disabled = !sample;
  }
  function showReceipt(value, fromFiles) {
    if (!value || value.schema_version !== 1 || typeof value.fixture !== 'boolean' || !Array.isArray(value.samples)) throw new Error('Expected a version 1 pilot receipt with explicit fixture status and a samples array.');
    if (typeof value.session_id !== 'string' || !value.session_id.trim() || !/^[a-f0-9]{64}$/.test(value.manifest_sha256 || '')) throw new Error('Receipt must identify its session and a lowercase SHA-256 manifest hash before loading or exporting samples.');
    const ids = new Set();
    value.samples.forEach(sample => {
      if (!sample.id || ids.has(sample.id) || !/^samples\/[A-Za-z0-9][A-Za-z0-9_.:-]*\.wav$/.test(sample.path || '') || !/^[a-f0-9]{64}$/i.test(sample.sha256 || '') || typeof sample.fixture !== 'boolean') throw new Error('Receipt contains an invalid, duplicate, unidentified, or unsafe sample.');
      ids.add(sample.id);
    });
    receipt = value;
    fileMode = fromFiles;
    $('fixture-status').textContent = value.fixture || value.samples.some(sample => sample.fixture)
      ? 'FIXTURE AUDIO · Synthetic calibration signals. No author voice or listening acceptance is demonstrated.'
      : 'SUPPLIED-RECORDING PILOT · Check receipt provenance and the author’s listening decision. This is not a finished or released voice bank.';
    $('provenance').textContent = pretty(value);
    $('sample-select').replaceChildren(...value.samples.map(sample => {
      const option = document.createElement('option');
      option.value = sample.id;
      option.textContent = `${sample.label || sample.id}${sample.fixture ? ' [FIXTURE]' : ''}`;
      return option;
    }));
    $('sample-select').disabled = value.samples.length === 0;
    $('diagnostics').replaceChildren();
    ['errors', 'warnings', 'missing_pronunciations'].forEach(key => {
      if (value[key]?.length) {
        const title = document.createElement('h3'), content = document.createElement('pre');
        title.textContent = key.replaceAll('_', ' ');
        content.textContent = pretty(value[key]);
        if (key === 'errors') content.className = 'error';
        $('diagnostics').append(title, content);
      }
    });
    showSample();
  }
  function decisionResolved(id) {
    const decisions = packet?.author_decisions;
    const value = Array.isArray(decisions) ? decisions.find(item => item.id === id) : decisions?.[id];
    if (!value || typeof value !== 'object') return false;
    const choice = Object.hasOwn(value, 'choice') ? value.choice : value.value;
    const author = Object.hasOwn(value, 'author') ? value.author : value.authority;
    const source = Object.hasOwn(value, 'source') ? value.source : value.source_ref;
    return [choice, author, source].every(field => typeof field === 'string' && field.trim());
  }
  function showPrompt() {
    const prompt = packet?.prompts[promptIndex];
    const card = $('prompt-card');
    card.replaceChildren();
    if (!prompt) { card.textContent = 'No prompts available.'; return; }
    const position = document.createElement('p'), title = document.createElement('h3'), instruction = document.createElement('p'), target = document.createElement('p'), gate = document.createElement('p');
    position.textContent = `${promptIndex + 1} / ${packet.prompts.length} · ${prompt.id} · ${prompt.section || 'Technical calibration'} · take ${prompt.take_number || 1}`;
    title.textContent = prompt.label || prompt.id;
    instruction.textContent = prompt.instruction || '';
    target.textContent = typeof prompt.target === 'string' ? prompt.target : pretty(prompt.target);
    target.className = 'target';
    const requirements = (prompt.requires_decisions || []).map(item => typeof item === 'string' ? item : item.id);
    const unresolved = requirements.filter(id => !decisionResolved(id));
    gate.className = 'gate';
    gate.textContent = unresolved.length ? `AUTHOR CHOICES UNSET: ${unresolved.join(', ')}. Rehearse or prepare; resolve these choices in the author decision sheet before recording this prompt.` : 'Technical preparation prompt. Confirm the session decisions and recorder settings before recording externally.';
    card.append(position, title, instruction, target, gate);
    $('prompt-prev').disabled = promptIndex === 0;
    $('prompt-next').disabled = promptIndex === packet.prompts.length - 1;
    ['prompt-rehearse', 'prompt-pause', 'prompt-repeat', 'export-progress'].forEach(id => $(id).disabled = false);
    $('prompt-log').disabled = unresolved.length > 0 || !packetHash;
    $('take-id').value = '';
    $('take-notes').value = '';
    $('prompt-status').textContent = 'Paused. Use the external recorder; this page captures no audio.';
  }
  function showPacket(value, sourceHash) {
    if (!value || value.schema_version !== 1 || typeof value.packet_id !== 'string' || !value.packet_id.trim() || !Array.isArray(value.prompts) || !value.prompts.length) throw new Error('Expected a version 1 prompt packet with a packet ID and prompts.');
    packet = value;
    packetHash = sourceHash;
    promptIndex = 0;
    $('packet-status').textContent = `${value.packet_id || 'Technical packet'} · ${value.prompts.length} prompts · ${pretty(value.session_minutes || 'See recording request')} minutes proposed. ${typeof value.recording_request === 'string' ? value.recording_request : value.recording_request?.rule || ''}${sourceHash ? '' : ' Packet hash unavailable in this browser; use loopback mode for provenance before recording.'}`;
    $('author-decisions').textContent = pretty(value.author_decisions || { status: 'unset' });
    showPrompt();
  }
  async function parseJSON(bytes) {
    const value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    let sha256 = null;
    if (globalThis.crypto?.subtle) {
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      sha256 = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
    }
    return { value, sha256 };
  }
  async function readJSON(url) {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return parseJSON(await response.arrayBuffer());
  }
  $('load-data').addEventListener('click', async () => {
    const generations = inputGenerations.map((value, index) => ++inputGenerations[index]);
    player.invalidate('Packet reload requested; sound is off.');
    if (location.protocol === 'file:') { status('For direct file mode, select the receipt and prompts using the file inputs.', true); return; }
    $('load-data').disabled = true;
    const results = await Promise.allSettled([readJSON('/receipt.json'), readJSON('/prompts.json')]);
    const messages = [];
    let hadError = false;
    results.forEach((result, index) => {
      if (generations[index] !== inputGenerations[index]) return;
      try {
        if (result.status !== 'fulfilled') throw result.reason;
        if (index === 0) showReceipt(result.value.value, false); else showPacket(result.value.value, result.value.sha256);
        messages.push(index === 0 ? 'Receipt loaded.' : 'Prompts loaded.');
      } catch (error) { hadError = true; messages.push(error.message); }
    });
    if (messages.length) status(messages.join(' '), hadError);
    $('load-data').disabled = false;
  });
  for (const [inputId, handler] of [['receipt-file', data => showReceipt(data.value, true)], ['prompts-file', data => showPacket(data.value, data.sha256)]]) {
    $(inputId).addEventListener('change', async event => {
      const file = event.target.files[0];
      if (!file) return;
      const index = inputId === 'receipt-file' ? 0 : 1;
      const generation = ++inputGenerations[index];
      $('load-data').disabled = false;
      player.invalidate('Local packet changed; sound is off.');
      try {
        const data = await parseJSON(await file.arrayBuffer());
        if (generation !== inputGenerations[index]) return;
        handler(data);
        status(`${file.name} loaded locally.`);
      } catch (error) { if (generation === inputGenerations[index]) status(error.message, true); }
    });
  }
  $('sample-files').addEventListener('change', event => {
    player.invalidate('Rendered files changed; sound is off.');
    localSamples = new Map(Array.from(event.target.files).map(file => [file.name, file]));
    status(`${localSamples.size} local rendered file(s) selected. Only a receipt-listed, SHA-256 verified sample can play.`);
  });
  $('sample-select').addEventListener('change', showSample);
  $('load-sample').addEventListener('click', async () => {
    const sample = selected();
    if (!sample) return;
    const source = fileMode ? localSamples.get(sample.path.split('/').pop()) : `/${sample.path}`;
    if (!source) { player.invalidate('Matching local sample file is missing.'); status(`Select rendered file ${sample.path.split('/').pop()}.`, true); return; }
    await player.load(sample, source);
  });
  $('start-playback').addEventListener('click', () => player.start());
  $('stop-playback').addEventListener('click', () => player.stop());
  $('volume').addEventListener('input', event => player.setVolume(event.target.value));
  function download(name, value) {
    const url = URL.createObjectURL(new Blob([pretty(value) + '\n'], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('export-feedback').addEventListener('click', () => {
    const sample = selected();
    if (!sample) return;
    feedback.push({ recorded_at: new Date().toISOString(), session_id: receipt.session_id, manifest_sha256: receipt.manifest_sha256, fixture: sample.fixture, sample_id: sample.id, sample_sha256: sample.sha256, response: $('feedback-choice').value, notes: $('feedback-notes').value, listening_gain: player.volume });
    download('t09-listening-feedback.json', { schema_version: 1, kind: 'pilot-listening-feedback', is_release_approval: false, is_acquisition_approval: false, is_sound_direction_acceptance: false, user_entered_notes_unverified: true, entries: feedback });
  });
  $('prompt-next').addEventListener('click', () => { if (promptIndex < packet.prompts.length - 1) { promptIndex += 1; showPrompt(); } });
  $('prompt-prev').addEventListener('click', () => { if (promptIndex > 0) { promptIndex -= 1; showPrompt(); } });
  $('prompt-rehearse').addEventListener('click', () => { $('prompt-status').textContent = 'Rehearsal. Read at your own pace; no timer, microphone, or recording is active.'; });
  $('prompt-pause').addEventListener('click', () => { $('prompt-status').textContent = 'Paused. Stop or pause your external recorder separately.'; });
  function logTake(kind) {
    const prompt = packet.prompts[promptIndex];
    if (kind === 'external-take' && !$('take-id').value.trim()) { $('prompt-status').textContent = 'Enter the external recorder’s take ID before logging.'; return; }
    progress.push({ kind, packet_id: packet.packet_id, prompts_json_sha256: packetHash, author_decisions_snapshot: structuredClone(packet.author_decisions || {}), prompt_snapshot: structuredClone(prompt), prompt_id: prompt.id, planned_take_number: prompt.take_number, external_take_id: $('take-id').value.trim(), notes: $('take-notes').value, recorded_at: new Date().toISOString(), required_decisions: prompt.requires_decisions || [] });
    $('prompt-status').textContent = `${kind === 'external-take' ? 'External take reference' : 'Repeat request'} logged locally. Export progress before closing.`;
  }
  $('prompt-log').addEventListener('click', () => logTake('external-take'));
  $('prompt-repeat').addEventListener('click', () => logTake('repeat-needed'));
  $('export-progress').addEventListener('click', () => download('t09-recording-progress.json', { schema_version: 1, kind: 'recording-prompt-progress', entry_identity: 'Each entry retains its original packet, prompt and decision snapshot; entries may span loaded packets.', current_packet_id: packet.packet_id, current_prompts_json_sha256: packetHash, current_prompt_id: packet.prompts[promptIndex].id, no_browser_recording: true, user_entered_notes_unverified: true, entries: progress }));
})();
