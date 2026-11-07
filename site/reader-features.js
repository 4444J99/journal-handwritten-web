import {assertSourceBinding, assertPackageReference, sameOriginAsset, loadRealizationPackage, loadRegionPackage} from './reader-packages.js';

/**
 * Shared lifetime for explicitly invoked reader features. This module does not
 * fetch private data, choose release policy, or persist author decisions.
 */
export function createReaderLifecycle({host, timeoutMs = 0, onClose = () => {}} = {}) {
  if (!host?.ownerDocument) throw new TypeError('A dedicated reader host is required.');
  const doc = host.ownerDocument, win = doc.defaultView;
  let active = false, destroyed = false, trigger = null, controller = null, cleanups = [], generation = 0;
  const failures = [];
  function close(reason = 'hide', restoreFocus = true) {
    if (!active) return;
    active = false; generation++;
    controller.abort(reason); controller = null;
    for (const cleanup of cleanups.splice(0).reverse()) {
      try { cleanup(); } catch (error) { failures.push(error); }
    }
    host.replaceChildren(); host.hidden = true; host.setAttribute('aria-hidden', 'true');
    const previous = trigger; trigger = null;
    previous?.setAttribute?.('aria-expanded', 'false');
    try { onClose(reason); } catch (error) { failures.push(error); }
    if (restoreFocus && previous?.isConnected) previous.focus?.({preventScroll:true});
  }
  function open({trigger: control = doc.activeElement, render, timeout = timeoutMs} = {}) {
    if (destroyed) throw new Error('Reader lifecycle has been destroyed.');
    if (typeof render !== 'function') throw new TypeError('A feature renderer is required.');
    close('replace', false);
    active = true; controller = new AbortController(); const current = ++generation;
    trigger = control === doc.body ? null : control;
    trigger?.setAttribute?.('aria-expanded', 'true');
    host.replaceChildren(); host.hidden = false; host.removeAttribute('aria-hidden');
    const own = cleanup => {
      if (typeof cleanup !== 'function') throw new TypeError('Cleanup must be a function.');
      if (!active || generation !== current) cleanup(); else cleanups.push(cleanup);
      return cleanup;
    };
    const scope = {
      host, signal:controller.signal,
      current:() => active && generation === current && !destroyed,
      own,
      listen(target, type, listener, options) {
        target.addEventListener(type, listener, options);
        own(() => target.removeEventListener(type, listener, options));
      },
      delay(callback, ms) {
        const id = win.setTimeout(() => { if (scope.current()) callback(); }, ms);
        own(() => win.clearTimeout(id)); return id;
      },
      frame(callback) {
        const id = win.requestAnimationFrame(time => { if (scope.current()) callback(time); });
        own(() => win.cancelAnimationFrame(id)); return id;
      },
      close:(reason = 'hide') => { if (scope.current()) close(reason); },
    };
    try {
      const cleanup = render(scope);
      if (typeof cleanup === 'function') own(cleanup);
      if (timeout > 0) scope.delay(() => close('timeout'), timeout);
      const focusTarget = host.querySelector('[autofocus], button, [tabindex]') || host;
      if (focusTarget === host) host.tabIndex = -1;
      focusTarget.focus?.({preventScroll:true});
      return scope;
    } catch (error) { close('error'); throw error; }
  }
  const outside = event => { if (active && !host.contains(event.target) && !trigger?.contains?.(event.target)) close('outside'); };
  const escape = event => { if (active && event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); close('escape'); } };
  const visibility = () => { if (doc.hidden) close('hidden', false); };
  const source = () => close('source-switch', false);
  const pagehide = () => close('pagehide', false);
  doc.addEventListener('pointerdown', outside, true);
  doc.addEventListener('keydown', escape, true);
  doc.addEventListener('visibilitychange', visibility);
  doc.addEventListener('reader:sourcechange', source);
  win?.addEventListener('pagehide', pagehide);
  host.hidden = true; host.setAttribute('aria-hidden', 'true');
  return {
    open, close, switchSource:source,
    get isOpen() { return active; },
    get cleanupErrors() { return failures.slice(); },
    destroy() {
      if (destroyed) return;
      close('destroy'); destroyed = true;
      doc.removeEventListener('pointerdown', outside, true);
      doc.removeEventListener('keydown', escape, true);
      doc.removeEventListener('visibilitychange', visibility);
      doc.removeEventListener('reader:sourcechange', source);
      win?.removeEventListener('pagehide', pagehide);
    },
  };
}

function node(doc, tag, text) { const el = doc.createElement(tag); if (text !== undefined) el.textContent = text; return el; }
function localAsset(value, doc) {
  return sameOriginAsset(value, doc);
}
function sourceKey(source) { return [source?.pieceId, source?.versionId, source?.sourceFingerprint].join('\n'); }
function assertSource(source) {
  assertSourceBinding(source);
}
async function verifiedAsset(descriptor, url, scope, doc) {
  if (!descriptor.sha256) return url;
  const response = await doc.defaultView.fetch(url, {signal:scope.signal, cache:'no-store', redirect:'error'});
  if (!response.ok) throw new Error('Preview asset could not be loaded.');
  const bytes = await response.arrayBuffer();
  const digest = [...new Uint8Array(await doc.defaultView.crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2,'0')).join('');
  if ('sha256:' + digest !== descriptor.sha256) throw new Error('Preview asset digest does not match.');
  if (!scope.current()) throw new DOMException('Preview closed.', 'AbortError');
  const objectURL = URL.createObjectURL(new Blob([bytes], {type:response.headers.get('content-type') || 'application/octet-stream'}));
  scope.own(() => URL.revokeObjectURL(objectURL)); return objectURL;
}

/** Private integration surface; callers supply already-projected records. */
export function mountPrivateFeaturePreview(host, {enabled = false, source, notes = [], audio = null, regions = null, realization = null, renderNotes = null, timeoutMs = 0, getCurrentSource = null, getCurrentPolicy = null, getStoredArtifact = null, getCurrentReviewGeometry = null, getCurrentReaderGeometry = null, getCurrentRegionMedia = null} = {}) {
  if (!enabled) return {enabled:false, destroy(){}, switchSource(){}};
  assertSource(source);
  source = {...source};
  audio = audio && {...audio, source:{...audio.source}};
  regions = regions && {...regions, source:{...regions.source}, package:regions.package && {...regions.package}, sourceAnchor:regions.sourceAnchor && {...regions.sourceAnchor, box:regions.sourceAnchor.box && [...regions.sourceAnchor.box]}};
  realization = realization && {...realization, source:{...realization.source}, package:realization.package && {...realization.package}};
  const doc = host.ownerDocument;
  for (const [kind, descriptor] of Object.entries({audio, regions, realization})) {
    if (!descriptor) continue;
    assertSource(descriptor.source);
    if (sourceKey(descriptor.source) !== sourceKey(source)) throw new Error(kind + ' preview belongs to a different source version.');
    if (descriptor.sha256 !== undefined && (typeof descriptor.sha256 !== 'string' || !/^sha256:[a-f0-9]{64}$/.test(descriptor.sha256))) throw new Error(kind + ' preview has an invalid asset digest.');
  }
  if (realization) {
    if (!realization.package || realization.url !== undefined || realization.sha256 !== undefined) throw new Error('Realizations require a verified package, not a raw HTML URL.');
    assertPackageReference(realization.package, doc);
    if (typeof getStoredArtifact !== 'function' || typeof getCurrentSource !== 'function' || typeof getCurrentPolicy !== 'function') throw new Error('Realization packages require current stored artifact, source and policy providers.');
  }
  const audioURL = audio && localAsset(audio.url, doc);
  const box = regions?.sourceAnchor?.box;
  const regionAvailable = regions?.sourceAnchor?.status === 'available' && Array.isArray(box) && box.length === 4 && box.every(Number.isFinite) && box[0] >= 0 && box[1] >= 0 && box[2] <= 1 && box[3] <= 1 && box[2] > box[0] && box[3] > box[1];
  if (regions?.package) {
    assertPackageReference(regions.package,doc);
    if (regions.url !== undefined || regions.sha256 !== undefined || typeof getCurrentSource !== 'function' || typeof getCurrentPolicy !== 'function' || typeof getCurrentRegionMedia !== 'function' || typeof getCurrentReviewGeometry !== 'function' && typeof getCurrentReaderGeometry !== 'function') throw new Error('Region packages require current source, policy, geometry and media providers.');
  } else if (regionAvailable) throw new Error('Available source regions require a verified T08 package.');
  const controls = node(doc, 'nav'); controls.setAttribute('aria-label', 'Private feature preview');
  const panel = node(doc, 'section'); panel.setAttribute('aria-label', 'Private feature preview'); panel.setAttribute('role', 'region');
  host.replaceChildren(controls, panel);
  const lifecycle = createReaderLifecycle({host:panel, timeoutMs});
  const sourceId = sourceKey(source);
  const buttons = new Map();
  function add(label, render) {
    const button = node(doc, 'button', label); button.type = 'button'; button.setAttribute('aria-expanded', 'false');
    button.addEventListener('click', () => lifecycle.open({trigger:button, render:scope => {
      const heading = node(doc, 'h2', label), close = node(doc, 'button', 'Close preview'); close.type = 'button';
      scope.listen(close, 'click', () => scope.close());
      panel.append(heading, node(doc, 'p', 'Private technical preview · placement is not an author decision'), close);
      render(scope);
    }}));
    controls.append(button); buttons.set(label, button);
  }
  if (notes.length && typeof renderNotes === 'function') add('Notes', scope => {
    const target = node(doc, 'div'); panel.append(target);
    const adapter = renderNotes(target, {pieceId:source.pieceId, versionId:source.versionId, records:notes});
    scope.own(() => adapter.destroy()); adapter.reveal();
  });
  if (audio) add('Audio', scope => {
    const media = node(doc, 'audio'); media.controls = true; media.preload = 'none'; media.autoplay = false;
    const progress = node(doc, 'p', audio.sha256 ? 'Verifying audio bytes…' : ''); panel.append(progress);
    verifiedAsset(audio, audioURL, scope, doc).then(url => {
      if (!scope.current()) return; media.src = url; panel.append(media); progress.remove();
    }).catch(error => { if (scope.current()) progress.textContent = error.message; });
    if (audio.label) panel.append(node(doc, 'p', String(audio.label)));
    scope.own(() => { media.pause(); media.removeAttribute('src'); media.load(); });
  });
  if (regions) add('Source regions', scope => {
    if (regions.package) {
      const progress = node(doc,'p','Verifying the selected source-region package…'); progress.setAttribute('role','status'); panel.append(progress);
      loadRegionPackage({descriptor:regions,source,scope,doc,getCurrentSource,getCurrentPolicy,getCurrentReviewGeometry,getCurrentReaderGeometry,getCurrentRegionMedia}).then(result => {
        result.assertCurrent();
        if (result.manifest.sourceAnchor.status !== 'available') { progress.textContent = 'Source line geometry is unavailable. No region has been substituted.'; return; }
        const image = node(doc,'img'); image.alt = 'Verified full source image'; image.style.maxWidth = '100%';
        const url = doc.defaultView.URL.createObjectURL(new Blob([result.bytes],{type:'image/jpeg'}));
        scope.own(() => { image.removeAttribute('src'); image.remove(); doc.defaultView.URL.revokeObjectURL(url); });
        result.assertCurrent(); image.src = url; panel.append(image);
        progress.textContent = 'Verified full source image · original region geometry retained; no crop is applied here.';
      }).catch(error => { if (scope.current()) progress.textContent = error.message; });
      return;
    }
    // Derived atoms and inferred polygons are not author-confirmed anchors.
    if (!regionAvailable) { panel.append(node(doc, 'p', 'Source line geometry is unavailable. No region has been substituted.')); return; }
  });
  if (realization) add('Realization', scope => {
    panel.append(node(doc, 'p', realization.label || 'Saved realization'));
    const start = node(doc, 'button', 'Start realization'); start.type = 'button'; panel.append(start);
    scope.listen(start, 'click', () => {
      if (start.disabled) return;
      start.disabled = true;
      const progress = node(doc, 'p', 'Verifying the stored realization package…'); progress.setAttribute('role','status'); panel.append(progress);
      loadRealizationPackage({descriptor:realization,source,scope,doc,getCurrentSource,getCurrentPolicy,getStoredArtifact}).then(result => {
        result.assertCurrent();
        const frame = node(doc, 'iframe'); frame.title = realization.label || 'Private realization';
        // No child scripts are permitted. Same-origin document access is used
        // only for parent-owned Escape handling after the fixed static template
        // has passed byte, dependency and markup validation.
        frame.setAttribute('sandbox', 'allow-same-origin'); frame.setAttribute('allow', 'autoplay \'none\''); frame.referrerPolicy = 'no-referrer';
        frame.style.width = '100%'; frame.style.height = '70vh';
        scope.listen(frame,'load',() => {
          if (!scope.current() || !frame.contentDocument) return;
          scope.listen(frame.contentDocument,'keydown',event => {
            if (event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); scope.close('escape'); }
          },true);
        });
        frame.srcdoc = result.html;
        scope.own(() => { frame.removeAttribute('srcdoc'); frame.removeAttribute('src'); frame.remove(); });
        panel.append(frame); progress.textContent = 'Verified private package · ' + result.rendering.lineCount + ' logical lines';
      }).catch(error => { if (scope.current()) progress.textContent = error.message; });
    });
  });
  const invalidate = () => { lifecycle.switchSource(); for (const button of buttons.values()) button.disabled = true; };
  doc.addEventListener('reader:sourcechange', invalidate);
  return {
    enabled:true, lifecycle, buttons,
    switchSource(next) {
      if (sourceKey(next) !== sourceId) invalidate();
    },
    destroy() { doc.removeEventListener('reader:sourcechange', invalidate); lifecycle.destroy(); host.replaceChildren(); },
  };
}
