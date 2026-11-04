# B3 End-to-End Value-Stream Diagram · Design Specification v2.0

> Scope: business-architecture view B3 (an overview slide + one swimlane slide per value stream), industry-independent; fonts and header text come from the profile.
> The values in this specification come from six rounds of rework on the B3 diagrams of the project-management domain in the case project, and have since been verified in other domains (healthcare, resource management).
> The first five rounds only "added arrows and clearance"; the sixth round broke the user's complaint that the diagram was "messy" down into measurable indicators (parallel overlaps / bidirectional ports / too-short last segments) and drove each to zero.
> **Conclusion first: unreadable arrows are almost never caused by arrowheads being too small, but by "last segments that are too short" and "ports used for both incoming and outgoing links".**

Implementation: `scripts/b3_flow.py` (layout constant block = §2, `plan_link` = §5, `_nudge/_spread` = §7).

---

## 1. Slide structure (seven layers, bottom to top)

| Layer | Content | Notes |
|---|---|---|
| L1 background | master accent1 diagonal gradient + blue header band (0.669") | band = accent1@61% solid + gradient strip image + outer shadow |
| L2 stage band | pentagon (first) + chevrons (others), `4BACC6` fill, white text | overlap 0.18"; the last block must be squared off, otherwise its point overflows the canvas |
| L3 swimlanes | `FFFFEB` fill + `666666` outline; name bar `D9E8F8`/`0D6FB8`/`1F4E79`, 10.5 pt bold | lane = organizational unit, ordered by tier from top to bottom |
| L4 nodes | task = rounded rectangle, solid `4BACC6`, white text; document = folded-corner rectangle, white fill + `4BACC6` outline | tasks from 10.5 pt, documents from 10 pt, fitted to the box width |
| L5 links | 1.15 pt `9E3039`, triangle arrowhead `lg/med` | **one link = one connector**, really glued at both ends |
| L6 start/end | 0.175" dot `2E75B6` + dark blue outline, two-line 9 pt label | placed in the gutter reserved at the first/last stage |
| L7 legend | footer at 7.03", 10 pt `595959` | task / business object / start-end event / sequence flow |

Canvas 13.333 × 7.5 in (16:9).

---

## 2. Layout and grid (the values are the specification; change the layout only here)

| Constant | Value | Purpose | Rationale |
|---|---|---|---|
| `X0_LANE` | 1.628 | left edge of lanes | leaves 1.18 for the lane name bar |
| `W_LANE` | 11.35 | total lane width | right edge 12.978, leaving a 0.355 margin |
| `X_LABEL / W_LABEL` | 0.338 / 1.18 | lane name bar | fits two lines of 6 CJK characters |
| `BAND_Y / BAND_H` | 0.835 / 0.331 | stage band | aligned with the V11 reference layout |
| `LANE_Y0 → LANE_BOTTOM` | 1.241 → 6.94 | lane area | height 5.699 |
| `OVL` | 0.18 | overlap depth of stages | affects only the stage band, not the node area |
| `GUT` | 0.50 | gutter at the first/last stage | holds the 0.175 dot + 0.30 label block |
| `CH` | 0.28 | clearance between node columns of adjacent stages | vertical links run in this channel without touching either side |
| `GX` | 0.26 | clearance between two columns within a stage | two columns only when a bucket has > 3 nodes |
| `COL_MIN` | 0.62 | minimum column width | about 5 CJK characters at 8 pt; narrower squeezes the text |
| `NODE_H` | 0.33 | node height | one line at 10 pt + padding |
| `NODE_GAP` | 0.155 (fallback 0.145/0.135/0.125/0.115/0.105) | clearance between rows in a column | **at 0.105 a vertical link is only 0.10 long; the arrowhead fills it and neither shaft nor direction is visible** |

**Row pitch** `pitch = NODE_H + NODE_GAP = 0.485`.
**Stage width**: first satisfy "columns × COL_MIN + GX between columns + end allowances", then distribute the remainder by demand weight;
each inner boundary gives up `OVL/2 + CH/2` on both sides, so the clearance between neighbouring columns is exactly `CH`.
**Vertical**: lane height follows the lane's maximum number of parallel rows; when space runs out, `NODE_GAP` falls back step by step - **never shrink NODE_H**.

Node placement rules (`layout_nodes`):

1. Bucket by `(stage, lane)`; **two columns only when a bucket has more than 3 nodes** (otherwise lanes become too tall).
2. Documents go to one end of the bucket, whichever end (top or bottom) blocks fewer cross-lane vertical links -
   a document between two tasks blocks exactly the centre-axis link from task to task.
3. Document width = column width - 0.16, left-aligned, leaving a routing channel on the right;
   vertical links blocked by a document use this 0.14 gap and do not merge with the document border.
4. Font fitting: choose the largest candidate size at which the whole text fits the box (`fit_font`);
   measured usable width in a WPS rounded box is 0.11-0.13 smaller than the box, estimated as -0.12.

---

## 3. Shapes and colours

| Element | Shape | Fill | Outline | Text |
|---|---|---|---|---|
| Task | `roundRect` | `4BACC6` | none | white, 10.5 → 7.5 adaptive |
| Business object (document) | `foldedCorner` | `FFFFFF` | `4BACC6` 0.75 pt | `1F4E79` bold, 10 → 7.5 |
| Stage band | `pentagon` / `chevron` | `4BACC6` | black 0.75 pt | white bold 11.5/10.5/9.5 |
| Lane background | `rect` | `FFFFEB` | `666666` 0.75 pt | - |
| Lane name bar | `rect` | `D9E8F8` | `0D6FB8` 0.75 pt | `1F4E79` bold 10.5 |
| Sequence flow | connector | - | `9E3039` 1.15 pt | triangle arrowhead |
| Start/end event | `oval` | `2E75B6` | `0F2B5B` 1.1 pt | label `595959` 9 pt |

Fonts come from profile.branding (`font_latin` / `font_ea`); both must be written into the run properties (including the `a:ea` East Asian font, otherwise WPS falls back to SimSun).

---

## 4. Connector rules (one link is one shape)

### 4.1 Iron rules

- Use **exactly one connector** between two nodes; never assemble a bend from two or three straight lines:
  each piece then lacks an arrow, the last arrow is not glued to the target box, and the drawing falls apart when a node is moved.
- All segments are **horizontal or vertical**; no diagonals (diagonals make readers misjudge which box a line crosses).
- After drawing, connectors are **pushed below the nodes** (z-order) so that arrows do not cover text.

### 4.2 Four geometries (`kind`)

| kind | Shape | Use | Notes |
|---|---|---|---|
| `line` | `STRAIGHT` | adjacent nodes in the same row / column | 47 of 99 links in the reference case; no bends, longest shaft, easiest to read |
| `c3` | `bentConnector3` (H-V-H) | mainly horizontal, across columns | `adj1` = position of the vertical segment (0-1) |
| `c4` | `bentConnector4` (adj1=0 degenerates to V-H-V) | **vertically adjacent** nodes | `adj2` = position of the horizontal crossing; runs along the centre axis of both boxes, not around their sides |
| `cust` | `custGeom` explicit polyline | "zero-width / zero-height" pairs with identical x or y at both ends | see §6, zero-width trap |

### 4.3 Gluing (must be real gluing, not "looks connected")

Write `a:stCxn` / `a:endCxn` in `p:nvCxnSpPr/p:cNvCxnSpPr`, with `id` = the shape's `shape_id` and `idx` = connection-site index:

| Shape | top | left | bottom | right |
|---|---|---|---|---|
| rectangle / rounded rectangle / folded corner | 0 | 1 | 2 | 3 |
| ellipse (8 sites, counter-clockwise from the top) | 0 | 2 | 4 | 6 |

Once glued, links follow nodes when they are moved: the difference between a professional process diagram and a jigsaw.

---

## 5. Routing rules (`plan_link` scores and picks the best)

For each link, enumerate all candidates (exit side × entry side × bend position), score each and take the minimum:

```
s = box crossings × 0.8 + total polyline length × 0.02 + edge-hugging segments × 0.20 + port penalty + orientation penalty
```

| # | Rule | Implementation | Threshold / penalty |
|---|---|---|---|
| R1 | **No box crossing** | any hit discards the candidate (hard filter) | `hits > 0` → rejected |
| R2 | **No edge hugging** | a segment within 0.075" of a box edge with > 0.05" overlap counts as one hug | × 0.20 |
| R3 | **Exclusive ports** | in + out on the same port heavily penalized; several in or several out lightly penalized | in + out +3.0; same direction +0.25/+0.20 |
| R4 | **Prefer straight lines** | same row/column without obstacles | -0.55 |
| R5 | **Vertically adjacent pairs use the centre axis** | mainly vertical (`|dy| ≥ 0.22` and `|dy| ≥ 0.8|dx|`) forces bottom-out/top-in | `c4` -0.20; `c3` folding back along an edge +1.20 |
| R6 | **Limit detours** | without an elbow solution use a corridor: turn out 0.15 → vertical track → horizontal track → turn in; tracks use gap centre lines | total length ≤ 1.45 × Manhattan + 0.35; last segment ≥ 0.06 |
| R7 | **Corridors must be orthogonal** | rounded track coordinates leave a 0.0005" skew, which must be removed by `_snap` | see §6.2 |
| R8 | **No grazing** | a middle segment closer than 0.06" to any box counts as grazing, penalized × 1.2 | corridors prefer gap centre lines |

Besides R3 there is one **global repair**: if, after routing, a port still has both an incoming and an outgoing link,
a **cost comparison** is run - each side of the conflict "gives way" in turn (the port is disabled and the link re-routed), and the plan
that is better (bidirectional ports, defects, total length) is kept.

Early versions only "moved the outgoing link"; long back-links then occupied ports and pushed main links into large detours (in one measured case a direct
link became a 7" detour). With the comparison, `f2→f3` returned to a 3.7" straight line. **Rule: same-port conflicts are resolved by comparing total cost, not by a fixed choice.**

---

## 5.1 Start/end events also take part in avoidance

Start/end dots and their label blocks (e.g. "Start", "Resource pool optimization") were originally not obstacles; a corridor then ran
straight through a label block - a red line across the words, with the arrowhead inside the text.

Fix: `terminal_boxes()` adds dots and label blocks to the obstacles,
and **the QA scripts must call the same function** to obtain the geometry; otherwise the check results and the actual drawing use different coordinates.

---

## 6. Zero-width trap (the real cause of outward arrows)

**Symptom**: a small arrow pointing **outwards** on a link, or a link without any visible arrow.

**Cause**: when both anchors have the same x (both on left/right sides) or the same y, the bounding rectangle of the connector has zero width/height;
an elbow connector's polyline must stay inside that rectangle → the last segment has zero length → **the arrow direction is undefined**,
and WPS draws it according to the flip flags, pointing outwards. PDF renderers and the WPS editor treat this case differently,
which is why "it looks fine in the PDF but points outwards in WPS".

**Detection**: `_seg_len(pts[-2], pts[-1]) < 0.06`.

**Fix**: use a `cust` polyline - both ends turn out along the normal by `D=0.16`" into the gutter,
joined by a vertical/horizontal run; the last segment always has length and the arrow always points into the box.
`D` tries 0.16 / 0.20 / 0.12 in turn and takes the first that crosses no box.

> General lesson: **any geometry that relies on the last segment to carry the arrow must guarantee a last segment ≥ 0.06" (≈ 4.3 pt)**.

## 6.2 Skew trap (even harder to spot)

**Symptom**: a line "enters the left side of a box without an arrow and then disappears"; another piece of line appears on the right side of the box.
Zoomed in, both ends of the line are there, but the middle is hidden by the box.

**Cause**: corridor track coordinates come from `round(v, 3)` (e.g. 5.332), while port anchors are raw floats (5.33154).
The polyline therefore gets a **"horizontal" segment with Δ = 0.0005"**. Collision detection `_seg_hits` tested horizontality with `abs(dy) < 1e-6`,
did not recognize the segment as horizontal → returned "no hit" → the line ran through two boxes and was hidden by them.

**Fix (both parts are needed)**
1. `AX_TOL = 0.012`: `_seg_hits` / `_graze` treat segments with |Δ| ≤ 0.012 as orthogonal and test by interval overlap.
2. `_snap()`: corridor polylines are snapped to strict orthogonality before being returned, aligning the first segment to the start and the last to the end (anchors are not moved off their ports);
   after snapping, `_free` and the last-segment length are re-checked, and failing candidates are discarded.

> This and the zero-width trap are a pair: **zero width makes the last segment vanish (outward arrow); skew makes the whole line invisible (missing arrow)**.
> Both come from "floating-point coordinates + exact comparison"; think about tolerances before writing any geometric check.

## 6.3 Tracks must use gap centre lines

`_tracks()` originally used only fixed offsets of 0.13/0.10 outside the boxes, so corridors always hugged some box (clearance 0.02-0.03,
i.e. drawn on the border). Adding **the centre lines of the gaps between adjacent boxes** (one set vertical, one horizontal)
lets corridors pass "through the gap", equidistant from both boxes.

---

## 7. Parallel-track separation (`_nudge` / `_spread`)

Two parallel lines squeezed into one channel render as one thick line, and readers take them for one link.

| Means | Method | Constraints |
|---|---|---|
| `_nudge` | find pairs of parallel segments with gap < `MIN_SEP=0.095` and overlap > 0.15, and shift one by `+0.095/0.11/0.13/0.145`, trying both sides | **only middle segments not attached to a port are moved**; afterwards re-check: no box crossing, no zero-length segment, last segment still ≥ 0.10 |
| `_spread` | when a single shift is impossible (channel too narrow), **spread** the whole group of parallel lines in the channel evenly across the available width | after spreading, every segment must still pass "no box crossing + segment length ≥ 0.05 + last segment ≥ 0.10" |

Same-direction fan-out at one port (one in, many out; many in, one out) is part of the process semantics and may share a trunk;
shared trunks render as one thick line, so the specification allows at most 3 such cases, confirmed visually.

---

## 8. Acceptance thresholds

### 8.1 Offline check (`scripts/qa/check_links.py`, no rendering needed)

| Level | Indicator | Threshold |
|---|---|---|
| hard | box crossings | 0 |
| hard | last segment too short (< 0.06") | 0 |
| hard | isolated tasks (no link, documents excluded) | 0 |
| hard | bidirectional ports | 0 |
| soft | independent parallel overlaps | ≤ 3 |
| soft | shared-trunk overlaps (same port, same direction) | ≤ 3, confirmed visually |

### 8.2 Rendered acceptance (**must be rendered by WPS itself, not via PDF**)

```bash
python scripts/qa/export_png.py output.pptx png_out          # WPS COM: Slide.Export(..., "PNG", 2400, 1350)
python scripts/qa/check_arrow_px.py biz_data.json png_out     # pixel-level arrow check
```

`check_arrow_px.py` measures, 4/6/8 px outside the end of each link, the continuous ink width perpendicular to the line:
a plain line is about 2 px, an arrowhead base about 10 px; **< 4 px counts as an invisible arrow**.

> Why PNG: PDF and WPS render arrows of zero-width connectors differently,
> so acceptance on PDF lets outward arrows pass; only PNGs exported by WPS match what the user sees.

### 8.3 Structural acceptance (`scripts/qa/check_cxn.py`)

- all connectors are one of `line / bentConnector3 / bentConnector4 / custGeom` (no loose straight segments)
- 100% glued at both ends
- 0 isolated tasks per slide

---

## 9. Troubleshooting

| Symptom | Cause | How to locate | Fix |
|---|---|---|---|
| arrow points outwards | last segment of zero length (zero-width connector) | `last segment < 0.06` | `cust` polyline, D = 0.16 |
| line visible but no arrow | last segment too short (0.02-0.06); arrowhead fills it | as above + pixel arrow width | larger row gap / straight line / arrow `med→lg` |
| two lines merge into one | parallel gap < 0.095 | overlap items of `check_links` | `_nudge`; if that fails, `_spread` |
| line runs along a box edge | edge-hugging candidates not penalized enough | `graze` count | raise the hugging penalty from × 0.20 to × 0.55 (inside corridors) |
| line crosses a box | candidate blocked, fallback to default `c3` | crossing items of `check_links` | corridor detour + length limit |
| line stops at a box edge, arrow gone | **skewed segment** (0.0005") escaped collision detection; the box hides the line | zoom in: line on both sides, nothing in between | `AX_TOL` tolerance + `_snap` orthogonalization (§6.2) |
| arrow over text | start/end labels were not obstacles | look at the text next to "Start/End" | include `terminal_boxes` in avoidance (§5.1) |
| one line loops around half the slide | corridor without a length limit | total length / Manhattan ratio | ≤ 1.45 × Manhattan; exit towards the target |

---

## 10. Data conventions (the data already decides whether the diagram will look good)

1. **`stages` names = L1 names of the B1 execution layer**; compound stage names containing "→" raise a WARN.
2. **4-6 stages, 4-6 lanes, 15-25 nodes per slide**; more than 30 requires splitting (one main line per slide).
3. **The order of `links` is the skeleton order**: first direct same-row/same-column links and the main cross-lane chain, **back-links last**.
   Routing claims ports in this order, so the main chain gets good ports and back-links take the next best.
4. **Every task node except business objects has at least one link**. A missing link is tolerated -
   `ensure_connected` attaches it to the nearest upstream task in the same lane and prints a notice - but please fix the data accordingly.
5. **Do not put document nodes in the middle of a chain**: their position in the bucket is chosen by the program to block the fewest cross-lane links,
   but as a business rule keep a document on the same side as the task that produces it.
6. Balance long labels manually with `\n` (e.g. `On-site use\nissue and attendance`) instead of relying on automatic wrapping in the middle of a word.
7. Start/end events may be omitted; the program attaches them to the tasks with in-degree/out-degree 0 in the first/last stage.

---

## 11. Iteration loop (run it for every change to a diagram)

```
edit biz_data.json
   ↓
python scripts/qa/check_links.py biz_data.json     # all hard items must be 0; otherwise do not waste time looking at the diagram
   ↓
python scripts/generate_views.py --data ... --views b3
   ↓
python scripts/qa/export_png.py output.pptx png_out   # render with WPS
   ↓
inspect the PNGs (focus: arrow direction / thick merged lines / edge hugging)
   ↓
problem → locate the specific node pair → change the data (not the rendering code) or tune the §2 constants
```

**The order must not be reversed**: pass the offline thresholds first, then look at the diagram. Nine out of ten "messy" spots can be found as numbers in `check_links`.

---

## 12. Parameter summary (to change the layout, change only these)

```python
X0_LANE = 1.628 ; W_LANE = 11.35        # lane frame
OVL = 0.18 ; GUT = 0.50                 # stage overlap / end gutter
CH = 0.28 ; GX = 0.26                   # clearance between / within columns
COL_MIN = 0.62 ; NODE_H = 0.33          # column width / node height
NODE_GAP = 0.155                        # row clearance (reduce this first, not NODE_H)
MIN_SEP = 0.095                         # minimum distance between parallel lines
```

After changing any of them, rerun the §11 loop: the values are coupled
(e.g. with `NODE_GAP` below 0.13, vertical links become too short to show an arrow).
