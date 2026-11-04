# -*- coding: utf-8 -*-
"""Pixel-level arrow check: outside the end of every link, measure the ink width perpendicular to the line direction.

A plain line is about 2 px wide (at 2400 px slide width) and an arrowhead base about 10 px; a width < 4 px counts as an invisible arrow.
Must be run on PNGs exported by WPS (PDF rendering differs from WPS).

Usage:
  python check_arrow_px.py biz_data.json png_dir [--offset 1]
    --offset  : page offset (1 when there is an overview slide; s1.png is the overview)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import b3_flow as S
from PIL import Image

SC = 180.0                      # 2400px / 13.333in
LINE_PX = 1.15 * SC / 72.0      # line width in pixels


def isink(p):
    r, g, b = p[:3]
    return 90 < r < 220 and g < 115 and b < 130 and r - g > 50


def width_at(im, cx, cy, ux, uy, back):
    """Continuous ink width (pixels) perpendicular to dir, at back pixels behind the end point along -dir."""
    px, py = cx - ux * back, cy - uy * back
    px_p, py_p = -uy, ux
    n = 0
    for k in range(-10, 11):
        x = int(round(px + px_p * k))
        y = int(round(py + py_p * k))
        if 0 <= x < im.size[0] and 0 <= y < im.size[1] and isink(im.getpixel((x, y))):
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("pngdir")
    ap.add_argument("--offset", type=int, default=1)
    a = ap.parse_args()
    d = json.load(open(a.data, encoding="utf-8"))
    bad, checked = [], 0
    for pi, pg in enumerate(d["b3"]["pages"]):
        pg = S.norm_page(pg)
        pos, ys, xs = S.layout_nodes(pg)
        n = pi + 1 + a.offset
        f = os.path.join(a.pngdir, "s%d.png" % n)
        if not os.path.exists(f):
            print("  ! missing %s, skipping p%d" % (f, pi + 1))
            continue
        im = Image.open(f).convert("RGB")
        _, extra = S.terminal_boxes(pg, pos, ys)
        for x0, y0, kind, sa, sb, p, pts in S.link_plan(pg, pos, extra):
            (ax, ay), (bx, by) = pts[-2], pts[-1]
            L = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            if L < 1e-6:
                bad.append((pg["title"], x0, y0, "zero-length last segment"))
                continue
            ux, uy = (bx - ax) / L, (by - ay) / L
            cx, cy = int(bx * SC), int(by * SC)
            w = max(width_at(im, cx, cy, ux, uy, k) for k in (4, 6, 8))
            checked += 1
            if w < 4:
                bad.append((pg["title"], x0, y0, "arrow not visible, width %dpx" % w))
    print("checked %d arrows, %d not visible" % (checked, len(bad)))
    for r in bad[:12]:
        print("   ", r)
    sys.exit(0 if not bad else 2)


if __name__ == "__main__":
    main()
