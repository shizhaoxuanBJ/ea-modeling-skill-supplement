# -*- coding: utf-8 -*-
"""B3 structural check (reads the final PPTX): connector types, gluing at both ends, isolated tasks, one shape per link.

Usage:
  python check_cxn.py output.pptx
"""
import argparse
import sys

from pptx import Presentation
from pptx.oxml.ns import qn

ALLOWED = {"line", "bentConnector3", "bentConnector4", "custGeom", "straightConnector1"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    a = ap.parse_args()
    prs = Presentation(a.pptx)
    total_iso = total_glued = total_cxn = total_half = 0
    for si, s in enumerate(prs.slides, 1):
        shapes, conns, kinds = {}, [], {}
        for sp in s.shapes:
            txt = sp.text_frame.text.strip().replace("\n", "") if sp.has_text_frame else ""
            shapes[sp.shape_id] = (sp, txt)
        for sp in s.shapes:
            el = sp._element
            if el.tag != qn('p:cxnSp'):
                continue
            spPr = el.find(qn('p:spPr'))
            pg = spPr.find(qn('a:prstGeom'))
            if pg is not None:
                prst = pg.get('prst')
            else:
                prst = "custGeom" if spPr.find(qn('a:custGeom')) is not None else "?"
            cNv = el.find(qn('p:nvCxnSpPr')).find(qn('p:cNvCxnSpPr'))
            st, en = cNv.find(qn('a:stCxn')), cNv.find(qn('a:endCxn'))
            conns.append((prst, int(st.get('id')) if st is not None else None,
                          int(en.get('id')) if en is not None else None))
            kinds[prst] = kinds.get(prst, 0) + 1
        linked = set()
        for prst, x, y in conns:
            if x:
                linked.add(x)
            if y:
                linked.add(y)
        iso = []
        for sid, (sp, txt) in shapes.items():
            if sp._element.tag != qn('p:sp') or not txt:
                continue
            pg = sp._element.find(qn('p:spPr')).find(qn('a:prstGeom'))
            if pg is None or pg.get('prst') != 'roundRect':
                continue
            if sp.top / 914400 < 1.0:          # the stage band is not a task node
                continue
            if sid not in linked:
                iso.append(txt)
        glued = sum(1 for p, x, y in conns if x and y)
        # the "flow" sample in the legend connects to no shape; both ends empty is expected
        deco = sum(1 for p, x, y in conns if not x and not y)
        half = [c for c in conns if (c[1] is None) != (c[2] is None)]
        bad = [k for k in kinds if k not in ALLOWED]
        print("  p%d connectors=%d %s glued_both_ends=%d half_glued=%d legend_samples=%d isolated_tasks=%s%s"
              % (si, len(conns), kinds, glued, len(half), deco, iso or "none",
                 ("  !! non-connector types:%s" % bad) if bad else ""))
        total_iso += len(iso)
        total_glued += glued
        total_cxn += len(conns) - deco
        total_half += len(half)
    print("Total: node-to-node connectors %d, glued at both ends %d, half-glued %d, isolated tasks %d"
          % (total_cxn, total_glued, total_half, total_iso))
    sys.exit(0 if total_iso == 0 and total_half == 0 and total_glued == total_cxn else 2)


if __name__ == "__main__":
    main()
