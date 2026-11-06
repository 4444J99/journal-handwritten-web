#!/usr/bin/env python3
"""Read-only, loopback-only pilot server. Never serve a recording directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/playback.js": ("playback.js", "text/javascript; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8")}
SAMPLE_PATH = re.compile(r"samples/[A-Za-z0-9][A-Za-z0-9_.-]*\.wav\Z")
HASH = re.compile(r"[a-fA-F0-9]{64}\Z")
MAX_SAMPLE_BYTES = 40 * 1024 * 1024


def safe_file(root: Path, relative: str) -> Path:
    """Resolve only an existing ordinary file, with no symlink in the route."""
    root = root.absolute()
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in (".", "..") for p in parts):
        raise ValueError("Invalid relative file path")
    candidate = root
    if candidate.is_symlink():
        raise ValueError("Symlink root is not served")
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("Symlink files or directories are not served")
    candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    if not candidate.is_file():
        raise ValueError("Expected an ordinary file")
    return candidate


def make_server(renders: Path | None, packet: Path | None, port: int = 8765) -> ThreadingHTTPServer:
    static_root = Path(__file__).parent
    routes = {route: (safe_file(static_root, name).read_bytes(), mime) for route, (name, mime) in STATIC.items()}
    samples = {}
    if renders is not None:
        raw = safe_file(renders, "receipt.json").read_bytes()
        receipt = json.loads(raw)
        if not isinstance(receipt, dict) or receipt.get("schema_version") != 1 or not isinstance(receipt.get("fixture"), bool) or not isinstance(receipt.get("samples"), list):
            raise ValueError("Expected a version 1 receipt with samples")
        if not isinstance(receipt.get("session_id"), str) or not receipt["session_id"].strip() or not isinstance(receipt.get("manifest_sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", receipt["manifest_sha256"]):
            raise ValueError("Receipt requires a session ID and lowercase SHA-256 manifest hash")
        ids = set()
        for sample in receipt["samples"]:
            if not isinstance(sample, dict) or not isinstance(sample.get("id"), str) or not sample["id"] or not isinstance(sample.get("fixture"), bool):
                raise ValueError("Each rendered sample needs an ID and explicit fixture status")
            relative, digest = sample.get("path", ""), sample.get("sha256", "")
            if not SAMPLE_PATH.fullmatch(relative) or not HASH.fullmatch(digest):
                raise ValueError("Unsafe or unidentified rendered sample")
            if relative in samples or sample.get("id") in ids:
                raise ValueError("Duplicate rendered sample path or ID")
            path = safe_file(renders, relative)
            if path.stat().st_size > MAX_SAMPLE_BYTES:
                raise ValueError("Rendered sample exceeds 40 MiB")
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest.lower():
                raise ValueError("Rendered sample does not match receipt SHA-256")
            samples[relative] = digest.lower()
            ids.add(sample.get("id"))
        routes["/receipt.json"] = (raw, "application/json; charset=utf-8")
    if packet is not None:
        if packet.name.endswith(".json"):
            prompt_file = safe_file(packet.parent, packet.name)
        else:
            prompt_file = safe_file(packet, "prompts.json")
        raw = prompt_file.read_bytes()
        prompts = json.loads(raw)
        if not isinstance(prompts, dict) or prompts.get("schema_version") != 1 or not isinstance(prompts.get("prompts"), list):
            raise ValueError("Expected a version 1 prompt packet")
        routes["/prompts.json"] = (raw, "application/json; charset=utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.respond(head=True)

        def do_GET(self):
            self.respond(head=False)

        def respond(self, head=False):
            expected = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected:
                self.reply(403, b"Loopback host required.\n", "text/plain", head)
                return
            try:
                parsed = urlsplit(self.path)
                path = unquote(parsed.path, errors="strict")
            except (ValueError, UnicodeError):
                self.reply(404, b"Route not allowed.\n", "text/plain", head)
                return
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or path != parsed.path or "\\" in path or "\x00" in path:
                self.reply(404, b"Route not allowed.\n", "text/plain", head)
                return
            if path in routes:
                data, mime = routes[path]
                self.reply(200, data, mime, head)
                return
            relative = path.removeprefix("/")
            if path.startswith("/samples/") and relative in samples:
                try:
                    file = safe_file(renders, relative)
                    if file.stat().st_size > MAX_SAMPLE_BYTES:
                        raise ValueError("Sample too large")
                    data = file.read_bytes()
                    if hashlib.sha256(data).hexdigest() != samples[relative]:
                        raise ValueError("Sample identity changed")
                except (OSError, ValueError):
                    self.reply(409, b"Rendered sample changed or is unsafe; restart with a valid receipt.\n", "text/plain", head)
                    return
                self.reply(200, data, "audio/wav", head)
                return
            self.reply(404, b"Route not allowed. Original recordings and directories are never served.\n", "text/plain", head)

        def reply(self, code, data, mime, head):
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self' blob:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            if not head:
                self.wfile.write(data)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renders", type=Path, help="Directory containing receipt.json and rendered samples (never raw recordings)")
    parser.add_argument("--packet", type=Path, help="Directory containing prompts.json, or exact prompt JSON file")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        server = make_server(args.renders, args.packet, args.port)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f"Pilot server could not start: {error}\n")
    print(f"Private T09 workbench: http://127.0.0.1:{server.server_port}/", flush=True)
    print("Read-only allowlist; no original recordings. Stop with Ctrl-C.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
