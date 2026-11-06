"""Boundary tests for the private audio server, including raw-file denial."""
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest

SPEC = importlib.util.spec_from_file_location("pilot_server", Path(__file__).resolve().parents[1] / "audio_pilot" / "serve.py")
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.renders = self.root / "renders"
        (self.renders / "samples").mkdir(parents=True)
        self.audio = b"RIFF fixture bytes for transport only"
        self.sample = self.renders / "samples" / "fixture.wav"
        self.sample.write_bytes(self.audio)
        self.receipt = {"schema_version": 1, "fixture": True, "session_id": "transport-test-fixture", "manifest_sha256": "a" * 64, "samples": [{"id": "fixture", "fixture": True, "path": "samples/fixture.wav", "sha256": hashlib.sha256(self.audio).hexdigest()}]}
        (self.renders / "receipt.json").write_text(json.dumps(self.receipt))
        (self.renders / "raw.wav").write_bytes(b"private raw master")
        self.packet = self.root / "packet"
        self.packet.mkdir()
        (self.packet / "prompts.json").write_text(json.dumps({"schema_version": 1, "prompts": []}))
        self.server = SERVER.make_server(self.renders, self.packet, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, method="GET", host=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        connection.request(method, path, headers={} if host is None else {"Host": host})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_loopback_static_receipt_prompts_and_only_listed_sample(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        for route in ("/", "/app.js", "/playback.js", "/style.css", "/receipt.json", "/prompts.json"):
            with self.subTest(route=route):
                code, headers, data = self.request(route)
                self.assertEqual(code, 200)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
                self.assertTrue(data)
        self.assertEqual(self.request("/samples/fixture.wav")[2], self.audio)
        self.assertEqual(self.request("/samples/fixture.wav", "HEAD")[2], b"")

    def test_raw_directories_traversal_encodings_and_unlisted_files_denied(self):
        for route in ("/raw.wav", "/samples/", "/samples/unlisted.wav", "/../raw.wav", "/samples/../raw.wav", "/samples/%2e%2e/raw.wav", "/samples/%66ixture.wav", "/%FF", "/samples\\fixture.wav", "/receipt.json?raw=1", "/serve.py", "/timing/forward.json"):
            with self.subTest(route=route):
                self.assertEqual(self.request(route)[0], 404)

    def test_foreign_host_and_writes_denied(self):
        self.assertEqual(self.request("/receipt.json", host="foreign.example")[0], 403)
        self.assertEqual(self.request("/receipt.json", "POST")[0], 501)

    def test_changed_sample_identity_denied(self):
        self.sample.write_bytes(b"different rendered or raw content")
        self.assertEqual(self.request("/samples/fixture.wav")[0], 409)

    def test_sample_symlink_swap_denied(self):
        self.sample.unlink()
        self.sample.symlink_to(self.renders / "raw.wav")
        self.assertEqual(self.request("/samples/fixture.wav")[0], 409)

    def test_symlink_or_traversal_in_initial_receipt_denied(self):
        self.sample.unlink()
        self.sample.symlink_to(self.renders / "raw.wav")
        with self.assertRaises(ValueError):
            SERVER.make_server(self.renders, self.packet, 0)
        self.receipt["samples"][0]["path"] = "samples/../raw.wav"
        (self.renders / "receipt.json").write_text(json.dumps(self.receipt))
        with self.assertRaises(ValueError):
            SERVER.make_server(self.renders, self.packet, 0)

    def test_missing_or_invalid_manifest_identity_denied(self):
        for field, value in (("session_id", None), ("session_id", "  "), ("manifest_sha256", None), ("manifest_sha256", "short"), ("manifest_sha256", "A" * 64)):
            with self.subTest(field=field, value=value):
                receipt = dict(self.receipt)
                if value is None:
                    receipt.pop(field)
                else:
                    receipt[field] = value
                (self.renders / "receipt.json").write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError, "session ID.*manifest hash"):
                    SERVER.make_server(self.renders, self.packet, 0)


if __name__ == "__main__":
    unittest.main()
