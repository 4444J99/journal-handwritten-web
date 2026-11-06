"""Bounded, deterministic calibration DSP; no voice model or external samples.

Spectral stretching retains frequency-bin locations and uses seeded phase
randomization. It is an intentionally small texture experiment, not TD-PSOLA,
forced alignment, or an implementation of the Paulstretch application.
"""
from __future__ import annotations
import math
import numpy as np

MAX_PREVIEW_SECONDS = 6.0


def finite_audio(samples):
    x = np.asarray(samples, dtype=np.float64)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
        raise ValueError("Audio must be a nonempty finite mono array")
    return x


def number(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return float(value)


def integer(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


def finish(samples, peak=0.5, fade_frames=240):
    """One symmetric edge fade and peak ceiling; scale never boosts a source."""
    x = finite_audio(samples).copy()
    n = min(integer(fade_frames, "fade_frames", 0, 48000), len(x) // 2)
    if n:
        edge = np.linspace(0.0, 1.0, n, endpoint=True)
        x[:n] *= edge
        x[-n:] *= edge[::-1]
    magnitude = float(np.max(np.abs(x)))
    gain = min(1.0, peak / magnitude) if magnitude else 1.0
    return x * gain, {"edge_fade_frames": n, "peak_ceiling": peak, "gain": gain}


def concatenate(parts, crossfade_frames=240):
    """Equal-power overlaps. Timings describe actual overlapping output spans."""
    if not parts:
        raise ValueError("No concatenation units")
    integer(crossfade_frames, "crossfade_frames", 0, 2400)
    result = finite_audio(parts[0]).copy()
    spans = [{"start_frame": 0, "end_frame": len(result), "overlap_before_frames": 0}]
    for part in parts[1:]:
        x = finite_audio(part)
        overlap = min(crossfade_frames, len(result) // 2, len(x) // 2)
        start = len(result) - overlap
        if overlap:
            angle = np.linspace(0.0, math.pi / 2, overlap)
            mix = result[-overlap:] * np.cos(angle) + x[:overlap] * np.sin(angle)
            result = np.concatenate((result[:-overlap], mix, x[overlap:]))
        else:
            result = np.concatenate((result, x))
        spans.append({"start_frame": start, "end_frame": len(result), "overlap_before_frames": overlap})
    return result, spans


def spectral_texture(samples, sample_rate, *, factor=10.0, window_seconds=0.25,
                     preview_seconds=6.0, seed=9, freeze=False):
    """Seeded magnitude-spectrum overlap/add, bounded by the preview duration.

    No spectrum bin is moved: pitch frequencies are retained, while random
    phases deliberately smear time structure. Freeze fixes the analysis center.
    Short signals are reflect-padded for the requested window. The full implied
    stretch duration is recorded, but only the preview is computed.
    """
    x = finite_audio(samples)
    factor = number(factor, "factor", 1, 200)
    window_seconds = number(window_seconds, "window_seconds", 0.02, 1.0)
    preview_seconds = number(preview_seconds, "preview_seconds", 0.02, MAX_PREVIEW_SECONDS)
    integer(seed, "seed", 0, 2**32 - 1)
    if sample_rate != 48000:
        raise ValueError("Only 48000 Hz is supported")
    n_fft = max(256, round(window_seconds * sample_rate))
    n_fft += n_fft % 2
    hop = n_fft // 4
    implied_frames = round(len(x) * factor) if not freeze else round(preview_seconds * sample_rate)
    count = min(implied_frames, round(preview_seconds * sample_rate))
    count = max(1, count)
    window = np.hanning(n_fft)
    padded = np.pad(x, (n_fft, n_fft), mode="reflect" if len(x) > 1 else "edge")
    result = np.zeros(count + 2 * n_fft, dtype=np.float64)
    weights = np.zeros_like(result)
    rng = np.random.default_rng(seed)
    for out_start in range(-n_fft, count, hop):
        position = len(x) / 2 if freeze else max(0, out_start + n_fft / 2) / factor
        center = min(len(x) - 1, round(position)) + n_fft
        source_start = center - n_fft // 2
        frame = padded[source_start:source_start + n_fft]
        spectrum = np.fft.rfft(frame * window)
        phases = rng.uniform(-math.pi, math.pi, len(spectrum))
        phases[0] = 0
        phases[-1] = 0
        synthesized = np.fft.irfft(np.abs(spectrum) * np.exp(1j * phases), n=n_fft)
        offset = out_start + n_fft
        result[offset:offset + n_fft] += synthesized * window
        weights[offset:offset + n_fft] += window * window
    result = result[n_fft:n_fft + count]
    weights = weights[n_fft:n_fft + count]
    result /= np.maximum(weights, 1e-8)
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite spectral output")
    return result, {
        "algorithm": "seeded-magnitude-spectrum-overlap-add-v1",
        "factor": factor, "requested_window_seconds": window_seconds,
        "actual_window_frames": n_fft, "actual_window_seconds": n_fft / sample_rate,
        "hop_frames": hop, "seed": seed, "freeze": freeze,
        "padding": "reflect" if len(x) > 1 else "edge",
        "window_exceeds_source": n_fft > len(x),
        "implied_full_duration_seconds": implied_frames / sample_rate,
        "preview_cap_seconds": preview_seconds,
        "preview_truncated": count < implied_frames,
        "pitch_method": "frequency bins retained; no pitch transposition",
    }


def octave(samples, sample_rate, *, semitones=-12, preview_seconds=6.0):
    """Rate transposition with linear interpolation; changes pitch AND duration."""
    x = finite_audio(samples)
    if isinstance(semitones, bool) or semitones not in (-12, 12):
        raise ValueError("semitones must be -12 or 12")
    preview_seconds = number(preview_seconds, "preview_seconds", 0.02, MAX_PREVIEW_SECONDS)
    rate = 2 ** (semitones / 12)
    implied_frames = math.ceil(len(x) / rate)
    count = min(implied_frames, round(sample_rate * preview_seconds))
    positions = np.arange(count, dtype=np.float64) * rate
    y = np.interp(positions, np.arange(len(x), dtype=np.float64), x)
    return y, {"algorithm": "linear-rate-transposition-v1", "semitones": semitones,
               "playback_rate": rate, "duration_preserved": False,
               "implied_full_duration_seconds": implied_frames / sample_rate,
               "preview_cap_seconds": preview_seconds, "preview_truncated": count < implied_frames,
               "limitation": "No antialias filter; audition only, especially octave-up"}


def voice_reverb(samples, sample_rate, *, wet=0.25, decay=0.6, seed=9,
                 preview_seconds=6.0):
    """Dry source plus bounded seeded echoes of that source; no external IR."""
    x = finite_audio(samples)
    wet = number(wet, "wet", 0, 0.4)
    decay = number(decay, "decay", 0.1, 0.8)
    preview_seconds = number(preview_seconds, "preview_seconds", 0.02, MAX_PREVIEW_SECONDS)
    integer(seed, "seed", 0, 2**32 - 1)
    rng = np.random.default_rng(seed)
    delays = sorted(int(v) for v in rng.integers(round(sample_rate * 0.035), round(sample_rate * 0.4), 12))
    implied_frames = len(x) + max(delays)
    count = min(implied_frames, round(sample_rate * preview_seconds))
    y = np.zeros(count, dtype=np.float64)
    y[:min(count, len(x))] += x[:count] * (1 - wet)
    taps = []
    for i, delay in enumerate(delays):
        gain = wet * (decay ** i) / 2
        available = max(0, min(len(x), count - delay))
        if available:
            y[delay:delay + available] += x[:available] * gain
        taps.append({"delay_frames": delay, "gain": gain})
    return y, {"algorithm": "seeded-source-only-multitap-v1", "wet": wet,
               "decay": decay, "seed": seed, "taps": taps, "external_impulse_response": False,
               "implied_full_duration_seconds": implied_frames / sample_rate,
               "preview_cap_seconds": preview_seconds, "preview_truncated": count < implied_frames}
