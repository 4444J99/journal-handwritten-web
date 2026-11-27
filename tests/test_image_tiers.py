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

# image_tiers imports scipy at module scope; importing it unconditionally here
# breaks discovery on machines without the optional local-tooling dependency.
# The tests that need it are already decorated with skipUnless(HAVE_STACK).
if HAVE_STACK:
    import image_tiers as tiers  # noqa: E402
else:
    tiers = None  # type: ignore[assignment]


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


@unittest.skipUnless(HAVE_STACK, "Pillow/numpy/scipy required")
class PaperBoxTest(unittest.TestCase):
    def _gray(self, path):
        return np.asarray(Image.open(path).convert("L")).astype(np.float32)

    def _bar_page(self, path, size=(320, 240), bars=None):
        """White page with strokes, plus solid black bars on named sides."""
        img = Image.new("RGB", size, (250, 248, 244))
        draw = ImageDraw.Draw(img)
        for y in range(20, size[1] - 10, 18):
            draw.line([(15, y), (size[0] - 20, y)], fill=(40, 38, 35), width=3)
        bars = bars or {}
        if "top" in bars:
            draw.rectangle([0, 0, size[0], bars["top"]], fill=(0, 0, 0))
        if "bottom" in bars:
            draw.rectangle([0, size[1] - bars["bottom"], size[0], size[1]], fill=(0, 0, 0))
        if "left" in bars:
            draw.rectangle([0, 0, bars["left"], size[1]], fill=(0, 0, 0))
        if "right" in bars:
            draw.rectangle([size[0] - bars["right"], 0, size[0], size[1]], fill=(0, 0, 0))
        img.save(path, format="JPEG", quality=92)
        return img

    def test_clean_page_is_full_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "clean.jpg"
            synthetic_page(p)
            box = tiers.paper_box(self._gray(p))
            self.assertEqual(box["box_norm"], [0.0, 0.0, 1.0, 1.0])
            self.assertEqual(box["inset_px"], {"top": 0, "bottom": 0, "left": 0, "right": 0})

    def test_top_and_left_bars_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bars.jpg"
            self._bar_page(p, bars={"top": 30, "left": 40})
            box = tiers.paper_box(self._gray(p))
            # downscaled measurement: within ~2% of the true edge
            self.assertAlmostEqual(box["box_norm"][0], 40 / 320, delta=0.02)
            self.assertAlmostEqual(box["box_norm"][1], 30 / 240, delta=0.02)
            self.assertEqual(box["box_norm"][2], 1.0)
            self.assertEqual(box["box_norm"][3], 1.0)

    def test_vertical_dark_band_left_only(self):
        # diary25 shape: a dark surface left of the paper, paper full height.
        # A one-pass row-wise detector would walk the bottom inset to the top;
        # the two-pass detector must find left ~0.6 and top/bottom ~0.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "band.jpg"
            self._bar_page(p, size=(400, 300), bars={"left": 240})
            box = tiers.paper_box(self._gray(p))
            self.assertAlmostEqual(box["box_norm"][0], 240 / 400, delta=0.02)
            self.assertEqual(box["box_norm"][1], 0.0)
            self.assertEqual(box["box_norm"][2], 1.0)
            self.assertEqual(box["box_norm"][3], 1.0)

    def test_fully_dark_image_is_not_cropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "dark.jpg"
            Image.new("RGB", (320, 240), (10, 10, 10)).save(p, format="JPEG", quality=92)
            box = tiers.paper_box(self._gray(p))
            self.assertEqual(box["box_norm"], [0.0, 0.0, 1.0, 1.0])


@unittest.skipUnless(HAVE_STACK, "Pillow/numpy/scipy required")
class CoverTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.master = self.root / "diaryX.jpg"
        synthetic_page(self.master, size=(640, 480))
        # block 0 occupies the top-left quarter of the page
        self.page = {"id": "diaryX", "x": [
            [0, 0, 0.05, 0.05, 0.60, 0.20, 0.0, 0.0],
            [0, 1, 0.05, 0.25, 0.55, 0.40, 0.0, 0.0],
            [1, 0, 0.05, 0.50, 0.60, 0.65, 0.0, 0.0],
        ]}

    def tearDown(self):
        self._tmp.cleanup()

    def test_opening_block_cover(self):
        cover, record = tiers.cover_image(self.master, self.page)
        self.assertEqual(cover.size, (1080, 1350))
        self.assertEqual(record["source"], "opening-block")
        self.assertEqual(record["block"], 0)
        self.assertEqual(record["paper_box_norm"], [0.0, 0.0, 1.0, 1.0])
        # cover box is the padded block-0 union, inside the paper box
        box = record["cover_box_norm"]
        self.assertAlmostEqual(box[0], 0.05 - 0.03, delta=0.005)
        self.assertAlmostEqual(box[1], 0.05 - 0.02, delta=0.005)
        self.assertAlmostEqual(box[2], 0.60 + 0.03, delta=0.005)
        self.assertAlmostEqual(box[3], 0.40 + 0.02, delta=0.005)
        # the strokes land on the canvas: the upper third is not blank paper
        arr = np.asarray(cover.convert("L")).astype(np.float32)
        self.assertLess(arr[300:600, 100:900].mean(), 245.0)

    def test_no_line_boxes_falls_back_to_whole_paper(self):
        cover, record = tiers.cover_image(self.master, {"id": "diaryX", "x": []})
        self.assertEqual(cover.size, (1080, 1350))
        self.assertEqual(record["source"], "whole-paper")
        self.assertIsNone(record["block"])
        self.assertEqual(record["cover_box_norm"], [0.0, 0.0, 1.0, 1.0])

    def test_cover_is_deterministic(self):
        import io
        c1, _ = tiers.cover_image(self.master, self.page)
        c2, _ = tiers.cover_image(self.master, self.page)
        b1, b2 = io.BytesIO(), io.BytesIO()
        c1.save(b1, format="JPEG", quality=92)
        c2.save(b2, format="JPEG", quality=92)
        self.assertEqual(b1.getvalue(), b2.getvalue())

    def test_tall_opening_block_is_not_clipped(self):
        # A tall, narrow opening block contains to the full canvas height
        # (1206px); the upper-third paste (y=270) would clip 126px off its
        # bottom, so y is clamped to the bottom margin instead (diary55a
        # side-by-side, JHW #48 step 6).
        page = {"id": "diaryX", "x": [
            [0, 0, 0.05, 0.02, 0.25, 0.98, 0.0, 0.0],
        ]}
        cover, record = tiers.cover_image(self.master, page)
        self.assertEqual(cover.size, (1080, 1350))
        arr = np.asarray(cover.convert("L")).astype(np.float32)
        # bottom margin rows are blank paper, not clipped handwriting
        self.assertGreater(arr[-40:, :].mean(), 240.0)
        # and the block itself is present (ink in the middle of the canvas)
        self.assertGreater((arr[200:1200, 100:900] < 200).mean(), 0.005)

    def test_opening_block_box_none_without_rows(self):
        self.assertEqual(tiers.opening_block_box({"id": "diaryX", "x": []}), (None, None))
        self.assertEqual(tiers.opening_block_box({"id": "diaryX"}), (None, None))

    def test_opening_block_is_first_block_with_geometry(self):
        # block 0 has no line boxes; the opening block is block 2, the
        # lowest-numbered block with rows (13 real pages look like this).
        page = {"id": "diaryX", "x": [
            [2, 0, 0.10, 0.10, 0.50, 0.30, 0.0, 0.0],
            [3, 0, 0.10, 0.40, 0.50, 0.60, 0.0, 0.0],
        ]}
        box, block = tiers.opening_block_box(page)
        self.assertEqual(block, 2)
        self.assertEqual(box, [0.1, 0.1, 0.5, 0.3])
        cover, record = tiers.cover_image(self.master, page)
        self.assertEqual(record["source"], "opening-block")
        self.assertEqual(record["block"], 2)


@unittest.skipUnless(HAVE_STACK, "Pillow/numpy/scipy required")
class CropsVerifyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "site" / "img" / "p").mkdir(parents=True)
        (self.root / "site" / "img" / "crop").mkdir(parents=True)
        self.master = self.root / "site" / "img" / "p" / "diaryX.jpg"
        synthetic_page(self.master, size=(640, 480))
        self.page = {"id": "diaryX", "x": [
            [0, 0, 0.05, 0.05, 0.60, 0.20, 0.0, 0.0],
            [0, 1, 0.05, 0.25, 0.55, 0.40, 0.0, 0.0],
        ]}
        self.cover_path = self.root / "site" / "img" / "crop" / "diaryX.jpg"
        cover, record = tiers.cover_image(self.master, self.page)
        cover.save(self.cover_path, format="JPEG", quality=92)
        self.manifest = {
            "version": 1,
            "tool": "tools/image_tiers.py",
            "tool_version": tiers.TOOL_VERSION,
            "pages": {
                "diaryX": {
                    "master": "site/img/p/diaryX.jpg",
                    "master_sha256": hashlib.sha256(self.master.read_bytes()).hexdigest(),
                    "paper_box_norm": record["paper_box_norm"],
                    "paper_box_px": record["paper_box_px"],
                    "cover": {
                        "file": "site/img/crop/diaryX.jpg",
                        "sha256": hashlib.sha256(self.cover_path.read_bytes()).hexdigest(),
                        "width": 1080,
                        "height": 1350,
                        "source": record["source"],
                        "block": record["block"],
                        "cover_box_norm": record["cover_box_norm"],
                    },
                },
            },
        }

    def tearDown(self):
        self._tmp.cleanup()

    def _write_manifest(self):
        (self.root / "images-crops.json").write_text(json.dumps(self.manifest))

    def test_consistent_crops_manifest_passes(self):
        self._write_manifest()
        self.assertEqual(checkmod.verify_crops_manifest(self.root), [])

    def test_tampered_cover_hash_fails(self):
        self._write_manifest()
        self.manifest["pages"]["diaryX"]["cover"]["sha256"] = "0" * 64
        self._write_manifest()
        problems = checkmod.verify_crops_manifest(self.root)
        self.assertTrue(any("hash mismatch" in p for p in problems))

    def test_wrong_cover_dimensions_fail(self):
        Image.new("RGB", (100, 100), (250, 248, 244)).save(self.cover_path, format="JPEG", quality=92)
        self._write_manifest()
        problems = checkmod.verify_crops_manifest(self.root)
        self.assertTrue(any("not 1080x1350" in p for p in problems))

    def test_cover_box_escaping_paper_box_fails(self):
        self._write_manifest()
        self.manifest["pages"]["diaryX"]["cover"]["cover_box_norm"] = [0.0, 0.0, 1.0, 1.0]
        self.manifest["pages"]["diaryX"]["paper_box_norm"] = [0.2, 0.2, 0.8, 0.8]
        self._write_manifest()
        problems = checkmod.verify_crops_manifest(self.root)
        self.assertTrue(any("escapes paper box" in p for p in problems))

    def test_missing_manifest_is_not_a_problem(self):
        self.assertEqual(checkmod.verify_crops_manifest(self.root), [])

    def test_jpeg_size_reader(self):
        self.assertEqual(checkmod.jpeg_size(self.cover_path), (1080, 1350))
        self.assertEqual(checkmod.jpeg_size(self.master), (640, 480))


if __name__ == "__main__":
    unittest.main()
