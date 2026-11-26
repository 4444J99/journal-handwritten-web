"""Tests for tools/export_round1_projection.py (Round 1 social projections).

All output images are written to temporary directories outside the repo.
The tests verify metadata stripping and shared/spread-surface isolation.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TOOL = TOOLS / "export_round1_projection.py"
J_JSON = ROOT / "site" / "data" / "j.json"
CANONICAL = ROOT / "source" / "canonical.json"
sys.path.insert(0, str(TOOLS))

from build_chronology import CorpusIndex  # noqa: E402

from PIL import Image, ImageCms  # noqa: E402
from PIL.TiffImagePlugin import IFDRational  # noqa: E402

XMP_MARKER = b"http://ns.adobe.com/xap/1.0/\x00"
EXIF_MARKER = b"Exif\x00\x00"


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


class ExportRound1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = CorpusIndex(J_JSON, CANONICAL)

    def chronology(self, pieces: list[str]) -> dict[str, Any]:
        entries = []
        for piece_id in pieces:
            surface = self.corpus.primary_surface(piece_id)
            entries.append(
                {
                    "piece_id": piece_id,
                    "witnesses": {
                        "codex_scan": {
                            "surface_id": surface,
                            "scan_sha256": self.corpus.canonical_masters.get(surface, ""),
                            "digitized_at": "2015-09",
                            "shared_surface": surface in self.corpus.multi_piece_pages,
                        },
                        "photo_witnesses": [],
                        "linked_ios_notes": [],
                    },
                    "chronology": {
                        "date_basis": "photo_anchored",
                        "est_start": "2015-01-02",
                        "est_end": "2015-01-06",
                        "anchor_prev": None,
                        "anchor_next": "ph-001-a",
                        "amalgamated_sort_key": f"2015-01-06T10:00:00#{piece_id}",
                    },
                }
            )
        return {"schema": "versforms.chronology.v1", "physical_codex_order": entries}

    def run_tool(
        self,
        chronology: dict[str, Any],
        out_dir: Path,
        tmp: str,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        chronology_path = Path(tmp) / "chronology.json"
        chronology_path.write_text(json.dumps(chronology, indent=2), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--chronology",
                str(chronology_path),
                "--j-json",
                str(J_JSON),
                "--out-dir",
                str(out_dir),
                *extra,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def manifest(self, out_dir: Path) -> dict[str, Any]:
        return json.loads(
            (out_dir / "projection_manifest.json").read_text(encoding="utf-8")
        )

    def make_metadata_rich_image(self, path: Path) -> None:
        """Write a JPEG carrying EXIF, GPS, XMP, ICC and an IFD1 thumbnail."""
        image = Image.new("RGB", (96, 64), (130, 90, 50))
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
        exif = Image.Exif()
        exif[0x010F] = "Apple"
        exif[0x0110] = "iPhone"
        exif[0x8825] = {
            1: "N",
            2: (IFDRational(40, 1), IFDRational(42, 1), IFDRational(0, 1)),
            3: "W",
            4: (IFDRational(73, 1), IFDRational(59, 1), IFDRational(0, 1)),
        }
        image.save(path, format="JPEG", exif=exif, icc_profile=profile.tobytes())
        payload = XMP_MARKER + b"<x:xmpmeta>private</x:xmpmeta>"
        raw = path.read_bytes()
        marker = b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big")
        path.write_bytes(raw[:2] + marker + payload + raw[2:])

    def test_01_metadata_is_stripped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_export_01_") as tmp:
            base = Path(tmp)
            source = base / "rich.jpg"
            self.make_metadata_rich_image(source)
            raw_source = source.read_bytes()
            self.assertIn(EXIF_MARKER, raw_source)
            self.assertIn(XMP_MARKER, raw_source)
            out_dir = base / "out"
            proc = self.run_tool(
                self.chronology(["p001"]),
                out_dir,
                tmp,
                "--piece",
                "p001",
                "--surface",
                "diary1",
                "--override-image",
                str(source),
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            output = out_dir / "p001_diary1.jpg"
            self.assertTrue(output.is_file())
            raw = output.read_bytes()
            for marker in (EXIF_MARKER, XMP_MARKER, b"APP2", b"\xff\xd8\xff\xe2"):
                self.assertNotIn(marker, raw)
            with Image.open(output) as image:
                self.assertEqual(image.getexif(), {})
                self.assertNotIn("icc_profile", image.info)
                self.assertNotIn("xmp", image.info)
            manifest = self.manifest(out_dir)
            self.assertEqual(manifest["schema"], "versforms.round1-projection.v1")
            self.assertEqual(len(manifest["exports"]), 1)
            self.assertEqual(manifest["exports"][0]["sha256"], file_sha256(output))
            self.assertEqual(source.read_bytes(), raw_source, "source image was mutated")

    def test_02_shared_surface_diary62a_is_isolated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_export_02_") as tmp:
            base = Path(tmp)
            source = ROOT / "site" / "img" / "p" / "diary62a.jpg"
            out_dir = base / "out"
            proc = self.run_tool(
                self.chronology(["p001", "p126"]),
                out_dir,
                tmp,
                "--piece",
                "p001",
                "--surface",
                "diary62a",
                "--override-image",
                str(source),
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            export = self.manifest(out_dir)["exports"][0]
            self.assertTrue(export["shared_surface"])
            self.assertTrue(export["isolated_crop"])
            page = self.corpus.page_by_id["diary62a"]
            crop = export["crop_box"]
            self.assertEqual(len(crop), 4)
            self.assertLess(crop[2] - crop[0], page["iw"])
            self.assertLess(crop[3] - crop[1], page["ih"])
            with Image.open(out_dir / export["output_file"]) as image:
                self.assertEqual(image.size, (crop[2] - crop[0], crop[3] - crop[1]))
                self.assertLess(image.width, page["iw"])
                self.assertLess(image.height, page["ih"])

    def test_03_shared_surface_no_crop_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_export_03_") as tmp:
            base = Path(tmp)
            out_dir = base / "out"
            proc = self.run_tool(
                self.chronology(["p001"]),
                out_dir,
                tmp,
                "--piece",
                "p001",
                "--surface",
                "diary62a",
                "--override-image",
                str(ROOT / "site" / "img" / "p" / "diary62a.jpg"),
                "--no-crop",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            manifest = self.manifest(out_dir)
            self.assertEqual(manifest["exports"], [])
            self.assertEqual(len(manifest["blocked"]), 1)
            self.assertEqual(manifest["blocked"][0]["reason"], "co_tenanted_surface_blocked_without_crop")

    def test_04_spread_exposed_surface_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_export_04_") as tmp:
            base = Path(tmp)
            out_dir = base / "out"
            proc = self.run_tool(
                self.chronology(["p039"]),
                out_dir,
                tmp,
                "--piece",
                "p039",
                "--surface",
                "diary25",
                "--override-image",
                str(ROOT / "site" / "img" / "p" / "diary25.jpg"),
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            manifest = self.manifest(out_dir)
            self.assertEqual(manifest["exports"], [])
            self.assertEqual(
                manifest["blocked"][0]["reason"],
                "spread_exposed_surface_requires_isolation",
            )

    def test_05_strict_mode_fails_when_all_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_export_05_") as tmp:
            base = Path(tmp)
            out_dir = base / "out"
            proc = self.run_tool(
                self.chronology(["p039"]),
                out_dir,
                tmp,
                "--piece",
                "p039",
                "--surface",
                "diary25",
                "--override-image",
                str(ROOT / "site" / "img" / "p" / "diary25.jpg"),
                "--strict",
            )
            self.assertNotEqual(proc.returncode, 0)

    def test_06_unknown_piece_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_export_06_") as tmp:
            base = Path(tmp)
            proc = self.run_tool(
                self.chronology([]),
                base / "out",
                tmp,
                "--piece",
                "p999",
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn("unknown piece_id", proc.stderr)

    def test_07_manifest_has_no_private_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_export_07_") as tmp:
            base = Path(tmp)
            out_dir = base / "out"
            proc = self.run_tool(
                self.chronology(["p001"]),
                out_dir,
                tmp,
                "--piece",
                "p001",
                "--surface",
                "diary1",
                "--override-image",
                str(ROOT / "site" / "img" / "p" / "diary1.jpg"),
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            raw = (out_dir / "projection_manifest.json").read_text(encoding="utf-8")
            for forbidden in ("plaintext", "local_path", "ocr_text", "/Users/", "title"):
                self.assertNotIn(forbidden, raw)


if __name__ == "__main__":
    unittest.main()
