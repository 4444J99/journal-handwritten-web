#!/usr/bin/env python3
"""Trace the author's supplied photograph into recolorable SVG reader marks.

This is a deterministic pixel-boundary trace, not a generative redraw. The
source photograph remains in the author's Library; only the selected marks
belong in the reader. Run with the original image and an output directory.
Pillow is the only non-standard dependency (already used by build_public.py).
"""

import argparse
from collections import defaultdict, deque
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageOps, __version__ as pillow_version


SOURCE_SHA256 = "e83fbf423fa1568f0f7a33303392e5b3308e4d577d1bb5bc6bec442cb17c4e89"
MARKS = {
    "menu": {"crop": [625, 1170, 775, 1350], "luma_below": 96,
             "rotation_degrees": -78, "large_components": 3},
    "crown": {"crop": [340, 425, 620, 660], "luma_below": 132,
              "rotation_degrees": -29, "large_components": 1,
              "exclude_rectangles": [[340, 610, 375, 660]]},
}


def components(pixels):
    """Return eight-connected components without changing their pixels."""
    remaining = set(pixels)
    result = []
    neighbors = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 if dx or dy]
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        found, queue = {start}, deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in neighbors:
                p = (x + dx, y + dy)
                if p in remaining:
                    remaining.remove(p)
                    found.add(p)
                    queue.append(p)
        result.append(found)
    return sorted(result, key=lambda group: (-len(group), min(group)))


def boundary_loops(pixels):
    """Trace exact square-pixel boundaries, including white holes."""
    edges = defaultdict(set)
    for x, y in pixels:
        if (x, y - 1) not in pixels:
            edges[(x, y)].add((x + 1, y))
        if (x + 1, y) not in pixels:
            edges[(x + 1, y)].add((x + 1, y + 1))
        if (x, y + 1) not in pixels:
            edges[(x + 1, y + 1)].add((x, y + 1))
        if (x - 1, y) not in pixels:
            edges[(x, y + 1)].add((x, y))
    loops = []
    while edges:
        start = min(edges)
        current, previous, loop = start, None, [start]
        while True:
            candidates = edges[current]
            if previous is None or len(candidates) == 1:
                following = min(candidates)
            else:
                dx, dy = current[0] - previous[0], current[1] - previous[1]
                def turn(point):
                    nx, ny = point[0] - current[0], point[1] - current[1]
                    return (dx * ny - dy * nx, dx * nx + dy * ny, point)
                following = max(candidates, key=turn)
            candidates.remove(following)
            if not candidates:
                del edges[current]
            previous, current = current, following
            if current == start:
                break
            loop.append(current)
        # Removing collinear vertices preserves the traced boundary exactly.
        simple = []
        for i, point in enumerate(loop):
            before, after = loop[i - 1], loop[(i + 1) % len(loop)]
            a = point[0] - before[0], point[1] - before[1]
            b = after[0] - point[0], after[1] - point[1]
            if a[0] * b[1] != a[1] * b[0]:
                simple.append(point)
        if len(simple) >= 3:
            loops.append(simple)
    return loops


def svg_for(name, pixels, angle):
    theta = math.radians(angle)
    cosine, sine = math.cos(theta), math.sin(theta)
    rotated = [[(x * cosine - y * sine, x * sine + y * cosine)
                for x, y in loop] for loop in boundary_loops(pixels)]
    points = [point for loop in rotated for point in loop]
    left, top = min(p[0] for p in points), min(p[1] for p in points)
    width = max(p[0] for p in points) - left + 6
    height = max(p[1] for p in points) - top + 6
    paths = []
    for loop in rotated:
        commands = [f"{x-left+3:.2f},{y-top+3:.2f}" for x, y in loop]
        paths.append("M" + "L".join(commands) + "Z")
    data = "".join(paths)
    viewbox = f"0 0 {width:.2f} {height:.2f}"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" '
           f'fill="currentColor" role="img" aria-label="Author-drawn {name}">\n'
           f'  <path fill-rule="evenodd" d="{data}"/>\n</svg>\n')
    symbol = (f'<symbol id="author-{name}-mark" viewBox="{viewbox}">'
              f'<path fill="currentColor" fill-rule="evenodd" d="{data}"/></symbol>')
    return svg, symbol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if source_hash != SOURCE_SHA256:
        raise SystemExit("Source differs from the author's supplied photograph; inspect before tracing.")
    original = Image.open(args.source)
    image = ImageOps.exif_transpose(original).convert("RGB")
    if image.size != (1080, 1920):
        raise SystemExit("Unexpected oriented source dimensions.")
    args.output.mkdir(parents=True, exist_ok=True)
    receipt = {"source_sha256": source_hash, "source_orientation": original.getexif().get(274),
               "normalized_size": list(image.size), "pillow_version": pillow_version,
               "method": "Exact thresholded pixel boundaries; no generative redraw or curve smoothing.",
               "marks": {}}
    symbols = []
    for name, settings in MARKS.items():
        crop = image.crop(settings["crop"])
        pixels = set()
        for y in range(crop.height):
            for x in range(crop.width):
                source_x, source_y = x + settings["crop"][0], y + settings["crop"][1]
                if any(x0 <= source_x < x1 and y0 <= source_y < y1
                       for x0, y0, x1, y1 in settings.get("exclude_rectangles", [])):
                    continue  # Neighboring lettering, outside the crown.
                red, green, blue = crop.getpixel((x, y))
                luma = (2126 * red + 7152 * green + 722 * blue) / 10000
                # Exclude the colored under-marks as well as the pale paper/grid.
                if luma < settings["luma_below"] and max(red, green, blue) - min(red, green, blue) < 45:
                    pixels.add((x, y))
        groups = components(pixels)
        large = [group for group in groups if len(group) >= 100]
        if len(large) != settings["large_components"]:
            raise SystemExit(f"{name}: unexpected major components: {[len(g) for g in groups[:12]]}")
        retained = [group for group in groups if len(group) >= 8]
        pixels = set().union(*retained)
        svg, symbol = svg_for(name, pixels, settings["rotation_degrees"])
        output = args.output / f"author-{name}.svg"
        output.write_text(svg)
        symbols.append(symbol)
        receipt["marks"][name] = {**settings, "chroma_below": 45, "minimum_component_pixels": 8,
                                  "retained_component_pixels": [len(g) for g in retained],
                                  "svg_sha256": hashlib.sha256(svg.encode()).hexdigest()}
    (args.output / "author-marks-symbols.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><defs>' + "".join(symbols) + '</defs></svg>\n')
    (args.output / "trace-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
