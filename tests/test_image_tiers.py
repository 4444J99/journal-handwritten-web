"""tools/image_tiers.py: deterministic cleanup + manifest verification (JHW #25).

Builds synthetic page images in temporary folders, so nothing under the real
site/ or images/ is touched. Skips when Pillow / numpy / scipy are absent
(the tool needs them; tools/check.py verifies the manifest without them).
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage  # noqa: F401  (imported for the availability check)
    HAVE_STACK = True
except ImportError:
    HAVE_STACK = False

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check as checkmod  # noqa: E402
import image_tiers as tiers  # noqa: E402


def synthetic_page(path: Path, faint: bool = False, size=(320, 240)) -> None:
    """A white page with dark horizontal handwriting-like strokes.

    Strokes are 3 px wide and axis-aligned, like real ruled handwriting:
    thin enough to exercise the denoise/sharpen steps, thick enough that a
    3x3 median does not erase them (a 2 px slanted stroke would be a
    worst case the real pages do not have).
    """
    img = Image.new("RGB", size, (250, 248, 244))
    draw = ImageDraw.Draw(img)
    ink = (150, 145, 140) if faint else (40, 38, 35)
    for y in range(20, size[1] - 10, 18):
        draw.line([(15, y), (size[0] - 20, y)], fill=ink, width=3)
        draw.line([(15, y + 7), (size[0] - 60, y + 7)], fill=ink, width=3)
    img.save(path, format="JPEG", quality=92)


@unittest.skipUnless(HAVE_STACK, "Pillow/numpy/scipy required")
class ImageTiersTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "images" / "cleaned").mkdir(parents=True)
        self.master = self.root / "site" / "img" / "p" / "diaryX.jpg"
        self.master.parent.mkdir(parents=True)
        synthetic_page(self.master)

    def tearDown(self):
        self._tmp.cleanup()

    def test_clean_is_deterministic(self):
        rgb = np.asarray(Image.open(self.master).convert("RGB")).astype(np.float32)
        out1, _ = tiers.clean_array(rgb)
        out2, _ = tiers.clean_array(rgb)
        np.testing.assert_array_equal(out1, out2)

    def test_clean_improves_faint_page(self):
        faint = self.root / "faint.jpg"
        synthetic_page(faint, faint=True)
        rgb = np.asarray(Image.open(faint).convert("RGB")).astype(np.float32)
        _, m = tiers.clean_array(rgb)
        self.assertGreater(m["after"]["std"], m["before"]["std"])
        self.assertGreater(m["after"]["lap_var"], m["before"]["lap_var"])
        self.assertGreaterEqual(m["after"]["dark_frac"], m["before"]["dark_frac"])

    def test_clean_keeps_dimensions_and_mode(self):
        out = self.root / "images" / "cleaned" / "diaryX.jpg"
        tiers.clean_file(self.master, out)
        cleaned = Image.open(out)
        self.assertEqual(cleaned.size, Image.open(self.master).size)
        self.assertEqual(cleaned.mode, "RGB")

    def test_recipe_schema_and_no_sr(self):
        out = self.root / "images" / "cleaned" / "diaryX.jpg"
        recipe = tiers.clean_file(self.master, out)
        for key in checkmod.RECIPE_KEYS:
            self.assertIn(key, recipe)
        self.assertIsNone(recipe["sr"])
        self.assertIn("before", recipe["measurements"])
        self.assertIn("after", recipe["measurements"])

    def test_master_write_guard(self):
        with self.assertRaises(ValueError):
            tiers.clean_file(self.master, self.master)

    def test_deskew_axis_aligned(self):
        rgb = np.asarray(Image.open(self.master).convert("RGB")).astype(np.float32)
        angle = tiers.estimate_skew(tiers.luminance(rgb))
        self.assertLessEqual(abs(angle), 0.5)


@unittest.skipUnless(HAVE_STACK, "Pillow/numpy/scipy required")
class ManifestVerifyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "site" / "img" / "p").mkdir(parents=True)
        (self.root / "images" / "cleaned").mkdir(parents=True)
        self.master = self.root / "site" / "img" / "p" / "diaryX.jpg"
        synthetic_page(self.master)
        self.cleaned = self.root / "images" / "cleaned" / "diaryX.jpg"
        recipe = tiers.clean_file(self.master, self.cleaned)
        # Build the entry by hand: tiers.manifest_entry resolves against the
        # real repo root, so the temp-root hashes are computed here.
        self.manifest = {
            "version": 1,
            "tool": "tools/image_tiers.py",
            "tool_version": tiers.TOOL_VERSION,
            "pages": {
                "diaryX": {
                    "master": "site/img/p/diaryX.jpg",
                    "master_sha256": hashlib.sha256(self.master.read_bytes()).hexdigest(),
                    "cleaned": "images/cleaned/diaryX.jpg",
                    "cleaned_sha256": hashlib.sha256(self.cleaned.read_bytes()).hexdigest(),
                    "recipe": recipe,
                    "display": {"status": "pending", "reason": "no SR model provisioned"},
                },
            },
        }
        (self.root / "MANIFEST.sha256").write_text(
            f"{hashlib.sha256(self.master.read_bytes()).hexdigest()}  site/img/p/diaryX.jpg\n"
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _write_manifest(self):
        (self.root / "images-manifest.json").write_text(json.dumps(self.manifest))

    def test_consistent_manifest_passes(self):
        self._write_manifest()
        self.assertEqual(checkmod.verify_images_manifest(self.root), [])

    def test_tampered_cleaned_hash_fails(self):
        self._write_manifest()
        self.manifest["pages"]["diaryX"]["cleaned_sha256"] = "0" * 64
        self._write_manifest()
        problems = checkmod.verify_images_manifest(self.root)
        self.assertTrue(any("hash mismatch" in p for p in problems))

    def test_sr_in_cleaned_recipe_fails(self):
        self._write_manifest()
        self.manifest["pages"]["diaryX"]["recipe"]["sr"] = {"model": "Real-ESRGAN", "version": "x4plus"}
        self._write_manifest()
        problems = checkmod.verify_images_manifest(self.root)
        self.assertTrue(any("super-resolution recorded in the cleaned tier" in p for p in problems))

    def test_built_display_without_model_fails(self):
        self._write_manifest()
        self.manifest["pages"]["diaryX"]["display"] = {
            "status": "built", "file": "images/display/diaryX.jpg",
            "sha256": "0" * 64, "sr": {},
        }
        self._write_manifest()
        problems = checkmod.verify_images_manifest(self.root)
        self.assertTrue(any("without sr model+version" in p for p in problems))

    def test_missing_manifest_is_not_a_problem(self):
        self.assertEqual(checkmod.verify_images_manifest(self.root), [])


if __name__ == "__main__":
    unittest.main()
