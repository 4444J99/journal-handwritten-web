#!/usr/bin/env python3
"""
T07 media-production kit.

One source package -> stills, carousel, Reel, 9:16 assembly and widget tiles.
The source package is a piece/version/page selection in a JSON config plus the
repository's site/data/j.json line boxes and a preserved scan.

Design rules enforced here:
  * no generated copy is drawn on any export;
  * every crop is derived from a named page/version/block/line set;
  * every output is listed with a hash and a clearance state;
  * the same code path produces the second-piece substitution.

Run from the repository root (or pass --repo):
  python3 production/kit/kit.py --config production/kit/config/p001.json
  python3 production/kit/kit.py --config production/kit/config/p004.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W4, H4 = 1080, 1350
W9, H9 = 1080, 1920
PAPER = (247, 245, 239)
PAPER_RGB = PAPER
MARGIN = 72
JPEG_QUALITY = 92
FPS = 30

KIT_DIR = Path(__file__).resolve().parent
PRODUCTION_DIR = KIT_DIR.parent
DEFAULT_REPO = PRODUCTION_DIR.parent


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def git_head(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def rgb(im: Image.Image) -> Image.Image:
    return im.convert("RGB")


def resample(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    return im.resize(size, Image.Resampling.LANCZOS)


def fit_contain(im: Image.Image, w: int, h: int) -> Image.Image:
    s = min(w / im.width, h / im.height)
    return resample(im, (max(1, round(im.width * s)), max(1, round(im.height * s))))


def fit_cover(im: Image.Image, w: int, h: int) -> Image.Image:
    s = max(w / im.width, h / im.height)
    out = resample(im, (max(1, round(im.width * s)), max(1, round(im.height * s))))
    x = (out.width - w) // 2
    y = (out.height - h) // 2
    return out.crop((x, y, x + w, y + h))


def clamp_box(box, pad_x=0.0, pad_y=0.0):
    x0, y0, x1, y1 = box
    return (
        max(0.0, x0 - pad_x),
        max(0.0, y0 - pad_y),
        min(1.0, x1 + pad_x),
        min(1.0, y1 + pad_y),
    )


def page_row_boxes(page, block_ids=None, line_ids=None):
    """Return the j.json line boxes in reading order for the selected blocks."""
    out = []
    for row in page["x"]:
        b, ln = row[0], row[1]
        if block_ids is not None and b not in block_ids:
            continue
        if line_ids is not None and (b, ln) not in line_ids:
            continue
        out.append(tuple(row))
    return out


def union_box(rows):
    if not rows:
        raise ValueError("no line boxes selected")
    return (
        min(r[2] for r in rows),
        min(r[3] for r in rows),
        max(r[4] for r in rows),
        max(r[5] for r in rows),
    )


def crop_norm(im: Image.Image, box) -> Image.Image:
    w, h = im.size
    x0, y0, x1, y1 = box
    return im.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))


def page_canvas(w=W4, h=H4, color=PAPER_RGB) -> Image.Image:
    return Image.new("RGB", (w, h), color)


def add_paper_wash(canvas: Image.Image, alpha=0.0) -> Image.Image:
    if alpha <= 0:
        return canvas
    wash = Image.new("RGBA", canvas.size, (*PAPER, round(alpha * 255)))
    return Image.alpha_composite(canvas.convert("RGBA"), wash).convert("RGB")


def shadowed_card(card: Image.Image, pad=48, blur=18, opacity=96, offset=(0, 12)):
    w, h = card.size
    base = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    x0 = pad + offset[0]
    y0 = pad + offset[1]
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=(20, 18, 14, opacity))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(sh)
    base.alpha_composite(card.convert("RGBA"), (pad, pad))
    return base, pad


def paste_card(canvas: Image.Image, card: Image.Image, x: int, y: int,
              pad=48, blur=18, opacity=96) -> None:
    shadow, p = shadowed_card(card, pad=pad, blur=blur, opacity=opacity)
    canvas.paste(shadow, (x - p, y - p), shadow)


def rounded_rgba(im: Image.Image, radius: int) -> Image.Image:
    im = im.convert("RGBA")
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=radius, fill=255)
    im.putalpha(mask)
    return im


def identity_chip(path: Path, size=206, border=9) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    inner = fit_cover(src, size, size)
    inner = rounded_rgba(inner, round(size * 0.22))
    outer = Image.new("RGBA", (size + border * 2, size + border * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(outer)
    d.rounded_rectangle(
        [0, 0, outer.width - 1, outer.height - 1],
        radius=round((size + border * 2) * 0.22), fill=(255, 255, 255, 255),
    )
    outer.alpha_composite(inner, (border, border))
    return outer


# --------------------------------------------------------------------------
# source package
# --------------------------------------------------------------------------

class SourcePackage:
    def __init__(self, repo: Path, cfg: dict):
        self.repo = repo
        self.cfg = cfg
        jpath = repo / "site" / "data" / "j.json"
        self.j = load_json(jpath)
        self.j_sha = sha256(jpath)
        self.piece = self._piece(cfg["piece_id"])
        self.version = self._version(cfg["version_id"])
        self.page = self._page(cfg["page_id"])
        self.source_path = self._resolve(cfg["source"])
        self.source_kind = cfg.get("source_kind", "preserved")
        self.image = rgb(Image.open(self.source_path))
        self.src_w, self.src_h = self.image.size
        self._validate()

    def _piece(self, pid):
        for p in self.j["pieces"]:
            if p["id"] == pid:
                return p
        raise KeyError(pid)

    def _version(self, vid):
        for v in self.piece["V"]:
            if v["id"] == vid:
                return v
        raise KeyError(vid)

    def _page(self, pgid):
        for p in self.j["pages"]:
            if p["id"] == pgid:
                return p
        raise KeyError(pgid)

    def _resolve(self, rel):
        p = Path(rel)
        if not p.is_absolute():
            p = self.repo / p
        if not p.exists():
            raise FileNotFoundError(p)
        return p

    def _validate(self):
        # j.json page dimensions are the web tier. The original scan has the
        # same aspect ratio; a mismatch means the wrong file was supplied.
        want = self.page["iw"] / self.page["ih"]
        got = self.src_w / self.src_h
        if abs(want - got) > 0.01:
            raise ValueError(
                f"{self.source_path.name}: aspect {got:.4f} != j.json page "
                f"{self.page['id']} aspect {want:.4f}"
            )

    def version_blocks(self):
        blocks = []
        for pg, bs in self.version["P"]:
            if pg == self.page["id"]:
                blocks.extend(bs)
        return sorted(set(blocks))

    def blocks(self, ids):
        return [self.page["B"][i] for i in ids]

    def rows(self, block_ids):
        return page_row_boxes(self.page, block_ids=set(block_ids))

    def text(self, block_ids):
        return [ln for b in self.blocks(block_ids) for ln in b["L"]]

    def norm_to_px(self, box):
        return (
            box[0] * self.src_w, box[1] * self.src_h,
            box[2] * self.src_w, box[3] * self.src_h,
        )


# --------------------------------------------------------------------------
# renders
# --------------------------------------------------------------------------

def render_page(source: SourcePackage, block_ids=None, canvas_size=(W4, H4),
                margin=MARGIN, crop_blocks=None) -> Image.Image:
    canvas = page_canvas(*canvas_size)
    if crop_blocks:
        rows = source.rows(crop_blocks)
        box = clamp_box(union_box(rows), 0.012, 0.018)
        page_im = crop_norm(source.image, box)
    else:
        page_im = source.image.copy()
    max_w = canvas.width - margin * 2
    max_h = canvas.height - margin * 2
    card = fit_contain(page_im, max_w, max_h)
    x = (canvas.width - card.width) // 2
    y = (canvas.height - card.height) // 2
    paste_card(canvas, card, x, y, pad=36, blur=14, opacity=84)
    return canvas


def render_line(source: SourcePackage, block_ids, canvas_size=(W4, H4),
                pad=(0.030, 0.020), max_w=W4 - 2 * MARGIN) -> Image.Image:
    rows = source.rows(block_ids)
    box = clamp_box(union_box(rows), pad[0], pad[1])
    crop = crop_norm(source.image, box)
    canvas = page_canvas(*canvas_size)
    crop = fit_contain(crop, max_w, canvas.height - 2 * MARGIN)
    x = (canvas.width - crop.width) // 2
    # cover: upper third, so the eye lands on the opening
    y = round(canvas.height * 0.20) if canvas.height == H4 else (canvas.height - crop.height) // 2
    paste_card(canvas, crop, x, y, pad=30, blur=12, opacity=72)
    return canvas


def render_stack(source: SourcePackage, block_ids, avatar_path: Path | None,
                 canvas_size=(W4, H4)) -> Image.Image:
    rows = source.rows(block_ids)
    page_box = clamp_box(union_box(rows), 0.020, 0.020)
    page_im = crop_norm(source.image, page_box)

    # layer 3: the same scan, blurred and darkened, filling the frame
    bg = fit_cover(crop_norm(source.image, union_box(rows)), W4, H4)
    bg = bg.filter(ImageFilter.GaussianBlur(26))
    bg = ImageEnhance.Brightness(bg).enhance(0.78)
    canvas = add_paper_wash(bg, 0.10)

    # layer 2: page card
    max_h = H4 - 196
    card = fit_contain(page_im, W4 - 270, max_h)
    x = (W4 - card.width) // 2 + 26
    y = H4 - 84 - card.height
    paste_card(canvas, card, x, y, pad=40, blur=20, opacity=104)

    # layer 1: identity chip (author-supplied; see clearance)
    if avatar_path and avatar_path.exists():
        chip = identity_chip(avatar_path, size=214, border=9)
        # chip shadow
        sh = Image.new("RGBA", (chip.width + 56, chip.height + 56), (0, 0, 0, 0))
        d = ImageDraw.Draw(sh)
        d.rounded_rectangle([28, 36, 28 + chip.width, 36 + chip.height],
                            radius=52, fill=(18, 16, 12, 112))
        sh = sh.filter(ImageFilter.GaussianBlur(15))
        sh.alpha_composite(chip, (28, 28))
        canvas.paste(sh, (44, 48), sh)
    return canvas


def render_detail(source: SourcePackage, block_ids, canvas_size=(W4, H4)) -> Image.Image:
    return render_line(source, block_ids, canvas_size=canvas_size,
                       pad=(0.025, 0.018), max_w=W4 - 2 * 54)


def render_version_page(source: SourcePackage, page_id, block_ids,
                        canvas_size=(W4, H4)) -> Image.Image:
    """A later/alternate version, cropped to the p001 blocks only (neighbour excluded)."""
    pg = source._page(page_id)
    rows = page_row_boxes(pg, block_ids=set(block_ids))
    box = clamp_box(union_box(rows), 0.012, 0.018)
    im = rgb(Image.open(source._resolve(source.cfg["later_version"]["source"])))
    # scale factors for this page
    px = (box[0] * im.width, box[1] * im.height, box[2] * im.width, box[3] * im.height)
    crop = im.crop(tuple(round(v) for v in px))
    canvas = page_canvas(*canvas_size)
    card = fit_contain(crop, canvas.width - 2 * MARGIN, canvas.height - 2 * MARGIN)
    x = (canvas.width - card.width) // 2
    y = (canvas.height - card.height) // 2
    paste_card(canvas, card, x, y, pad=36, blur=14, opacity=84)
    return canvas


def render_still_set(src: SourcePackage, out: Path, avatar: Path | None,
                     cfg: dict) -> dict:
    cover_block = cfg["cover_block"]
    detail_block = cfg["detail_block"]
    primary_blocks = src.version_blocks()
    later = cfg.get("later_version")

    stills = {}
    stills["cover-stack"] = render_stack(src, primary_blocks, avatar)
    stills["cover-page"] = render_page(src, primary_blocks)
    stills["cover-line"] = render_line(src, [cover_block])
    stills["carousel-01-cover"] = stills["cover-stack"]
    stills["carousel-02-page"] = stills["cover-page"]
    stills["carousel-03-line"] = stills["cover-line"]
    stills["carousel-04-detail"] = render_detail(src, [detail_block])
    if later:
        stills["carousel-05-version"] = render_version_page(
            src, later["page_id"], later["blocks"]
        )
    else:
        stills["carousel-05-detail"] = render_detail(src, [primary_blocks[-1]])

    dirs = {"cover": out / "4x5", "carousel": out / "carousel"}
    written = {}
    for name, im in stills.items():
        sub = dirs["cover"] if name.startswith("cover-") else dirs["carousel"]
        sub.mkdir(parents=True, exist_ok=True)
        p = sub / f"{name}.jpg"
        im.save(p, quality=JPEG_QUALITY, subsampling=1, optimize=True)
        written[str(p.relative_to(out))] = im
    return written


# --------------------------------------------------------------------------
# motion
# --------------------------------------------------------------------------

def wipe_frames(a: Image.Image, b: Image.Image, t: float) -> Image.Image:
    """Soft vertical wipe; t=0 -> a, t=1 -> b."""
    t = max(0.0, min(1.0, t))
    edge = 48
    pos = round(-edge + (a.width + 2 * edge) * t)
    mask = Image.new("L", a.size, 0)
    d = ImageDraw.Draw(mask)
    d.rectangle([0, 0, max(0, pos), a.height], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(edge / 2))
    out = Image.composite(b, a, mask)
    return out


def framed_9x16(frame4x5: Image.Image) -> Image.Image:
    canvas = page_canvas(W9, H9)
    x = (W9 - frame4x5.width) // 2
    y = (H9 - frame4x5.height) // 2
    paste_card(canvas, frame4x5, x, y, pad=28, blur=16, opacity=80)
    return canvas


def make_reel(out: Path, a: Image.Image, b: Image.Image, piece_id: str,
              duration=6.0) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    frames_dir = out / "_frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    n = round(duration * FPS)
    fa = framed_9x16(a)
    fb = framed_9x16(b)

    # 0.00-0.75 hold A | 0.75-1.50 wipe A->B | 1.50-3.00 hold B
    # 3.00-3.75 wipe B->A | 3.75-6.00 hold A
    for i in range(n):
        t = i / FPS
        if t < 0.75:
            frame = fa
        elif t < 1.50:
            frame = wipe_frames(fa, fb, (t - 0.75) / 0.75)
        elif t < 3.00:
            frame = fb
        elif t < 3.75:
            frame = wipe_frames(fb, fa, (t - 3.00) / 0.75)
        else:
            frame = fa
        frame.save(frames_dir / f"f{i:04d}.png")
    mp4 = out / f"{piece_id}-version-reel-1080x1920.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
         "-i", str(frames_dir / "f%04d.png"), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
         "-movflags", "+faststart", "-an", str(mp4)],
        check=True,
    )
    fa.save(out / "poster-1080x1920.jpg", quality=JPEG_QUALITY)
    shutil.rmtree(frames_dir)
    return {
        "file": mp4.name, "width": W9, "height": H9, "fps": FPS,
        "duration_seconds": duration, "codec": "h264", "audio": "none",
    }


def make_story(out: Path, src: SourcePackage, avatar: Path | None, cfg: dict) -> dict:
    """9:16 assembly: recorded-ink reveal over a page, plus two loop slots.

    The background and photo layers are still-image stand-ins, not recordings.
    They are deliberately labelled provisional; the finished sample needs the
    author's Live Photo / video clips.
    """
    out.mkdir(parents=True, exist_ok=True)
    layers = out / "layers"
    layers.mkdir(parents=True, exist_ok=True)

    primary_blocks = src.version_blocks()
    rows = src.rows(primary_blocks)
    page_box = clamp_box(union_box(rows), 0.020, 0.020)
    page_crop = crop_norm(src.image, page_box)

    # background still: full-bleed, blurred scan (ordinary scan movement only)
    bg = fit_cover(page_crop, W9, H9).filter(ImageFilter.GaussianBlur(22))
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    bg = add_paper_wash(bg, 0.08)
    bg.save(layers / "00-background-provisional.jpg", quality=JPEG_QUALITY)

    # page card
    card = fit_contain(page_crop, W9 - 96, H9 - 366)
    card_x = (W9 - card.width) // 2
    card_y = (H9 - card.height) // 2
    page_layer = Image.new("RGBA", (W9, H9), (0, 0, 0, 0))
    page_layer.alpha_composite(card.convert("RGBA"), (card_x, card_y))
    page_layer.save(layers / "01-page-recorded-ink.png")

    # photo slot (top-right), transparent, clearly a slot in the assembly
    slot = Image.new("RGBA", (W9, H9), (0, 0, 0, 0))
    d = ImageDraw.Draw(slot)
    sw, sh = 372, 462
    sx, sy = W9 - sw - 74, 176
    d.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=28,
                        fill=(255, 255, 255, 24), outline=(40, 36, 30, 150), width=3)
    slot.save(layers / "02-photo-slot-empty.png")

    # composite preview frame (still) with technical slot visible only in QA
    preview = bg.copy()
    # page shadow
    sh_im, p = shadowed_card(card, pad=36, blur=18, opacity=92)
    preview.paste(sh_im, (card_x - p, card_y - p), sh_im)
    preview.paste(card, (card_x, card_y))
    if avatar and avatar.exists():
        chip = identity_chip(avatar, size=170, border=8)
        preview.paste(chip, (W9 - chip.width - 96, 204), chip)
    preview.save(out / "assembly-frame-provisional.jpg", quality=JPEG_QUALITY)

    # map line boxes to canvas
    px_scale = card.width / page_crop.width
    py_scale = card.height / page_crop.height
    norm_rows = []
    for r in rows:
        x0 = (r[2] - page_box[0]) * src.src_w
        y0 = (r[3] - page_box[1]) * src.src_h
        x1 = (r[4] - page_box[0]) * src.src_w
        y1 = (r[5] - page_box[1]) * src.src_h
        norm_rows.append((x0, y0, x1, y1))
    line_rects = []
    for (x0, y0, x1, y1) in norm_rows:
        line_rects.append((
            card_x + x0 * px_scale,
            card_y + y0 * py_scale,
            card_x + x1 * px_scale,
            card_y + y1 * py_scale,
        ))

    # 9 s = 4.5 s write-on + 4.5 s hold. Background and photo loops are declared
    # at 4.5 s and 3 s; the composite is the LCM, 9 s.
    duration = 9.0
    n = round(duration * FPS)
    frames_dir = out / "_frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    write_seconds = 4.5
    line_dur = write_seconds / max(1, len(line_rects))
    for i in range(n):
        t = i / FPS
        # background provisional drift (ordinary scan movement, not a clip)
        z = 1.0 + 0.018 * math.sin(2 * math.pi * t / duration)
        bw, bh = round(W9 * z), round(H9 * z)
        bframe = bg.resize((bw, bh), Image.Resampling.LANCZOS)
        bframe = bframe.crop(((bw - W9) // 2, (bh - H9) // 2,
                              (bw - W9) // 2 + W9, (bh - H9) // 2 + H9))
        # page mask: reveal the recorded ink line by line
        mask = Image.new("L", (W9, H9), 0)
        md = ImageDraw.Draw(mask)
        for j, (x0, y0, x1, y1) in enumerate(line_rects):
            start = j * line_dur
            if t < start:
                continue
            prog = min(1.0, (t - start) / max(0.01, line_dur * 0.88))
            if prog >= 1.0:
                md.rectangle([x0, y0, x1, y1], fill=255)
            else:
                md.rectangle([x0, y0, x0 + (x1 - x0) * prog, y1], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(1.1))
        frame = bframe.copy()
        pframe = page_layer.copy()
        # apply the reveal mask to the page's alpha
        alpha = pframe.getchannel("A")
        from PIL import ImageChops
        pframe.putalpha(ImageChops.multiply(alpha, mask))
        frame.paste(pframe, (0, 0), pframe)
        # photo slot outline, not a recorded clip
        frame.paste(slot, (0, 0), slot)
        frame.convert("RGB").save(frames_dir / f"f{i:04d}.png")

    mp4 = out / f"{cfg['piece_id']}-story-assembly-provisional-1080x1920.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
         "-i", str(frames_dir / "f%04d.png"), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "21", "-preset", "medium",
         "-movflags", "+faststart", "-an", str(mp4)],
        check=True,
    )
    poster = Image.open(frames_dir / "f0000.png").convert("RGB")
    poster.save(out / "poster-1080x1920.jpg", quality=JPEG_QUALITY)
    shutil.rmtree(frames_dir)

    spec = {
        "canvas": {"width": W9, "height": H9, "fps": FPS},
        "duration_seconds": duration,
        "layers": [
            {"order": 3, "name": "background", "kind": "clip slot",
             "intended_loop_seconds": 4.5, "supplied": False,
             "provisional": "still scan with slow drift; ordinary scan movement"},
            {"order": 2, "name": "page", "kind": "recorded handwriting",
             "intended_loop_seconds": 9.0, "supplied": True,
             "provisional": False,
             "method": "mask sweep over j.json line boxes; actual scan ink, not reconstructed strokes"},
            {"order": 1, "name": "photo", "kind": "clip slot",
             "intended_loop_seconds": 3.0, "supplied": False,
             "provisional": "empty rounded slot in the assembly preview"},
        ],
        "missing_clips": [
            "original Live Photo / video for the photo layer (3 s loop)",
            "original video/wallpaper loop for the background layer (4.5 s loop)",
        ],
        "artistic_decision": (
            "Reconstructed stroke animation is not produced. The write-on is a "
            "mask reveal of recorded scan ink; stroke tracing would be a new "
            "artistic treatment and needs the author's decision."
        ),
    }
    save_json(out / "assembly-spec.json", spec)
    return {
        "file": mp4.name, "spec": "assembly-spec.json",
        "width": W9, "height": H9, "fps": FPS, "duration_seconds": duration,
        "audio": "none", "finished": False,
    }


# --------------------------------------------------------------------------
# widget kit
# --------------------------------------------------------------------------

def widget_tile(im: Image.Image, w: int, h: int, pad=(0.04, 0.04)) -> Image.Image:
    box = clamp_box(union_box([(0, 0, 0, 0, 1, 1)]), 0, 0)  # full page
    crop = crop_norm(im, box)
    card = fit_cover(crop, w, h)
    canvas = page_canvas(w, h)
    # keep a paper margin so the handwriting does not touch the widget edge
    mx = round(w * pad[0])
    my = round(h * pad[1])
    card = fit_contain(card, w - 2 * mx, h - 2 * my)
    canvas.paste(card, ((w - card.width) // 2, (h - card.height) // 2))
    return canvas


def make_widget_kit(src: SourcePackage, out: Path, cfg: dict) -> dict:
    base = out / "widget"
    made = []

    def save_tile(name, im, w, h):
        p = base / "tiles" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        im.save(p, quality=JPEG_QUALITY, subsampling=1, optimize=True)
        made.append((str(p.relative_to(out)), w, h))

    same_block = cfg["cover_block"] == cfg["detail_block"]

    # 2x1 / wide: a line or a stanza, with paper margins. When the selected
    # version has a single block, one wide tile is enough; duplicating it under
    # two names would imply a variant that does not exist.
    wide_blocks = [("opening-line", cfg["cover_block"])]
    if not same_block:
        wide_blocks.append(("detail-line", cfg["detail_block"]))
    for label, block in wide_blocks:
        rows = src.rows([block])
        box = clamp_box(union_box(rows), 0.05, 0.05)
        crop = crop_norm(src.image, box)
        tile = fit_cover(crop, 1600, 760)
        save_tile(f"2x1/{label}.jpg", tile, 1600, 760)

    # 1x1: stanza detail
    square_blocks = [("detail", cfg["detail_block"])]
    if not same_block:
        square_blocks.append(("opening", cfg["cover_block"]))
    for label, block in square_blocks:
        rows = src.rows([block])
        box = clamp_box(union_box(rows), 0.06, 0.05)
        crop = crop_norm(src.image, box)
        tile = fit_cover(crop, 1080, 1080)
        save_tile(f"1x1/{label}.jpg", tile, 1080, 1080)

    # 2x2: page
    page_tile = render_page(src, None, canvas_size=(1080, 1080), margin=48)
    save_tile("2x2/page.jpg", page_tile, 1080, 1080)

    # wide: opening with deliberate negative space
    rows = src.rows([cfg["cover_block"]])
    box = clamp_box(union_box(rows), 0.08, 0.025)
    crop = crop_norm(src.image, box)
    tile = fit_contain(crop, 1600 - 96, 760 - 96)
    wide = page_canvas(1600, 760)
    wide.paste(tile, ((1600 - tile.width) // 2, (760 - tile.height) // 2))
    save_tile("wide/opening.jpg", wide, 1600, 760)

    readme = f"""# Widget kit — {cfg['piece_id']} ({cfg['page_id']})

Private, scan-based tiles for the Photos/album/widget path. **Not a public
downloadable and not cleared for distribution.** The archive source is
`{src.source_path.name}` ({src.src_w}×{src.src_h}); every tile is a crop of that
page. No AI-written copy is on any tile.

Tiles are square (1×1/2×2, 1080×1080), wide (2×1, 1600×760) and wide page
(1600×760). File names are technical only.

## Test the path on a device

1. Import the `tiles/` images into Photos.
2. Create an album (for example `T07 test — {cfg['piece_id']}`) and add the tiles.
3. On the home screen (or the Mac desktop), add the Photos widget.
4. Long-press / edit the widget and choose the album in the album picker.
5. Record whether the album appears, whether it advances through the tiles, and
   whether a **shared** album appears in the picker.
6. Delete the test album and the imported tiles afterwards.

Step 5 is the unresolved behavioural check. The macOS 26.7.2 Photos widget
extension advertises an album picker (`Album — Choose an album to shuffle
throughout the day`), but this kit has not tested a widget render or a shared
album.

## Clearance

{cfg['clearance_note']}
"""
    (base / "README.md").write_text(readme, encoding="utf-8")

    # A clearance note travels with the zip. The manifest cannot be inside the
    # zip because the manifest hashes the zip; refer to the manifest instead.
    (base / "CLEARANCE.txt").write_text(
        "STATUS: private test material; not cleared for publication or distribution.\n"
        "may_publish: false\n"
        "author_clearance: null\n"
        "The manifest that hashes this zip is one level above the kit output.\n"
        f"{cfg['clearance_note']}\n",
        encoding="utf-8",
    )

    # private zip
    zpath = base / f"{cfg['piece_id']}-widget-kit-private.zip"
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p, _, _ in made:
            arcname = p[len("widget/"):] if p.startswith("widget/") else p
            z.write(out / p, arcname=arcname)
        z.write(base / "README.md", arcname="README.md")
        z.write(base / "CLEARANCE.txt", arcname="CLEARANCE.txt")
    return {"tiles": made, "zip": str(zpath.relative_to(out))}


# --------------------------------------------------------------------------
# QA
# --------------------------------------------------------------------------

def phone_preview(im: Image.Image, width=390) -> Image.Image:
    h = round(im.height * width / im.width)
    return resample(im, (width, h))


def ink_metrics(src: SourcePackage, block_ids, card_height_px, canvas_w=W4,
                display_w=390, page_px_h=None, src_h=None):
    """Ink-box height on a 390 px display.

    ``page_px_h`` is the source height that the rendered card represents: the
    whole page for a full-page card, or the crop height for a cropped card.
    """
    rows = src.rows(block_ids)
    src_h = src_h or src.src_h
    if page_px_h is None:
        page_px_h = src_h
    scale = card_height_px / page_px_h
    disp = display_w / canvas_w
    vals = []
    for r in rows:
        ink = (r[5] - r[3]) * src_h * scale * disp
        vals.append(ink)
    if not vals:
        return {}
    vals.sort()
    return {
        "lines": len(vals),
        "min_ink_height_px_at_390": round(vals[0], 2),
        "median_ink_height_px_at_390": round(vals[len(vals) // 2], 2),
        "max_ink_height_px_at_390": round(vals[-1], 2),
    }


def ensure_vision_ocr() -> Path | None:
    swift = PRODUCTION_DIR / "tools" / "vision_ocr.swift"
    if not swift.exists():
        return None
    build = PRODUCTION_DIR / "tools" / ".build"
    build.mkdir(parents=True, exist_ok=True)
    binary = build / "visionocr"
    if not binary.exists() or binary.stat().st_mtime < swift.stat().st_mtime:
        try:
            subprocess.run(["swiftc", "-O", "-o", str(binary), str(swift)],
                           check=True, capture_output=True)
        except Exception as exc:
            print(f"warning: could not build Vision OCR: {exc}", file=sys.stderr)
            return None
    return binary


def ocr_words(binary: Path, image: Path) -> list[str]:
    out = subprocess.run([str(binary), str(image)], check=True,
                         capture_output=True, text=True).stdout
    return re.findall(r"[A-Za-z']+", out.lower())


def word_recall(expected: list[str], got: list[str]) -> float:
    exp = []
    for line in expected:
        exp.extend(re.findall(r"[A-Za-z']+", line.lower()))
    if not exp:
        return 0.0
    hit = 0
    pool = list(got)
    for w in exp:
        best = None
        best_r = 0.0
        for i, g in enumerate(pool):
            r = difflib.SequenceMatcher(None, w, g).ratio()
            if r > best_r:
                best_r, best = r, i
        if best is not None and best_r >= 0.80:
            hit += 1
            pool.pop(best)
    return round(hit / len(exp), 3)


def run_qa(src: SourcePackage, out: Path, still_paths: dict, cfg: dict) -> dict:
    binary = ensure_vision_ocr()
    qa_dir = out / "qa"
    (qa_dir / "phone-390").mkdir(parents=True, exist_ok=True)
    report = {
        "display_width_px": 390,
        "method": (
            "PIL ink-box geometry at a 390 px display width, plus Apple Vision "
            "OCR on the 390 px preview. Geometry is a proxy; physical-device "
            "review is still required."
        ),
        "ocr_note": (
            "Apple Vision accurate mode with language correction off. Cursive, "
            "faint or overlapping lines under-read, so recall is a lower bound "
            "on content legibility, not a publishability score."
        ),
        "readability_rule": (
            "Readable on a 390 px phone width when the smallest ink box is at "
            "least 8 px high; OCR recall is reported separately."
        ),
        "targets": {},
    }
    primary = src.version_blocks()
    later = cfg.get("later_version")
    later_size = None
    if later:
        later_size = Image.open(src._resolve(later["source"])).size

    def page_dims(is_later=False):
        return later_size if is_later else (src.src_w, src.src_h)

    def crop_px(block_ids, dims, pad):
        rows = src.rows(block_ids)
        box = clamp_box(union_box(rows), pad[0], pad[1])
        return ((box[2] - box[0]) * dims[0], (box[3] - box[1]) * dims[1])

    def line_card_height(block_ids, pad=(0.030, 0.020), max_w=W4 - 2 * MARGIN):
        w, h = crop_px(block_ids, page_dims(), pad)
        return min(H4 - 2 * MARGIN, (max_w / w) * h)

    def page_card_height(block_ids, max_w, max_h, pad=(0.012, 0.018),
                         is_later=False):
        w, h = crop_px(block_ids, page_dims(is_later), pad)
        return min(max_h, max_w / (w / h))

    def full_page_card_height(max_w, max_h):
        w, h = page_dims()
        return min(max_h, max_w / (w / h))

    specs = {}
    specs["cover-page"] = (primary, full_page_card_height(
        W4 - 2 * MARGIN, H4 - 2 * MARGIN), src.src_h, src.src_h)
    specs["cover-line"] = (
        [cfg["cover_block"]], line_card_height([cfg["cover_block"]]),
        crop_px([cfg["cover_block"]], page_dims(), (0.030, 0.020))[1], src.src_h,
    )
    specs["cover-stack"] = (
        primary,
        page_card_height(primary, W4 - 270, H4 - 196, pad=(0.020, 0.020)),
        crop_px(primary, page_dims(), (0.020, 0.020))[1], src.src_h,
    )
    specs["carousel-04-detail"] = (
        [cfg["detail_block"]],
        line_card_height([cfg["detail_block"]], pad=(0.025, 0.018),
                         max_w=W4 - 2 * 54),
        crop_px([cfg["detail_block"]], page_dims(), (0.025, 0.018))[1], src.src_h,
    )
    if later:
        specs["carousel-05-version"] = (
            later["blocks"],
            page_card_height(later["blocks"], W4 - 2 * MARGIN,
                             H4 - 2 * MARGIN, is_later=True),
            crop_px(later["blocks"], page_dims(True), (0.012, 0.018))[1],
            later_size[1],
        )

    for name, (blocks, card_h, page_px_h, src_h) in specs.items():
        p = out / "4x5" / f"{name}.jpg"
        if not p.exists():
            p = out / "carousel" / f"{name}.jpg"
        if not p.exists():
            continue
        im = Image.open(p)
        prev = phone_preview(im)
        prev.save(qa_dir / "phone-390" / f"{name}.jpg", quality=90)
        m = ink_metrics(src, blocks, card_h, page_px_h=page_px_h, src_h=src_h)
        m["geometry_readable_at_390"] = (
            m.get("min_ink_height_px_at_390", 0) >= 8
        )
        if binary:
            got = ocr_words(binary, qa_dir / "phone-390" / f"{name}.jpg")
            m["ocr_words"] = len(got)
            m["ocr_word_recall"] = word_recall(src.text(blocks), got)
        report["targets"][name] = m

    # contact sheet
    make_contact_sheet(out, still_paths, qa_dir)
    return report


def load_font(size):
    for p in ["/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/SFNS.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_contact_sheet(out: Path, still_paths: dict, qa_dir: Path):
    covers = ["cover-stack", "cover-page", "cover-line"]
    carousel = sorted(k for k in still_paths if k.startswith("carousel/"))
    cols = 4
    tw, th = 270, 338
    pad = 18
    label_h = 30
    rows = 1 + math.ceil(len(carousel) / cols)
    sheet = Image.new("RGB", (cols * (tw + pad) + pad,
                              rows * (th + label_h + pad) + pad + 40), (252, 251, 247))
    d = ImageDraw.Draw(sheet)
    f = load_font(16)
    d.text((pad, 10), "T07 private QA contact sheet — not for publication; technical labels only",
           fill=(40, 36, 30), font=load_font(18))
    for i, name in enumerate(covers):
        im = Image.open(out / "4x5" / f"{name}.jpg")
        im.thumbnail((tw, th))
        x = pad + i * (tw + pad)
        y = 48
        sheet.paste(im, (x, y))
        d.text((x, y + th + 4), f"{name} · 1080×1350", fill=(40, 36, 30), font=f)
    y0 = 48 + th + label_h + pad
    for i, key in enumerate(carousel):
        im = Image.open(out / key)
        im.thumbnail((tw, th))
        x = pad + (i % cols) * (tw + pad)
        y = y0 + (i // cols) * (th + label_h + pad)
        sheet.paste(im, (x, y))
        d.text((x, y + th + 4), Path(key).stem.replace("carousel-", ""),
               fill=(40, 36, 30), font=f)
    sheet.save(qa_dir / "contact-sheet.jpg", quality=90)


# --------------------------------------------------------------------------
# manifests
# --------------------------------------------------------------------------

def asset_entry(path: Path, base: Path, role: str, source_chain: list[str],
                clearance: str, extra=None) -> dict:
    im = Image.open(path)
    e = {
        "path": str(path.relative_to(base)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "width": im.width,
        "height": im.height,
        "role": role,
        "source_chain": source_chain,
        "clearance": clearance,
    }
    if extra:
        e.update(extra)
    return e


def media_entry(path: Path, base: Path, role: str, source_chain: list[str],
                clearance: str, extra=None) -> dict:
    e = {
        "path": str(path.relative_to(base)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "role": role,
        "source_chain": source_chain,
        "clearance": clearance,
    }
    if extra:
        e.update(extra)
    return e


def prune_stale(out: Path, cfg: dict) -> list[str]:
    """Remove generated files from an earlier config in the same export dir.

    Only kit-generated patterns are touched; author material such as a dropped-in
    Live Photo clip is left alone.
    """
    pid = cfg["piece_id"]
    removed = []
    expected_reel = f"{pid}-version-reel-1080x1920.mp4"
    expected_story = f"{pid}-story-assembly-provisional-1080x1920.mp4"
    patterns = [
        (out / "reel", "*-version-reel-1080x1920.mp4", {expected_reel}),
        (out / "story", "*-story-assembly-provisional-1080x1920.mp4", {expected_story}),
    ]
    for d, pat, keep in patterns:
        if not d.exists():
            continue
        for p in d.glob(pat):
            if p.name not in keep:
                p.unlink()
                removed.append(str(p.relative_to(out)))
    car = out / "carousel"
    if car.exists():
        expected = f"carousel-05-{'version' if cfg.get('later_version') else 'detail'}.jpg"
        for p in car.glob("carousel-05-*.jpg"):
            if p.name != expected:
                p.unlink()
                removed.append(str(p.relative_to(out)))
    tiles = out / "widget" / "tiles"
    if tiles.exists():
        same = cfg["cover_block"] == cfg["detail_block"]
        keep = {"tiles/2x1/opening-line.jpg", "tiles/1x1/detail.jpg",
                "tiles/2x2/page.jpg", "tiles/wide/opening.jpg"}
        if not same:
            keep |= {"tiles/2x1/detail-line.jpg", "tiles/1x1/opening.jpg"}
        for p in tiles.rglob("*.jpg"):
            rel = str(p.relative_to(out / "widget"))
            if rel not in keep:
                p.unlink()
                removed.append(str(p.relative_to(out)))
    return removed


def build_manifest(src: SourcePackage, out: Path, cfg: dict, stills: dict,
                   reel: dict, story: dict, widget: dict, qa: dict,
                   repo: Path) -> dict:
    clear = cfg["clearance"]
    entries = []
    for rel in stills:
        p = out / rel
        role = "still" if rel.startswith("4x5") else "carousel"
        entries.append(asset_entry(
            p, out, role,
            [f"page:{cfg['page_id']}", f"version:{cfg['version_id']}",
             f"source:{cfg['source']}"],
            clear["default"],
        ))
    for d, role in [(reel, "reel"), (story, "story")]:
        if not d:
            continue
        p = out / role / d["file"]
        entries.append(media_entry(
            p, out, role,
            [f"page:{cfg['page_id']}", f"version:{cfg['version_id']}",
             f"source:{cfg['source']}"],
            clear["motion"],
            {"width": d.get("width"), "height": d.get("height"),
             "duration_seconds": d.get("duration_seconds"),
             "audio": d.get("audio")},
        ))
    for rel, w, h in widget["tiles"]:
        p = out / rel
        entries.append(asset_entry(
            p, out, "widget-tile",
            [f"page:{cfg['page_id']}", f"version:{cfg['version_id']}",
             f"source:{cfg['source']}"],
            clear["widget"],
        ))
    zp = out / widget["zip"]
    entries.append({
        "path": widget["zip"], "sha256": sha256(zp), "bytes": zp.stat().st_size,
        "role": "downloadable-kit", "source_chain": [f"page:{cfg['page_id']}"],
        "clearance": clear["download"],
    })

    qa_path = out / "qa" / "readability.json"
    source_inputs = [dict(e) for e in cfg["source_inputs"]]
    for e in source_inputs:
        if e["path"].endswith("site/data/j.json"):
            e["sha256"] = src.j_sha
    report = {
        "schema": "t07.media-kit-manifest.v1",
        "generated_at": iso_now(),
        "kit_version": "t07-media-kit-v1",
        "source_revision": git_head(repo),
        "builder": {
            "kit_py_sha256": sha256(KIT_DIR / "kit.py"),
            "config_sha256": sha256(KIT_DIR / "config" / cfg["_config_name"]),
        },
        "candidate": {
            "piece_id": cfg["piece_id"],
            "version_id": cfg["version_id"],
            "page_id": cfg["page_id"],
            "version_blocks": src.version_blocks(),
            "pool_clearance": clear["pool"],
            "selection_provenance": cfg["selection_provenance"],
            "later_version": cfg.get("later_version"),
        },
        "source_inputs": source_inputs,
        "assets": entries,
        "clearance": {
            "schema": "versforms.release-clearance.v1",
            "status": "awaiting-author-and-evidence",
            "candidate": cfg["piece_id"],
            "candidate_provenance": cfg["selection_provenance"],
            "proposed_version_ids": [cfg["version_id"]],
            "public_whitelist_change_applied": False,
            "author_clearance": None,
            "filing_evidence": None,
            "shared_scan_resolution": cfg.get("shared_scan_resolution"),
            "withheld_metadata_clearance": None,
            "complete_technical_exclusion": False,
            "first_confirmed_post_date": None,
            "may_publish": False,
            "may_schedule_external_actions": False,
            "pool_clearance": clear["pool"],
            "per_asset": {
                "stills": clear["default"],
                "motion": clear["motion"],
                "widget_tiles": clear["widget"],
                "downloadable_kit": clear["download"],
                "identity": clear["identity"],
            },
        },
        "qa": qa,
        "missing": cfg["missing"],
        "substitution": {
            "config": cfg["_config_name"],
            "same_code_path": True,
            "second_piece_check": "production/tools/check_substitution.py",
        },
    }
    save_json(out / "manifest.json", report)
    write_manifest_md(out, report)
    save_json(qa_path, qa)
    return report


def write_manifest_md(out: Path, report: dict):
    c = report["candidate"]
    lines = [
        f"# {c['piece_id']} media kit — private manifest",
        "",
        f"Generated: {report['generated_at']}  ",
        f"Source revision: `{report['source_revision']}`  ",
        f"Kit: `{report['kit_version']}`  ",
        f"Candidate: `{c['piece_id']}` / `{c['version_id']}` / page `{c['page_id']}`  ",
        f"Pool: {c['pool_clearance']}  ",
        "",
        "**Status: awaiting author and evidence; `may_publish: false`.** This is a private kit. "
        "A green build or a Series label is not permission to publish.",
        "",
        "## Assets",
        "",
        "| asset | role | dimensions | bytes | sha256 | clearance |",
        "|---|---|---|---|---|---|",
    ]
    for e in report["assets"]:
        dims = f"{e.get('width','')}×{e.get('height','')}" if e.get("width") else "—"
        lines.append(
            f"| `{e['path']}` | {e['role']} | {dims} | {e['bytes']} | "
            f"`{e['sha256'][:16]}…` | {e['clearance']} |"
        )
    lines += [
        "",
        "## Clearance",
        "",
        f"- schema: `{report['clearance']['schema']}`",
        f"- status: `{report['clearance']['status']}`",
        f"- author clearance: `null`",
        f"- filing evidence: `null`",
        f"- shared scan: {report['clearance']['shared_scan_resolution']}",
        f"- complete technical exclusion: `false` (T03's 13 withheld page ids and PAL/HF metadata are outside this kit's scope)",
        f"- may publish: `false`",
        "",
        "## QA",
        "",
        f"- {report['qa']['method']}",
        "",
        "| target | lines | min ink px @390 | median ink px @390 | geometry readable | OCR word recall |",
        "|---|---|---|---|---|---|",
    ]
    for name, m in report["qa"]["targets"].items():
        lines.append(
            f"| `{name}` | {m.get('lines','')} | {m.get('min_ink_height_px_at_390','')} | "
            f"{m.get('median_ink_height_px_at_390','')} | "
            f"{'yes' if m.get('geometry_readable_at_390') else 'no'} | "
            f"{m.get('ocr_word_recall','not run')} |"
        )
    lines += ["", "## Missing", ""]
    for m in report["missing"]:
        lines.append(f"- {m}")
    lines += [
        "",
        "## Reproduction",
        "",
        "```sh",
        "python3 production/kit/kit.py --config production/kit/config/"
        + report["substitution"]["config"],
        "```",
        "",
        "The manifest is the authority for hashes and clearance state. Re-running after "
        "a source, crop, review, identity or clearance change invalidates this output.",
        "",
    ]
    (out / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--repo", default=str(DEFAULT_REPO))
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-motion", action="store_true",
                    help="skip the Reel and 9:16 encodes (stills/widgets only)")
    ap.add_argument("--no-ocr", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    cfg_path = Path(args.config).resolve()
    cfg = load_json(cfg_path)
    cfg["_config_name"] = cfg_path.name
    out = Path(args.out).resolve() if args.out else PRODUCTION_DIR / "exports" / cfg["piece_id"]
    out.mkdir(parents=True, exist_ok=True)

    src = SourcePackage(repo, cfg)
    avatar = None
    if cfg.get("identity"):
        avatar = (repo / cfg["identity"]["asset"]).resolve()
        if not avatar.exists():
            print(f"warning: identity asset missing: {avatar}", file=sys.stderr)
            avatar = None

    stills = render_still_set(src, out, avatar, cfg)
    print(f"stills: {len(stills)}")

    reel = {}
    story = {}
    if not args.no_motion:
        later = cfg.get("later_version")
        if later:
            b = render_version_page(src, later["page_id"], later["blocks"])
        else:
            b = stills["4x5/cover-page.jpg"]
        reel = make_reel(out / "reel", stills["4x5/cover-line.jpg"], b,
                         cfg["piece_id"])
        print("reel:", reel["file"])
        story = make_story(out / "story", src, avatar, cfg)
        print("story:", story["file"])

    widget = make_widget_kit(src, out, cfg)
    print(f"widget tiles: {len(widget['tiles'])}")

    qa = run_qa(src, out, stills, cfg)
    pruned = prune_stale(out, cfg)
    if pruned:
        print("pruned stale:", ", ".join(pruned))
    manifest = build_manifest(src, out, cfg, stills, reel, story, widget, qa, repo)
    print(f"manifest: {out / 'manifest.json'}")
    print(f"may_publish: {manifest['clearance']['may_publish']}")


if __name__ == "__main__":
    main()
