# B3 Checks (three thresholds)

All scripts import `b3_flow` via the relative path `..`, so they run from `scripts/` or any other directory.

| Script | Input | What it checks | Threshold |
|---|---|---|---|
| `check_links.py` | biz_data.json | offline recomputation of routes: box crossings / short last segments / isolated tasks / bidirectional ports / parallel overlaps | all hard items 0; independent overlaps ≤ 3 |
| `check_cxn.py` | output.pptx | connector types only line/c3/c4/custGeom, gluing at both ends, isolated tasks | half-glued 0, isolated 0, no non-connector shapes |
| `export_png.py` | output.pptx + directory | renders 2400×1350 PNGs via WPS COM | - (prerequisite for acceptance) |
| `check_arrow_px.py` | biz_data.json + PNG directory | ink width just outside the end of every link | invisible (< 4 px) = 0 |

Typical use (from the `scripts/` directory):

```bash
python qa/check_links.py biz_data.json
python qa/check_cxn.py   "../outputs/B3-End-to-End Value Streams (Resource Management).pptx"
python qa/export_png.py  "../outputs/B3-End-to-End Value Streams (Resource Management).pptx"  ../_png
python qa/check_arrow_px.py biz_data.json ../_png --offset 1
```

`--offset`: with an overview slide, PNG numbering starts at s2 for the first value stream, so use 1; without an overview slide use 0.

Exit code: 0 = thresholds passed, 2 = not passed (can be plugged into automation).

> Why not PDF: PDF renderers and WPS treat arrows of "zero-width connectors" differently;
> an arrow that looks fine in a PDF may point outwards in WPS. Acceptance only uses PNGs exported by WPS itself.
