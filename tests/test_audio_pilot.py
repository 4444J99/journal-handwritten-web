"""T09 regression receipts: synthetic technical fixtures only, never author voice."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

from audio_build import dsp, render


class AudioPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory(prefix="t09-test-fixture-")
        cls.fixture = Path(cls.shared.name) / "session"
        render.fixture(cls.fixture)

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="t09-test-")
        self.base = Path(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(render.PilotError) as raised:
            function(*args, **kwargs)
        self.assertEqual(raised.exception.code, code, raised.exception.record())

    def session_copy(self):
        path = self.base / "session"
        shutil.copytree(self.fixture, path)
        return path, render.json_read(path / "session.json")

    def save_manifest(self, session, manifest):
        (session / "session.json").write_bytes(render.json_bytes(manifest))

    def update_labels(self, session, manifest, transform):
        take = manifest["takes"][0]
        path = session / take["alignment"]["path"]
        labels = render.json_read(path)
        transform(labels)
        path.write_bytes(render.json_bytes(labels))
        take["alignment"]["sha256"] = render.sha256(path)
        self.save_manifest(session, manifest)

    def test_fixture_replay_has_identical_manifest_audio_timings_and_receipt(self):
        second = self.base / "second-session"
        render.fixture(second)
        self.assertEqual(render.sha256(self.fixture / "session.json"), render.sha256(second / "session.json"))
        before = {p.name: render.sha256(p) for p in (self.fixture / "raw").iterdir()}
        for index in (1, 2):
            render.run(self.fixture / "session.json", self.base / f"listen-{index}")
        a, b = self.base / "listen-1", self.base / "listen-2"
        self.assertEqual((a / "SHA256SUMS").read_bytes(), (b / "SHA256SUMS").read_bytes())
        receipt = render.json_read(a / "receipt.json")
        self.assertTrue(receipt["fixture"])
        self.assertEqual(len(receipt["samples"]), 13)
        self.assertEqual(receipt["reproducibility"]["raw_sha256_before"], receipt["reproducibility"]["raw_sha256_after"])
        for sample in receipt["samples"]:
            self.assertLessEqual(sample["duration_seconds"], 6)
            self.assertTrue(sample["fixture"])
            self.assertEqual(sample["sha256"], render.sha256(a / sample["path"]))
            self.assertEqual(sample["timing_sha256"], render.sha256(a / sample["timing_path"]))
            self.assertTrue(sample["source_refs"])
        self.assertEqual(before, {p.name: render.sha256(p) for p in (self.fixture / "raw").iterdir()})

    def test_wav_and_alignment_hash_mismatch_fail(self):
        session, manifest = self.session_copy()
        manifest["takes"][0]["sha256"] = "0" * 64
        self.save_manifest(session, manifest)
        self.error("source_hash_mismatch", render.validate_manifest, session / "session.json")
        manifest["takes"][0]["sha256"] = render.sha256(session / manifest["takes"][0]["path"])
        manifest["takes"][0]["alignment"]["sha256"] = "0" * 64
        self.save_manifest(session, manifest)
        self.error("alignment_hash_mismatch", render.validate_manifest, session / "session.json")

    def test_reviewed_labels_bind_exact_wav_hash_rate_and_frames(self):
        session, manifest = self.session_copy()
        take = manifest["takes"][0]
        label_path = session / take["alignment"]["path"]
        original = render.json_read(label_path)
        for field, wrong in (("wav_sha256", "0" * 64), ("wav_frames", 123), ("sample_rate", 44100), ("sample_rate", True)):
            with self.subTest(field=field, wrong=wrong):
                changed = {**original, field: wrong}
                label_path.write_bytes(render.json_bytes(changed))
                take["alignment"]["sha256"] = render.sha256(label_path)
                self.save_manifest(session, manifest)
                self.error("alignment_wav_mismatch", render.validate_manifest, session / "session.json")

    def test_label_review_gaps_and_bool_frames_fail(self):
        session, manifest = self.session_copy()
        original = render.json_read(session / manifest["takes"][0]["alignment"]["path"])
        for code, transform in (
                ("labels_unreviewed", lambda data: data.update(reviewed=False)),
                ("invalid_integer", lambda data: data["intervals"][0].update(start_frame=False)),
                ("label_gap_or_overlap", lambda data: data["intervals"][1].update(start_frame=24001))):
            with self.subTest(code=code):
                self.update_labels(session, manifest, lambda data: (data.clear(), data.update(copy.deepcopy(original)), transform(data)))
                self.error(code, render.validate_manifest, session / "session.json")

    def test_exact_text_hash_required(self):
        session, manifest = self.session_copy()
        manifest["requests"][0]["source"]["text_sha256"] = "0" * 64
        self.save_manifest(session, manifest)
        self.error("text_hash_mismatch", render.validate_manifest, session / "session.json")

    def test_unknown_and_unsupported_tokens_are_visible_with_source(self):
        source = {"id": "test:source", "version": "v7"}
        for text, code in (("unknown", "missing_pronunciation"), ("café", "unsupported_token"),
                           ("123", "unsupported_token"), ("[illegible]", "unsupported_token"), ("...", "empty_text")):
            with self.subTest(text=text):
                with self.assertRaises(render.PilotError) as raised:
                    render.text_phones(text, {"known": ["AA"]}, source)
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(raised.exception.context["source"], source)

    def test_missing_units_stop_and_write_diagnostic_without_samples(self):
        session, manifest = self.session_copy()
        manifest["lexicon"]["calibration"] = ["B"]
        self.save_manifest(session, manifest)
        self.error("missing_units", render.run, session / "session.json", self.base / "failed")
        diagnostic = render.json_read(self.base / "failed/diagnostic.json")
        self.assertEqual(diagnostic["errors"][0]["code"], "missing_units")
        self.assertFalse((self.base / "failed/samples").exists())

    def test_manifest_mutation_during_render_is_rejected(self):
        session, manifest = self.session_copy()
        original = render.concat_render
        def mutate(*args):
            (session / "session.json").write_bytes(render.json_bytes({**manifest, "status": "changed mid-render"}))
            return original(*args)
        with patch.object(render, "concat_render", side_effect=mutate):
            self.error("manifest_changed", render.run, session / "session.json", self.base / "failed")
        self.assertFalse((self.base / "failed/receipt.json").exists())

    def test_raw_and_alignment_mutation_during_render_are_rejected(self):
        for target, code in (("path", "raw_changed"), ("alignment", "alignment_changed")):
            with self.subTest(target=target):
                session = self.base / target
                shutil.copytree(self.fixture, session)
                manifest = render.json_read(session / "session.json")
                take = manifest["takes"][0]
                file = session / (take[target] if target == "path" else take[target]["path"])
                original = render.concat_render
                def mutate(*args):
                    with file.open("ab") as stream:
                        stream.write(b" ")
                    return original(*args)
                with patch.object(render, "concat_render", side_effect=mutate):
                    self.error(code, render.run, session / "session.json", self.base / f"failed-{target}")

    def test_diphone_midpoints_and_direction_semantics(self):
        manifest, _, units, _ = render.validate_manifest(self.fixture / "session.json")
        ref = units["AA-M"][0]["reference"]
        self.assertEqual((ref["start_frame"], ref["mid_frame"], ref["end_frame"]), (12000, 24000, 36000))
        requests = {r["mode"]: r for r in manifest["requests"]}
        mirror, refs, params, timing = render.concat_render(requests["mirror"], manifest, units)
        red, red_refs, red_params, red_timing = render.concat_render(requests["red_room"], manifest, units)
        np.testing.assert_allclose(mirror, red, atol=1e-14)
        self.assertTrue(all(ref["reversed_within_unit"] for ref in refs))
        self.assertTrue(all(ref["whole_buffer_reversed"] for ref in red_refs))
        self.assertFalse(params["td_psola"])
        ordered = sorted(red_timing, key=lambda x: x["start_frame"])
        self.assertEqual(ordered[0]["overlap_before_frames"], 0)
        for previous, current in zip(ordered, ordered[1:]):
            self.assertEqual(current["overlap_before_frames"], previous["end_frame"] - current["start_frame"])

    def test_wav_format_depth_clipping_and_silence(self):
        for name, rate, channels, samples, code in (
                ("wrong-rate", 44100, 1, [5000] * 100, "invalid_wav_format"),
                ("stereo", 48000, 2, [5000] * 100, "invalid_wav_format"),
                ("clipped", 48000, 1, [32767] * 100, "clipping_or_low_headroom"),
                ("silent", 48000, 1, [0] * 100, "silent_input")):
            path = self.base / f"{name}.wav"
            with wave.open(str(path), "wb") as stream:
                stream.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
                stream.writeframes(np.asarray(samples, dtype="<i2").tobytes())
            self.error(code, render.read_wav, path, fixture=True, purpose="texture")
        render.read_wav(self.base / "silent.wav", fixture=True, purpose="calibration_room")
        self.error("invalid_wav_depth", render.read_wav, self.base / "silent.wav", fixture=False, purpose="calibration_room")
        bad = self.base / "bad.wav"
        bad.write_bytes(b"not a WAV")
        self.error("invalid_wav", render.read_wav, bad, fixture=True, purpose="texture")

    def test_finite_parameters_resource_bounds_and_pitch(self):
        x = .2 * np.sin(2 * np.pi * 220 * np.arange(48000) / 48000)
        for params in ({"factor": 201}, {"preview_seconds": 7}, {"window_seconds": 1.01}, {"seed": True}, {"factor": float("nan")}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                dsp.spectral_texture(x, 48000, **params)
        with self.assertRaises(ValueError):
            dsp.finite_audio([float("inf")])
        y, params = dsp.spectral_texture(x, 48000, factor=200, window_seconds=.25, preview_seconds=1)
        self.assertEqual(len(y), 48000)
        self.assertEqual(params["implied_full_duration_seconds"], 200)
        self.assertTrue(params["preview_truncated"])
        spectrum = abs(np.fft.rfft(y * np.hanning(len(y))))
        self.assertLess(abs(np.argmax(spectrum) - 220), 8)
        frozen, info = dsp.spectral_texture(x, 48000, freeze=True, preview_seconds=1)
        self.assertTrue(info["freeze"])
        octave, info = dsp.octave(x, 48000, semitones=-12)
        self.assertEqual(len(octave), 96000)
        self.assertFalse(info["duration_preserved"])
        reverb, info = dsp.voice_reverb(x, 48000)
        self.assertEqual(len(info["taps"]), 12)
        self.assertFalse(info["external_impulse_response"])
        self.assertTrue(np.isfinite(reverb).all())

    def test_json_nan_privacy_output_and_path_traversal_rejected(self):
        invalid = self.base / "nan.json"
        invalid.write_text('{"value":NaN}')
        self.error("nonfinite_json", render.json_read, invalid)
        invalid.write_text('{"value":1e999}')
        self.error("nonfinite_json", render.json_read, invalid)
        self.error("publication_path_forbidden", render.new_directory, render.ROOT / "site/audio-test")
        self.error("output_exists", render.new_directory, self.fixture)
        self.error("unsafe_source_path", render.inside, self.fixture, "../other.wav")
        session, manifest = self.session_copy()
        manifest["privacy"]["rendered_release"] = "public"
        self.save_manifest(session, manifest)
        self.error("privacy_gate", render.validate_manifest, session / "session.json")

    def test_decisions_require_explicit_nonblank_string_records(self):
        valid = {"choice": "test choice", "author": "test operator", "source": "test:decision"}
        self.assertEqual(render.decision_value({"D01": valid}, "D01"), "test choice")
        self.assertEqual(render.decision_value([{"id": "D01", **valid}], "D01"), "test choice")
        for field in ("choice", "author", "source"):
            for value in (None, " ", [], 1, True):
                self.assertIsNone(render.decision_value({"D01": {**valid, field: value}}, "D01"))

    def test_packet_is_one_finite_proposal_with_no_author_defaults(self):
        data = render.prompt_packet()
        self.assertEqual(len(data["prompts"]), 50)
        self.assertEqual([sum(p["section"] == kind for p in data["prompts"]) for kind in ("calibration", "concatenative", "texture")], [2, 24, 24])
        self.assertEqual(sum(p["estimated_seconds"] for p in data["prompts"]) + data["recording_request"]["setup_break_label_budget_seconds"], 1800)
        self.assertTrue(all(p["target"]["respelling"] and p["filename"] == p["id"] + ".wav" for p in data["prompts"]))
        self.assertTrue(all(v["choice"] is None for v in data["author_decisions"].values()))

    def test_supplied_shape_intake_binds_packet_and_preserves_original(self):
        # Pure sine input exercises the supplied-recording path; it is not human or speech evidence.
        packet = self.base / "packet"
        render.packet(packet)
        prompts = render.json_read(packet / "prompts.json")
        for key in render.REQUIRED_RECORDING_DECISIONS:
            prompts["author_decisions"][key] = {"choice": "test only", "author": "test operator", "source": "test:fixture"}
        (packet / "prompts.json").write_bytes(render.json_bytes(prompts))
        originals, labels = self.base / "originals", self.base / "labels"
        originals.mkdir(); labels.mkdir()
        wav = originals / "C27.wav"
        render.write_wav(wav, .2 * np.sin(2 * np.pi * 220 * np.arange(48000) / 48000))
        before = render.sha256(wav)
        render.labels_template(wav, "pau IY pau", "C27", labels / "C27.json")
        data = render.json_read(labels / "C27.json")
        data.update(reviewed=True, reviewer="test fixture operator")
        for interval, (a, b) in zip(data["intervals"], ((0, 1200), (1200, 46800), (46800, 48000))):
            interval.update(start_frame=a, end_frame=b)
        (labels / "C27.json").write_bytes(render.json_bytes(data))
        config = render.json_read(packet / "session-request.template.json")
        config.update(author_decisions=prompts["author_decisions"], recordings_directory=str(originals), labels_directory=str(labels), take_ids=["C27"])
        config["source_refs"][0]["packet_sha256"] = render.sha256(packet / "prompts.json")
        request = packet / "request.json"
        request.write_bytes(render.json_bytes(config))
        result = render.init_session(request, self.base / "human-shape-test")
        manifest, loaded, _, _ = render.validate_manifest(result["manifest"])
        self.assertEqual(manifest["acquisition_packet"]["sha256"], config["source_refs"][0]["packet_sha256"])
        self.assertEqual(manifest["takes"][0]["source"]["prompt_snapshot"], prompts["prompts"][26])
        self.assertEqual(before, render.sha256(wav))
        config["source_refs"][0]["packet_sha256"] = "0" * 64
        request.write_bytes(render.json_bytes(config))
        self.error("packet_hash_mismatch", render.init_session, request, self.base / "stale")

    def test_textgrid_import_requires_review_and_preserves_seconds_and_hash(self):
        wav = self.fixture / "raw/pair-AA-M.wav"
        grid = self.base / "reviewed.TextGrid"
        grid.write_text('''File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 1
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.5
            text = "AA"
        intervals [2]:
            xmin = 0.5
            xmax = 1
            text = "M"
''')
        output = self.base / "imported.json"
        render.import_textgrid(grid, wav, "pair-AA-M", "technical fixture review", output, fixture_flag=True)
        data = render.labels_read(output, 48000, "pair-AA-M", fixture=True, wav_sha256=render.sha256(wav))
        self.assertEqual(data["intervals"][1]["start_frame"], 24000)
        self.assertEqual(data["import"]["textgrid_sha256"], render.sha256(grid))


if __name__ == "__main__":
    unittest.main()
