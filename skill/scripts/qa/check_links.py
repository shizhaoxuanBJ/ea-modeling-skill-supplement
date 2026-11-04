# -*- coding: utf-8 -*-
"""B3 link check (offline recomputation, no rendering needed) -- thresholds of b3-flow-spec.md §8.

Usage:
  python check_links.py biz_data.json [--pages 1,2]

Metrics have two levels (spec §8):
  [hard threshold, must be 0] box crossings / last segment too short (<0.06") / isolated tasks / bidirectional ports
      bidirectional port = the same port of a node carries both an incoming and an outgoing link;
      it renders as "a line passing through the box edge" and is the case most easily mistaken for an outward arrow.
  [soft threshold, <=3 and visually confirmed] independent parallel overlaps / same-direction fan-out at one port
      same-direction fan-out (one in, many out; many in, one out) is part of the process semantics, so several links may share a port,
      but the shared trunk renders as one thick line; the specification requires at most 3 such cases.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import b3_flow as S

MIN_SEP = 0.09        # minimum visual distance between adjacent parallel lines (1.15 pt line width ~ 0.016")


def seg_hits_box(p1, p2, box, pad=0.02):
    """Same criterion as b3_flow._seg_hits: nearly orthogonal (<=0.012") counts as orthogonal; slightly skewed segments must not escape."""
    x0, y0 = box["x"] + pad, box["y"] + pad
    x1, y1 = box["x"] + box["w"] - pad, box["y"] + box["h"] - pad
    (ax, ay), (bx, by) = p1, p2
    if abs(ay - by) <= S.AX_TOL:
        if not (min(ay, by) < y1 and max(ay, by) > y0):
            return 0
        lo, hi = sorted((ax, bx))
        return 1 if (hi > x0 and lo < x1) else 0
    if abs(ax - bx) <= S.AX_TOL:
        if not (min(ax, bx) < x1 and max(ax, bx) > x0):
            return 0
        lo, hi = sorted((ay, by))
        return 1 if (hi > y0 and lo < y1) else 0
    return 0


def check_page(pi, pg):
    pg = S.norm_page(pg)
    pos, ys, xs = S.layout_nodes(pg)
    _, extra = S.terminal_boxes(pg, pos, ys)
    plan = S.link_plan(pg, pos, extra)
    lab = {nd["id"]: nd["text"].replace("\n", "")[:7] for nd in pg["nodes"]}

    segs, ports = [], {}
    for li, (a, b, kind, sa, sb, p, pts) in enumerate(plan):
        ports.setdefault((b, sb), []).append((a, b, "in"))
        ports.setdefault((a, sa), []).append((a, b, "out"))
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            if abs(x1 - x0) + abs(y1 - y0) < 0.25:
                continue
            anchor_seg = (i == 0 or i == len(pts) - 2)   # segment attached to a port
            if abs(x0 - x1) < 1e-6:
                segs.append(("V", x0, min(y0, y1), max(y0, y1), a, b, anchor_seg))
            elif abs(y0 - y1) < 1e-6:
                segs.append(("H", y0, min(x0, x1), max(x0, x1), a, b, anchor_seg))

    glue, fan = [], []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            d1, o1, lo1, hi1, a1, b1, anc1 = segs[i]
            d2, o2, lo2, hi2, a2, b2, anc2 = segs[j]
            if d1 != d2 or (a1, b1) == (a2, b2):
                continue
            if abs(o1 - o2) > MIN_SEP:
                continue
            if min(hi1, hi2) - max(lo1, lo2) < 0.12:
                continue
            share = ({a1, b1} & {a2, b2})
            rec = (d1, round(abs(o1 - o2), 3), "%s→%s" % (a1, b1), "%s→%s" % (a2, b2),
                   round(o1, 2), round(o2, 2))
            (fan if (share and (anc1 or anc2)) else glue).append(rec)

    two_way = []
    same_dir = []
    for k, v in ports.items():
        ins = [x for x in v if x[2] == "in"]
        outs = [x for x in v if x[2] == "out"]
        if ins and outs:
            two_way.append((lab.get(k[0], k[0]), k[1], len(ins), len(outs)))
        elif len(ins) > 1 or len(outs) > 1:
            same_dir.append((lab.get(k[0], k[0]), k[1], len(ins), len(outs)))

    short = [(a, b, round(S._seg_len(pts[-2], pts[-1]), 3))
             for a, b, kind, sa, sb, p, pts in plan if S._seg_len(pts[-2], pts[-1]) < 0.06]

    boxes = [dict(x=p["x"], y=p["y"], w=p["w"], h=p["h"]) for p in pos.values()]
    cross = []
    for a, b, kind, sa, sb, p, pts in plan:
        for ob in boxes:
            if any(seg_hits_box(pts[i], pts[i + 1], ob) for i in range(len(pts) - 1)):
                cross.append("%s→%s" % (a, b))
                break

    linked = set()
    for a, b in pg["links"]:
        linked.add(a)
        linked.add(b)
    iso = [lab.get(nd["id"], nd["id"]) for nd in pg["nodes"]
           if nd.get("kind", "act") != "doc" and nd["id"] not in linked]

    print("== p%d %s | links %d" % (pi + 1, pg["title"], len(plan)))
    print("   hard: box crossings %d | short last segment %d | isolated tasks %d | bidirectional ports %d"
          % (len(cross), len(short), len(iso), len(two_way)))
    print("   soft: independent overlaps %d | shared-trunk overlaps %d | same-direction fan-out ports %d"
          % (len(glue), len(fan), len(same_dir)))
    for r in cross[:6]:
        print("     crossing %s" % r)
    for r in short[:6]:
        print("     short last segment %s->%s %.3f" % r)
    for r in iso[:6]:
        print("     isolated task %s" % r)
    for r in two_way[:6]:
        print("     bidirectional port %s·%s (in %d out %d)" % r)
    for r in glue[:6]:
        print("     overlap %s gap %.3f %s / %s (%.2f vs %.2f)" % r)
    for r in fan[:6]:
        print("     shared trunk %s gap %.3f %s / %s (%.2f vs %.2f)" % r)
    for r in same_dir[:6]:
        print("     same-direction fan-out %s·%s (in %d out %d)" % r)
    return (len(cross), len(short), len(iso), len(two_way), len(glue), len(fan))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--pages", default="", help="check only these pages, e.g. 1,2")
    a = ap.parse_args()
    d = json.load(open(a.data, encoding="utf-8"))
    pages = d["b3"]["pages"]
    pick = [int(x) for x in a.pages.split(",") if x.strip()] or list(range(1, len(pages) + 1))
    t = [0] * 6
    for pi in pick:
        t = [x + y for x, y in zip(t, check_page(pi - 1, pages[pi - 1]))]
    print("\nTotal: box crossings %d | short last segment %d | isolated tasks %d | bidirectional ports %d == hard items" % tuple(t[:4]))
    print("      independent overlaps %d | shared-trunk overlaps %d == soft items (<=3 and visually confirmed)" % (t[4], t[5]))
    hard = tuple(t[:4]) == (0, 0, 0, 0)
    soft = t[4] <= 3
    print("Verdict: %s" % ("PASS" if hard and soft else
                       ("hard items FAIL" if not hard else "soft items over the limit; inspect visually")))
    sys.exit(0 if hard else 2)


if __name__ == "__main__":
    main()
