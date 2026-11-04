# -*- coding: utf-8 -*-
"""B3 end-to-end value-stream diagram engine (industry-agnostic; layout derived from an earlier client template, V11; fonts and header text come from the profile).

One value stream = 1 slide: a stage band (pentagon/chevron arrows) x organizational swimlanes; nodes are placed automatically on the (stage, lane) grid;
each link is drawn as **one** elbow or straight connector from port to port, glued at both ends; plan_link scores candidate routes and picks the best.

Design specification: `b3-flow-spec.md` in the skill root. This file maps one-to-one onto it:
  · layout constant block = spec §2 value table (change the layout here only)
  · plan_link / _corridor_pts = routing rules in spec §5
  · _nudge / _spread = parallel-track separation in spec §7
  · ensure_connected = "no dangling task" fallback in spec §10
  · after generation, scripts/qa/check_*.py must pass the thresholds (spec §8)

Data section (the b3 part of biz_data.json):
  overview.rows[{name,trigger,stages,customer,value}]  -> overview table
  pages[{title, subtitle, chain, stages{names,weights}|[names], lanes[], start/end,
         nodes[{id,stage,lane,text,kind}], links[[a,b]], legend}]
  start/end are optional: if omitted they attach to the row of the first/last stage node, labelled "Start"/"Delivered".
"""
import math
import os
import sys

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

# ---------- specification colour palette ----------
C_BRAND   = RGBColor(0x0D, 0x6F, 0xB8)
C_INK     = RGBColor(0x1F, 0x4E, 0x79)
C_TITLE   = RGBColor(0x0F, 0x2B, 0x5B)
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_TEAL    = RGBColor(0x4B, 0xAC, 0xC6)
C_TEAL_LN = RGBColor(0x4B, 0xAC, 0xC6)
C_LANE_BG = RGBColor(0xFF, 0xFF, 0xEB)
C_LANE_LN = RGBColor(0x66, 0x66, 0x66)
C_LANE_HD = RGBColor(0xD9, 0xE8, 0xF8)
C_FLOW    = RGBColor(0x9E, 0x30, 0x39)
C_GRAY    = RGBColor(0x59, 0x59, 0x59)
C_LGRAY   = RGBColor(0x7F, 0x7F, 0x7F)
C_TBL_HDR = RGBColor(0x0D, 0x6F, 0xB8)
C_ROW_1   = RGBColor(0xAF, 0xDC, 0xF8)
C_ROW_N   = RGBColor(0xF2, 0xF7, 0xFC)
C_CELL_LN = RGBColor(0x9D, 0xC3, 0xE6)
C_NOTE_BG = RGBColor(0xF7, 0xFA, 0xFD)

import bizprofile as BP
FONT = "微软雅黑"      # Microsoft YaHei; overwritten by generate_views.apply_profile()
EA_FONT = "微软雅黑"  # Microsoft YaHei (East Asian font name)
SW, SH = 13.333, 7.5

# ---------- layout constants (matched to measured V11 coordinates) ----------
X0_LANE = 1.628          # left edge of lanes (V11 used 1.75 on the first slide and 1.628 elsewhere; the narrower value leaves room for labels)
W_LANE  = 11.35          # lane width
X_LABEL = 0.338          # lane name bar
W_LABEL = 1.18
OVL     = 0.18           # overlap depth of stage pentagons (affects only the top stage band, not the node area)
GUT     = 0.50           # gutter at the first/last stage (holds the start/end dots and their labels)
NODE_H  = 0.33
NODE_GAP = 0.155         # vertical clearance between rows in a column (row pitch = NODE_H + NODE_GAP = 0.485)
                         # at 0.105 a vertical link is only 0.10 long; the arrowhead fills the segment and neither shaft nor direction is visible
CH      = 0.28           # routing channel between node columns of adjacent stages (clearance, not centre distance)
GX      = 0.26           # routing channel between two node columns within the same stage
COL_MIN = 0.62           # minimum width of a single node column (about 5-6 CJK characters at 8 pt)
BAND_Y  = 0.835          # stage band (matched to V11)
BAND_H  = 0.331
LANE_Y0 = 1.241          # top of the first lane
LANE_BOTTOM = 6.94       # bottom limit of the lanes
LEGEND_Y = 7.03


def new_prs():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    # theme accent1 aligned with V11 (026CD4) so schemeClr gradients resolve to the same blue
    try:
        theme = prs.slide_masters[0].part.part_related_by(
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme")
        xml = theme.blob.decode("utf-8")
        xml = xml.replace("<a:accent1><a:srgbClr val=\"4472C4\"/></a:accent1>",
                          "<a:accent1><a:srgbClr val=\"026CD4\"/></a:accent1>")
        theme._blob = xml.encode("utf-8")
    except Exception:
        pass
    return prs


# Page header band (matched to the V11 slideLayout1):
#   (1) bottom: master accent1 diagonal gradient (alpha 0 -> 43%)
#   (2) band: solid accent1 at 61% alpha, full width x 0.669", with blue outer shadow
#   (3) on top: gradient strip image (accent1 lightened 40% -> bg1), full width x 0.669"
BG_XML = (
    '<p:bg xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    '<p:bgPr><a:gradFill flip="none" rotWithShape="1"><a:gsLst>'
    '<a:gs pos="21000"><a:schemeClr val="accent1">'
    '<a:lumMod val="20000"/><a:lumOff val="80000"/><a:alpha val="0"/></a:schemeClr></a:gs>'
    '<a:gs pos="100000"><a:schemeClr val="accent1">'
    '<a:lumMod val="20000"/><a:lumOff val="80000"/><a:alpha val="43000"/></a:schemeClr></a:gs>'
    '</a:gsLst><a:lin ang="8100000" scaled="1"/><a:tileRect/></a:gradFill>'
    '<a:effectLst/></p:bgPr></p:bg>'
)

BANNER_H = 0.669          # height of the header band (612140 EMU)


def apply_bg(slide, prs):
    """Inject the V11-style page header band (master gradient + blue overlay bar + gradient strip image)."""
    from pptx.oxml import parse_xml
    from PIL import Image, ImageDraw
    import io

    # (1) master gradient background
    cSld = slide._element.find(qn('p:cSld'))
    old = cSld.find(qn('p:bg'))
    if old is not None:
        cSld.remove(old)
    cSld.insert(0, parse_xml(BG_XML))

    # (2) blue overlay bar (accent1 @61%) with outer shadow
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                 Inches(SW), Inches(BANNER_H))
    bar.line.fill.background()
    bar.shadow.inherit = False
    spPr = bar._element.spPr
    fill = spPr.find(qn('a:solidFill'))
    if fill is not None:
        spPr.remove(fill)
    fill = parse_xml(
        '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:schemeClr val="accent1"><a:alpha val="61000"/></a:schemeClr></a:solidFill>')
    spPr.insert(list(spPr).index(spPr.find(qn('a:prstGeom'))) + 1, fill)
    eff = parse_xml(
        '<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:outerShdw blurRad="50800" dist="38100" dir="2700000" algn="tl" rotWithShape="0">'
        '<a:srgbClr val="036DD6"><a:alpha val="40000"/></a:srgbClr></a:outerShdw></a:effectLst>')
    for e in spPr.findall(qn('a:effectLst')):
        spPr.remove(e)
    spPr.append(eff)
    bar.text_frame.text = ""

    # (3) gradient strip image: dark to slightly lighter from left to right, imitating V11's three stacked layers
    cache = getattr(apply_bg, "_cache", None)
    if cache is None:
        W, H = 1600, 90
        im = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(im)
        for x in range(W):
            t = x / float(W - 1)
            # left (2,88,190) -> right (22,112,218), dark blue overall
            d.line([(x, 0), (x, H)],
                   fill=(int(2 + 20 * t), int(88 + 24 * t), int(190 + 28 * t)))
        cache = io.BytesIO()
        im.save(cache, format="PNG")
        cache.seek(0)
        apply_bg._cache = cache
    pic = slide.shapes.add_picture(apply_bg._cache, 0, 0, Inches(SW), Inches(BANNER_H))
    # push the picture below the band (lowest z-order, but above the background)
    tree = slide.shapes._spTree
    tree.remove(pic._element)
    tree.insert(list(tree).index(bar._element) + 1, pic._element)


class Tk:
    def __init__(self, slide, prs, d=None):
        self.d = d or {}
        self.slide = slide
        self.prs = prs
        self.ids = {}                 # node id -> shape_id (for gluing connectors)

    def _font(self, run, size, bold=False, color=C_INK):
        f = run.font
        f.size = Pt(size)
        f.bold = bold
        f.name = FONT
        f.color.rgb = color
        rPr = run._r.get_or_add_rPr()
        ea = rPr.find(qn('a:ea'))
        if ea is None:
            ea = rPr.makeelement(qn('a:ea'), {})
            rPr.append(ea)
        ea.set('typeface', EA_FONT)

    def text(self, x, y, w, h, s, size, bold=False, color=C_INK,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, wrap=True, ls=None,
             ml=0.02, mt=0.005):
        tb = self.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = wrap
        tf.margin_left = tf.margin_right = Inches(ml)
        tf.margin_top = tf.margin_bottom = Inches(mt)
        tf.vertical_anchor = anchor
        for i, ln in enumerate(str(s).split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            if ls:
                p.line_spacing = ls
            r = p.add_run()
            r.text = ln
            self._font(r, size, bold, color)
        return tb

    def box(self, x, y, w, h, s, size, fill, line=None, lnw=0.75, fc=C_INK,
            bold=False, shape=MSO_SHAPE.RECTANGLE, align=PP_ALIGN.CENTER,
            wrap=True, ml=0.01, mt=0):
        sp = self.slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill is None:
            sp.fill.background()
        else:
            sp.fill.solid()
            sp.fill.fore_color.rgb = fill
        if line is None:
            sp.line.fill.background()
        else:
            sp.line.color.rgb = line
            sp.line.width = Pt(lnw)
        sp.shadow.inherit = False
        tf = sp.text_frame
        tf.word_wrap = wrap
        tf.margin_left = tf.margin_right = Inches(ml)
        tf.margin_top = tf.margin_bottom = Inches(mt)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        lines = str(s).split("\n") if str(s) else [""]
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run()
            r.text = ln
            self._font(r, size, bold, fc)
        return sp

    def seg(self, x1, y1, x2, y2, head=False, color=C_FLOW, w=1.1):
        ln = self.slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                             Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        ln.line.color.rgb = color
        ln.line.width = Pt(w)
        ln.shadow.inherit = False
        if head:
            lnPr = ln.line._get_or_add_ln()
            lnPr.append(lnPr.makeelement(qn('a:tailEnd'),
                                         {'type': 'triangle', 'w': 'med', 'len': 'med'}))
        return ln

    def mark_node(self, el):
        if not hasattr(self, "_first_node"):
            self._first_node = el

    def put_behind_nodes(self, els):
        """Insert the connector before the first node so that nodes are drawn above links."""
        if not els or getattr(self, "_first_node", None) is None:
            return
        tree = self.slide.shapes._spTree
        idx = list(tree).index(self._first_node)
        for k, el in enumerate(els):
            tree.remove(el)
            tree.insert(idx + k, el)

    def page_head(self, domain, series, view_title, sub="", d=None):
        # dark blue header band: title in white (as in V11), series/domain label at top right
        self.text(8.9, 0.155, 3.95, 0.26, BP.T(self.d, "head_right", series=series, domain=domain),
                  9, False, RGBColor(0xDC, 0xEA, 0xFB), align=PP_ALIGN.RIGHT)
        fs = 16
        for fs in (16, 15, 14, 13, 12, 11):
            if _tw(view_title) * fs * 1.05 / 72.0 <= 8.4:
                break
        self.text(0.46, 0.150, 8.6, 0.40, view_title, fs, True, C_WHITE)


def _auto(pg, nstage, nnode, nlanes):
    return None


# ================= stage band =================
def stage_widths(names):
    """Stage widths: first satisfy each stage's minimum column width, then distribute the remainder by demand weight.

    Each inner boundary gives up OVL/2 + CH/2 on both sides, so the clearance between neighbouring node columns = CH;
    the first and last stages give up GUT for the start/end dots.
    """
    n = len(names)
    total = W_LANE + (n - 1) * OVL
    cols = []
    for i in range(n):
        il = GUT if i == 0 else OVL / 2 + CH / 2
        ir = GUT if i == n - 1 else OVL / 2 + CH / 2
        cols.append((il, ir))
    kinds = stage_cols.get(id(names)) or stage_cols.get(tuple(names)) or [1] * n
    dem = [k * COL_MIN + (k - 1) * GX + il + ir
           for k, (il, ir) in zip(kinds, cols)]
    spare = total - sum(dem)
    if spare < 0:                    # extreme crowding: scale down proportionally to fit
        k = total / sum(dem)
        dem = [d * k for d in dem]
        spare = 0
    wsum = float(sum(dem))
    ws = [d + spare * d / wsum for d in dem]
    xs, x = [], X0_LANE
    for w in ws:
        xs.append((x, w))
        x += w - OVL
    return xs


stage_cols = {}


def draw_stage_band(tk, stages, xs, y=BAND_Y, h=BAND_H):
    """First block is a pentagon, the rest are chevrons; the last block is not pointed so it does not overflow."""
    n = len(stages["names"])
    fs_all = 11.5
    for i, name in enumerate(stages["names"]):
        for s_ in (11.5, 11, 10.5, 10, 9.5, 9):
            if len(name) * 0.6 * s_ / 72.0 <= xs[i][1] - 0.45 or s_ == 9:
                fs_all = min(fs_all, s_)
                break
    for i, name in enumerate(stages["names"]):
        x, w = xs[i]
        shape = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
        last = (i == n - 1)
        fs = fs_all
        tk.box(x, y, w, h, name, fs, C_TEAL, line=RGBColor(0, 0, 0), lnw=0.75,
               fc=C_WHITE, bold=True,
               shape=MSO_SHAPE.RECTANGLE if last else shape)


# ================= swimlanes =================
def lane_heights(lanes, rows_needed, total=LANE_BOTTOM - LANE_Y0, min_h=0.55, gap=None):
    """Allocate lane heights by each lane's maximum number of parallel rows: first guarantee row spacing, then share the remainder by row count."""
    n = len(lanes)
    req = [max(1, r) for r in rows_needed]
    gap = NODE_GAP if gap is None else gap
    pitch = NODE_H + gap
    PAD = 0.13                       # total top + bottom padding of a lane
    need = [max(min_h, r * pitch - gap + PAD) for r in req]
    s = sum(need)
    if s > total:                    # extreme case: scale down proportionally (should not happen normally)
        k = total / s
        need = [b * k for b in need]
        print("  ! lane height insufficient, scaled proportionally by %.3f" % k)
    else:
        spare = total - s
        wsum = float(sum(req))
        need = [b + spare * (r / wsum) for b, r in zip(need, req)]
    ys, y = [], LANE_Y0
    for b in need:
        ys.append((y, b))
        y += b
    return ys


def draw_lanes(tk, lanes, ys):
    for i, (label, (y, h)) in enumerate(zip(lanes, ys)):
        tk.box(X0_LANE, y, W_LANE, h, "", 7, C_LANE_BG, line=C_LANE_LN, lnw=0.75)
        tk.box(X_LABEL, y + 0.02, W_LABEL, h - 0.04, label, 10.5, C_LANE_HD,
               line=C_BRAND, lnw=0.75, fc=C_INK, bold=True)


# ================= data normalization =================
def norm_page(pg):
    """Normalize the legacy format (stages as a list of strings, no start/end) into this engine's structure; returns a new dict (modified in place)."""
    st = pg.get("stages")
    if isinstance(st, (list, tuple)):
        pg["stages"] = {"names": list(st)}
    st = pg["stages"]
    if not st.get("weights"):
        # without manual weights, width follows the stage's maximum stacked rows: stages with more rows (e.g. execution) become wider
        rows = {}
        for nd in pg["nodes"]:
            rows.setdefault(nd["stage"], {}).setdefault(nd["lane"], 0)
            rows[nd["stage"]][nd["lane"]] += 1
        w = []
        for i in range(len(st["names"])):
            per = rows.get(i, {})
            r = max([math.ceil(c / 2.0) if c > 3 else c for c in per.values()] + [1])
            w.append(min(2.2, max(1.0, r * 0.95)))
        st["weights"] = w
    for nd in pg["nodes"]:
        nd.setdefault("kind", "act")
    pg.setdefault("subtitle", "")
    pg.setdefault("chain", "")
    return pg


# ================= node layout =================
def layout_nodes(pg):
    """Bucket nodes by (stage, lane); buckets with many nodes are split into two staggered columns. Returns coordinates and occupied rows."""
    stages = pg["stages"]
    lanes = pg["lanes"]
    names = stages["names"]
    buckets = {}
    for nd in pg["nodes"]:
        buckets.setdefault((nd["stage"], nd["lane"]), []).append(nd)

    n = len(names)
    # columns needed per stage: buckets with more than 3 nodes use two columns
    kcols = []
    for i in range(n):
        k = 1
        for (si, li), lst in buckets.items():
            if si == i and len(lst) > 3:
                k = 2
        kcols.append(k)
    stage_cols[tuple(names)] = kcols
    xs = stage_widths(names)

    rows = {}
    for (si, li), lst in buckets.items():
        rows[li] = max(rows.get(li, 0), math.ceil(len(lst) / (2 if len(lst) > 1 else 1)) if len(lst) > 3 else len(lst))
    rows_needed = [rows.get(li, 1) for li in range(len(lanes))]
    # row clearance: as large as fits (the arrow shaft of a vertical link depends entirely on it)
    total_h = LANE_BOTTOM - LANE_Y0
    gap = NODE_GAP
    for g in (NODE_GAP, 0.145, 0.135, 0.125, 0.115, 0.105):
        need = sum(max(0.55, r * (NODE_H + g) - g + 0.13) for r in rows_needed)
        if need <= total_h:
            gap = g
            break
    ys = lane_heights(lanes, rows_needed, gap=gap)

    # put documents at the top or bottom of the bucket: whichever side blocks fewer cross-lane vertical links
    lane_of = {nd["id"]: nd["lane"] for nd in pg["nodes"]}
    up_dn = {}
    for (si, li), lst in buckets.items():
        ids = {nd["id"] for nd in lst}
        up = dn = 0
        for a, b in pg.get("links", []):
            if a in ids and b not in ids:
                la = lane_of.get(b, li)
                up += la < li
                dn += la > li
            elif b in ids and a not in ids:
                la = lane_of.get(a, li)
                up += la < li
                dn += la > li
        up_dn[(si, li)] = up < dn          # True -> documents at the top of the bucket

    pos = {}
    BH, BGAP = NODE_H, gap
    pitch = BH + BGAP
    nstage = len(xs)
    for (si, li), lst in buckets.items():
        sx, swid = xs[si]
        y0, lh = ys[li]
        # business objects (documents) go to one end of the bucket (bottom by default) instead of between two tasks,
        # where they would block the vertical task-to-task centre link; top/bottom is chosen to block fewer cross-lane links
        if up_dn.get((si, li)):
            lst = sorted(lst, key=lambda nd: 0 if nd.get("kind") == "doc" else 1)
        else:
            lst = sorted(lst, key=lambda nd: 1 if nd.get("kind") == "doc" else 0)
        cnt = len(lst)
        # more than 3 nodes in one (stage, lane): use two columns so the lane does not become too tall
        ncol = 2 if cnt > 3 else 1
        per = math.ceil(cnt / float(ncol))
        # inset: each inner boundary gives up OVL/2 + CH/2 so the clearance between neighbouring columns is exactly CH;
        # the first/last stages give up the gutter GUT for the start/end dots
        il = GUT if si == 0 else OVL / 2 + CH / 2
        ir = GUT if si == nstage - 1 else OVL / 2 + CH / 2
        left = sx + il
        colw = ((sx + swid - ir) - left - (ncol - 1) * GX) / ncol
        # vertical: centre as a block by the lane's maximum row count
        rmax = rows.get(li, 1)
        used = (rmax - 1) * pitch + BH
        ytop = y0 + (lh - used) / 2.0
        for k, nd in enumerate(lst):
            c = min(k // per, ncol - 1)
            r = k % per
            nx = left + c * (colw + GX)
            ny = ytop + r * pitch
            is_doc = nd.get("kind", "act") == "doc"
            # documents are slightly narrower and left-aligned, leaving a 0.14 routing channel on the right:
            # vertical links blocked by a document use this channel instead of merging with the document border
            dw = colw - 0.16
            pos[nd["id"]] = dict(x=nx + (0.02 if is_doc else 0), y=ny,
                                 w=dw if is_doc else colw, h=BH, lane=li, stage=si,
                                 kind="doc" if is_doc else "act", order=k)
    return pos, ys, xs


def _tw(s):
    """Estimate text width (a CJK character = 1, ASCII about 0.55)."""
    return sum(1.0 if ord(c) > 127 else (0.62 if c.isupper() else 0.53) for c in s)


def fit_font(txt, w, h, sizes, ls=1.0):
    """Pick the largest candidate font size that fits the whole text into w x h; if none fits, return the smallest size and the estimated line count."""
    avail_w = max(0.05, w - 0.12)   # measured: the usable text width inside a WPS rounded box is about 0.11-0.13 smaller than the box width
    for fs in sizes:
        per = avail_w * 72.0 / fs                 # CJK characters per line
        nline = 0
        for line in str(txt).split("\n"):
            nline += max(1, math.ceil(_tw(line) / per))
        if nline * fs * 1.22 * ls / 72.0 <= h + 0.005:
            return fs
    return sizes[-1]


def draw_nodes(tk, pg, pos):
    for nd in pg["nodes"]:
        p = pos[nd["id"]]
        txt = nd["text"]
        if p["kind"] == "doc":
            fs = fit_font(txt, p["w"], p["h"], [10, 9.5, 9, 8.5, 8, 7.5])
            sp = tk.box(p["x"], p["y"], p["w"], p["h"], txt, fs, C_WHITE, line=C_TEAL_LN,
                        lnw=0.75, fc=C_INK, bold=True, shape=MSO_SHAPE.FOLDED_CORNER, ml=0.02)
        else:
            fs = fit_font(txt, p["w"], p["h"], [10.5, 10, 9.5, 9, 8.5, 8, 7.5])
            sp = tk.box(p["x"], p["y"], p["w"], p["h"], txt, fs, C_TEAL, line=None,
                        fc=C_WHITE, bold=False, shape=MSO_SHAPE.ROUNDED_RECTANGLE, ml=0.02)
        tk.ids[nd["id"]] = sp.shape_id
        tk.mark_node(sp._element)


# ================= links (single elbow connector + automatic gluing) =================
# connection-site indices (measured, 0-based):
#   rounded rectangle / rectangle: 0=top 1=left 2=bottom 3=right
#   ellipse (8 sites): 0=top 1=top-left 2=left 3=bottom-left 4=bottom 5=bottom-right 6=right 7=top-right
IDX_RECT = {"t": 0, "l": 1, "b": 2, "r": 3}
IDX_OVAL = {"t": 0, "l": 2, "b": 4, "r": 6}


def _box(p):
    return dict(l=p["x"], r=p["x"] + p["w"], t=p["y"], b=p["y"] + p["h"],
                cx=p["x"] + p["w"] / 2, cy=p["y"] + p["h"] / 2)


def _anchor(p, s):
    x, y, w, h = p["x"], p["y"], p["w"], p["h"]
    return {"r": (x + w, y + h / 2), "l": (x, y + h / 2),
            "b": (x + w / 2, y + h), "t": (x + w / 2, y)}[s]


def _poly(A, B, kind, sa, sb, p):
    """Polyline actually followed by a connector (used for offline route evaluation).

    kind="line" -> straight line (preferred for same-row/same-column pairs without obstacles; the last segment is the full length, so the arrow is clear)
    kind="c3" -> bentConnector3 (H-V-H; p is adj1: position of the vertical segment)
    kind="c4" -> bentConnector4 (adj1=0 degenerates to V-H-V; p is adj2: position of the horizontal crossing)
    so a vertically adjacent pair of nodes can leave and enter vertically, running along the centre axis of both boxes instead of around their sides.
    """
    ax, ay = _anchor(A, sa)
    bx, by = _anchor(B, sb)
    if kind == "line":
        return [(ax, ay), (bx, by)]
    if kind == "c4":
        my = ay + (by - ay) * p
        return [(ax, ay), (ax, my), (bx, my), (bx, by)]
    mx = ax + (bx - ax) * p
    return [(ax, ay), (mx, ay), (mx, by), (bx, by)]


def _seg_len(p1, p2):
    return abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])


def _custom_pts(A, B, sa, sb, D=0.16):
    """A pair on the same side with the same x: both ends turn out into the gutter by D, joined by a vertical run.

    An elbow connector's polyline must stay inside the rectangle spanned by its end points; with identical x the rectangle has zero width,
    so the last segment has zero length -> the arrow direction is undefined and WPS draws a small outward-pointing arrow.
    Such links use a custom polyline instead: start turns out along the box edge into the gutter -> vertical run -> turns back to the end; the last segment keeps its length,
    so the arrow always points into the box.
    """
    ax, ay = _anchor(A, sa)
    bx, by = _anchor(B, sb)
    if sa in ("l", "r"):
        off = ax + (-D if sa == "l" else D)
        return [(ax, ay), (off, ay), (off, by), (bx, by)]
    off = ay + (-D if sa == "t" else D)
    return [(ax, ay), (ax, off), (bx, off), (bx, by)]


def _vpair(A, B):
    """Decide whether a pair is "vertically adjacent" (mainly vertical); returns (exit side, entry side).

    When the offset is mainly vertical, force bottom/top exit and top/bottom entry so that the link runs through the centre axis of both boxes.
    """
    dx = (B["x"] + B["w"] / 2) - (A["x"] + A["w"] / 2)
    dy = (B["y"] + B["h"] / 2) - (A["y"] + A["h"] / 2)
    if abs(dy) < 0.22:                 # same row -> horizontal link
        return None
    if abs(dy) < 0.8 * abs(dx):        # larger horizontal offset -> horizontal Z
        return None
    return ("b", "t") if dy > 0 else ("t", "b")


AX_TOL = 0.012          # tolerance for "orthogonal": corridor polylines rounded to 3 decimals keep a skew of ~0.0005",
                        # and a strict 1e-6 test would let such segments escape the box-crossing check (exactly the lines that run along or through boxes)


def _seg_hits(p1, p2, bx, pad=0.02):
    """Does the segment pass through the inside of the rectangle (box shrunk by pad; end points on the edge do not count)?

    Nearly horizontal / nearly vertical segments (|delta| <= AX_TOL) are treated as orthogonal and tested by interval overlap,
    so that slightly skewed segments produced by rounding cannot escape detection.
    """
    x0, y0 = bx["x"] + pad, bx["y"] + pad
    x1, y1 = bx["x"] + bx["w"] - pad, bx["y"] + bx["h"] - pad
    (ax, ay), (bx2, by2) = p1, p2
    if abs(ay - by2) <= AX_TOL:                    # horizontal segment
        if not (min(ay, by2) < y1 and max(ay, by2) > y0):
            return 0
        lo, hi = sorted((ax, bx2))
        return 1 if (hi > x0 and lo < x1) else 0
    if abs(ax - bx2) <= AX_TOL:                    # vertical segment
        if not (min(ax, bx2) < x1 and max(ax, bx2) > x0):
            return 0
        lo, hi = sorted((ay, by2))
        return 1 if (hi > y0 and lo < y1) else 0
    return 0


def _graze(p1, p2, bx, tol=0.075):
    """Does the segment run along a rectangle edge (visually "hugging" the box)?"""
    x0, x1 = bx["x"], bx["x"] + bx["w"]
    y0, y1 = bx["y"], bx["y"] + bx["h"]
    (ax, ay), (bx2, by2) = p1, p2
    if abs(ay - by2) <= AX_TOL:                    # horizontal segment
        yy = (ay + by2) / 2.0
        if not (abs(yy - y0) <= tol or abs(yy - y1) <= tol):
            return 0
        lo, hi = sorted((ax, bx2))
        return 1 if (hi > x0 + 0.05 and lo < x1 - 0.05) else 0
    if abs(ax - bx2) <= AX_TOL:                    # vertical segment
        xx = (ax + bx2) / 2.0
        if not (abs(xx - x0) <= tol or abs(xx - x1) <= tol):
            return 0
        lo, hi = sorted((ay, by2))
        return 1 if (hi > y0 + 0.05 and lo < y1 - 0.05) else 0
    return 0


def _cands(vpair, A=None, B=None):
    """Candidate combinations: straight (same row/column) -> horizontal-out/horizontal-in Z -> vertical-then-horizontal L -> centre-axis V-H-V."""
    out = []
    if A is not None and B is not None:
        dx = (B["x"] + B["w"] / 2) - (A["x"] + A["w"] / 2)
        dy = (B["y"] + B["h"] / 2) - (A["y"] + A["h"] / 2)
        if abs(dy) < 0.02 and abs(dx) > 0.15:      # same row: direct horizontal link
            out.append(("line", "r" if dx > 0 else "l", "l" if dx > 0 else "r", 0.0))
        if abs(dx) < 0.02 and abs(dy) > 0.10:      # same column: direct vertical link
            out.append(("line", "b" if dy > 0 else "t", "t" if dy > 0 else "b", 0.0))
    for sa in ("r", "l"):                          # leave horizontally -> Z shape
        for sb in ("r", "l"):
            for p in (0.2, 0.35, 0.5, 0.65, 0.8):
                out.append(("c3", sa, sb, p))
    for sa in ("t", "b"):                          # vertical then horizontal L
        for sb in ("l", "r"):
            out.append(("c3", sa, sb, 0.0))
    for sa in ("l", "r"):                          # horizontal then vertical L
        for sb in ("t", "b"):
            out.append(("c3", sa, sb, 1.0))
    if vpair:                                      # vertically adjacent: centre-axis V-H-V
        for p in (0.5, 0.38, 0.62, 0.28, 0.72):
            out.append(("c4", vpair[0], vpair[1], p))
    return out


def _free(pts, obstacles):
    """Is the whole polyline free of box crossings?"""
    return not any(_seg_hits(pts[i], pts[i + 1], ob)
                   for ob in obstacles for i in range(len(pts) - 1))


def _tracks(obstacles):
    """Candidate routing tracks: lines 0.13" outside each box + **the centre line of the gap between adjacent boxes**.

    With fixed offsets only, a corridor always hugs some box (clearance 0.02-0.03, i.e. drawn on the border);
    adding gap centre lines lets the corridor pass "through the gap", equidistant from both boxes.
    """
    xs, ys = set(), set()
    for ob in obstacles:
        xs.add(round(ob["x"] - 0.13, 3))
        xs.add(round(ob["x"] + ob["w"] + 0.13, 3))
        ys.add(round(ob["y"] - 0.10, 3))
        ys.add(round(ob["y"] + ob["h"] + 0.10, 3))
    bs = list(obstacles)
    for a in bs:
        for b in bs:
            if a is b:
                continue
            # vertical gap: the boxes overlap horizontally, leaving a channel between them above/below
            if min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]) > 0.10:
                g0, g1 = a["y"] + a["h"], b["y"]
                if 0.05 < g1 - g0 < 0.6:
                    ys.add(round((g0 + g1) / 2.0, 3))
            # horizontal gap: the boxes overlap vertically, leaving a channel between them left/right
            if min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]) > 0.10:
                g0, g1 = a["x"] + a["w"], b["x"]
                if 0.05 < g1 - g0 < 0.6:
                    xs.add(round((g0 + g1) / 2.0, 3))
    return sorted(xs), sorted(ys)


def _snap(pts, eps=AX_TOL):
    """Snap a polyline to strict orthogonality: nearly horizontal segments get one y at both ends, nearly vertical ones one x.

    Corridor track coordinates come from `round(v, 3)` and differ by a few thousandths from raw port coordinates (e.g. 5.33154),
    which produces a line that looks horizontal but is actually skewed; invisible when rendered,
    yet it slips past collision detection, runs through boxes and is hidden by them, leaving only arrowless stubs at both ends.
    Snapping aligns to **the end attached to a port** first (start point for the first segment, end point for the last) so anchors are not moved off their ports.
    """
    out = [list(q) for q in pts]
    n = len(out)
    for i in range(n - 1):
        dx = abs(out[i + 1][0] - out[i][0])
        dy = abs(out[i + 1][1] - out[i][1])
        if dy <= eps and dy < dx:
            ref = out[0][1] if i == 0 else (out[-1][1] if i == n - 2 else (out[i][1] + out[i + 1][1]) / 2.0)
            out[i][1] = out[i + 1][1] = ref
        elif dx <= eps and dx < dy:
            ref = out[0][0] if i == 0 else (out[-1][0] if i == n - 2 else (out[i][0] + out[i + 1][0]) / 2.0)
            out[i][0] = out[i + 1][0] = ref
    res = [out[0]]
    for q in out[1:]:
        if _seg_len(res[-1], q) > 0.004:
            res.append(q)
    return [tuple(q) for q in res]


def _corridor_pts(A, B, sa, sb, obstacles, D=0.15):
    """Detour corridor: exit turn -> vertical track -> horizontal track -> entry turn; used for long back-links with no elbow solution.

    Tracks prefer gap centre lines (far from boxes on both sides) and are limited to 1.45 x the Manhattan distance,
    to avoid odd lines that cross the whole slide while hugging box edges.
    """
    S = _anchor(A, sa)
    E = _anchor(B, sb)
    dsx, dsy = {"l": (-1, 0), "r": (1, 0), "t": (0, -1), "b": (0, 1)}[sa]
    dex, dey = {"l": (-1, 0), "r": (1, 0), "t": (0, -1), "b": (0, 1)}[sb]
    S1 = (S[0] + dsx * D, S[1] + dsy * D)
    E1 = (E[0] + dex * D, E[1] + dey * D)
    man = abs(E[0] - S[0]) + abs(E[1] - S[1])
    limit = man * 1.45 + 0.35
    xs, ys = _tracks(obstacles)
    xs = [v for v in xs if (dsx == 0 or (v - S1[0]) * dsx >= -1e-6)]
    ys = [v for v in ys if (dsy == 0 or (v - S1[1]) * dsy >= -1e-6)]
    xs += [S1[0], E1[0]]
    ys += [S1[1], E1[1]]
    best, best_score = None, None
    for xg in sorted(set(round(v, 3) for v in xs)):
        for yg in sorted(set(round(v, 3) for v in ys)):
            pts = [S, S1, (xg, S1[1]), (xg, yg), (E1[0], yg), E1, E]
            pts = [pts[0]] + [q for i, q in enumerate(pts[1:], 1)
                              if _seg_len(pts[i - 1], q) > 0.02]
            if len(pts) < 3 or not _free(pts, obstacles):
                continue
            L = sum(_seg_len(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            if L > limit:
                continue
            graze = sum(_graze(pts[i], pts[i + 1], ob)
                        for ob in obstacles for i in range(len(pts) - 1))
            # a middle segment running close to another box (clearance < 0.06) also counts as grazing: it looks worse than a slightly longer detour,
            # so it is penalized heavily among candidates, forcing the choice of gap centre lines over "0.02 outside a box edge"
            hug = sum(_graze(pts[i], pts[i + 1], ob, tol=0.06)
                      for ob in obstacles for i in range(1, len(pts) - 2))
            if _seg_len(pts[-2], pts[-1]) < 0.06:
                continue
            score = L + graze * 0.55 + hug * 1.2
            if best_score is None or score < best_score:
                best, best_score = pts, score
    if best is None:
        return None
    best = _snap(best)                 # re-check after snapping to orthogonal: skewed segments must not cross boxes
    if not _free(best, obstacles) or _seg_len(best[-2], best[-1]) < 0.06:
        return None
    return best


def _corr_cands(A, B):
    """Exit/entry sides for corridor candidates: leave towards the target first, avoiding odd turns such as "probe 0.15 to the right, then fold back left"."""
    dx = (B["x"] + B["w"] / 2) - (A["x"] + A["w"] / 2)
    dy = (B["y"] + B["h"] / 2) - (A["y"] + A["h"] / 2)
    hx, hxo = ("r", "l") if dx >= 0 else ("l", "r")
    vy, vyo = ("b", "t") if dy >= 0 else ("t", "b")
    out = [(hx, hxo), (hx, vy), (vy, hx), (vy, vyo), (hxo, hx), (vyo, hx)]
    seen, res = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            res.append(p)
    return res


def plan_link(A, B, obstacles, segs, ports=None, aid=None, bid=None, forbid=None):
    """Pick the best route for one link: first no box crossing and no edge hugging, then rank by orientation and detour cost.

    ports records who already occupies each port (key = (node id, side)); two links sharing a port overlap
    into one thick line at the start/end, so this is heavily penalized and only allowed when there is no alternative.
    """
    ports = ports or {}
    forbid = forbid or ()
    vpair = _vpair(A, B)
    best, best_score = None, None
    for kind, sa, sb, p in _cands(vpair, A, B):
        if (aid, sa) in forbid or (bid, sb) in forbid:
            continue
        pts = _poly(A, B, kind, sa, sb, p)
        n = len(pts) - 1
        hits = graze = 0
        for ob in obstacles:
            for i in range(n):
                hits += _seg_hits(pts[i], pts[i + 1], ob)
                graze += _graze(pts[i], pts[i + 1], ob)
        if hits:
            continue
        # soft penalty for overlapping or crossing existing links
        clash = 0
        for i in range(n):
            for q1, q2 in segs:
                if _overlap(pts[i], pts[i + 1], q1, q2):
                    clash += 1
        # port occupancy: in and out on the same port renders as "a line passing through the box edge" and is heavily penalized;
        # several in or several out on one port is a normal merge/split and only slightly penalized.
        o = ports.get((aid, sa), {})
        i = ports.get((bid, sb), {})
        port_pen = 0.0
        if o.get("in"):
            port_pen += 3.0
        if i.get("out"):
            port_pen += 3.0
        port_pen += 0.25 * len(o.get("out", [])) + 0.20 * len(i.get("in", []))
        L = sum(abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
                for i in range(n))
        s = clash * 0.8 + L * 0.02 + graze * 0.20 + port_pen
        if kind == "line":
            s -= 0.55                              # prefer straight lines: no bends, the arrow keeps its full shaft
        elif vpair and (sa, sb) == vpair:
            # vertically adjacent: centre-axis V-H-V is second best; H-V-H folding back along a box edge is explicitly rejected
            s += -0.20 if kind == "c4" else 1.20
        elif sa in ("t", "b"):
            s += 0.45                              # unusual: leaving through the top/bottom port first
        elif sb in ("t", "b"):
            s += 0.30
        s += 0.0 if sa == "r" else 0.03
        if best_score is None or s < best_score:
            best, best_score = (kind, sa, sb, p, pts), s
    if best is None:                               # no elbow solution at all -> detour corridor
        for sa, sb in _corr_cands(A, B):
            if (aid, sa) in forbid or (bid, sb) in forbid:
                continue
            r = _corridor_pts(A, B, sa, sb, obstacles)
            if r:
                return ("cust", sa, sb, 0.15, r)
        pts = _poly(A, B, "c3", "r", "l", 0.5)
        return ("c3", "r", "l", 0.5, pts)
    # with a last segment < 0.06" the arrowhead fills the whole segment, its direction is unclear, and WPS may even draw it pointing outwards;
    # use a custom polyline that turns out into the gutter at both ends, keeping at least one visible arrow shaft
    if _seg_len(best[4][-2], best[4][-1]) < 0.06:
        sa, sb = best[1], best[2]
        pairs = []
        for pair in ((sa, sa), (sb, sb), ("l", "l"), ("r", "r"), ("t", "t"), ("b", "b")):
            if pair[0] == pair[1] and pair not in pairs:
                pairs.append(pair)
        for D in (0.16, 0.20, 0.12):
            for pair in pairs:
                pts = _custom_pts(A, B, pair[0], pair[1], D)
                if _free(pts, obstacles):
                    return ("cust", pair[0], pair[1], D, pts)
        for csa, csb in _corr_cands(A, B):
            if (aid, csa) in forbid or (bid, csb) in forbid:
                continue
            pts = _corridor_pts(A, B, csa, csb, obstacles)
            if pts:
                return ("cust", csa, csb, 0.15, pts)
    return best


def _overlap(p1, p2, q1, q2, tol=0.03):
    """Do two segments intersect or overlap (orthogonal segments only)?"""
    def vert(p, q):
        return abs(p[0] - q[0]) < 1e-6
    v1, v2 = vert(p1, p2), vert(q1, q2)
    if v1 == v2:                                    # parallel
        if v1:
            if abs(p1[0] - q1[0]) > tol:
                return False
            lo1, hi1 = sorted((p1[1], p2[1])); lo2, hi2 = sorted((q1[1], q2[1]))
        else:
            if abs(p1[1] - q1[1]) > tol:
                return False
            lo1, hi1 = sorted((p1[0], p2[0])); lo2, hi2 = sorted((q1[0], q2[0]))
        return hi1 > lo2 + tol and hi2 > lo1 + tol
    # one horizontal, one vertical
    if v1:
        vx = p1[0]; vy0, vy1 = sorted((p1[1], p2[1]))
        hy = q1[1]; hx0, hx1 = sorted((q1[0], q2[0]))
    else:
        vx = q1[0]; vy0, vy1 = sorted((q1[1], q2[1]))
        hy = p1[1]; hx0, hx1 = sorted((p1[0], p2[0]))
    return hx0 - tol <= vx <= hx1 + tol and vy0 - tol <= hy <= vy1 + tol


def _glue(conn, id1, idx1, id2, idx2):
    """Really glue both connector ends to their shapes (WPS/PowerPoint then moves the link with the shape)."""
    from lxml import etree
    cNv = conn._element.find(qn('p:nvCxnSpPr')).find(qn('p:cNvCxnSpPr'))
    for tag, sid, idx in (('a:stCxn', id1, idx1), ('a:endCxn', id2, idx2)):
        if sid is None:
            continue
        el = etree.SubElement(cNv, qn(tag))
        el.set('id', str(sid)); el.set('idx', str(idx))


def _cust_geom(conn, pts):
    """Replace the connector geometry with an explicit polyline (still the same connector shape, still glued at both ends)."""
    from lxml import etree
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    x0, y0 = min(xs), min(ys)
    w = max(0.03, max(xs) - x0)
    h = max(0.03, max(ys) - y0)
    spPr = conn._element.spPr
    xfrm = spPr.find(qn('a:xfrm'))
    for attr in ('flipH', 'flipV'):
        if attr in xfrm.attrib:
            del xfrm.attrib[attr]
    xfrm.find(qn('a:off')).set('x', str(int(Inches(x0))))
    xfrm.find(qn('a:off')).set('y', str(int(Inches(y0))))
    xfrm.find(qn('a:ext')).set('cx', str(int(Inches(w))))
    xfrm.find(qn('a:ext')).set('cy', str(int(Inches(h))))
    old = spPr.find(qn('a:prstGeom'))
    if old is not None:
        anchor = old
    else:
        anchor = xfrm
    cust = etree.Element(qn('a:custGeom'))
    for tag in ('a:avLst', 'a:gdLst', 'a:ahLst', 'a:cxnLst'):
        etree.SubElement(cust, qn(tag))
    rc = etree.SubElement(cust, qn('a:rect'))
    for k, v in (('l', '0'), ('t', '0'), ('r', 'r'), ('b', 'b')):
        rc.set(k, v)
    pl = etree.SubElement(cust, qn('a:pathLst'))
    path = etree.SubElement(pl, qn('a:path'))
    W, H = int(Inches(w)), int(Inches(h))
    path.set('w', str(W)); path.set('h', str(H)); path.set('fill', 'none')
    for i, (px, py) in enumerate(pts):
        node = etree.SubElement(path, qn('a:moveTo' if i == 0 else 'a:lnTo'))
        pt = etree.SubElement(node, qn('a:pt'))
        pt.set('x', str(max(0, min(W, int(Inches(px - x0))))))
        pt.set('y', str(max(0, min(H, int(Inches(py - y0))))))
    anchor.addprevious(cust)
    if old is not None:
        spPr.remove(old)


def tk_link(tk, A, B, kind, sa, sb, p, id1, id2, idmap1, idmap2, arrow=True, pts=None):
    """Draw one link as a single connector shape and glue it to the shapes at both ends.

    kind="c3" -> elbow connector (2 bends); kind="c4" -> elbow connector (3 bends, V-H-V);
    kind="cust" -> explicit polyline (only for zero-width/zero-height pairs; guarantees a last segment with length and an arrow pointing into the box).
    """
    from lxml import etree
    ax, ay = _anchor(A, sa)
    bx, by = _anchor(B, sb)
    if kind == "cust" and pts is None:
        pts = _custom_pts(A, B, sa, sb, p or 0.16)
    straight = (kind == "line")
    if kind == "cust":
        c = tk.slide.shapes.add_connector(
            MSO_CONNECTOR.ELBOW,
            Inches(min(q[0] for q in pts)), Inches(min(q[1] for q in pts)),
            Inches(max(q[0] for q in pts)), Inches(max(q[1] for q in pts)))
    else:
        c = tk.slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT if straight else MSO_CONNECTOR.ELBOW,
            Inches(ax), Inches(ay), Inches(bx), Inches(by))
    c.line.color.rgb = C_FLOW
    c.line.width = Pt(1.15)
    c.shadow.inherit = False
    if kind == "cust":
        _cust_geom(c, pts)
    elif not straight:
        # set the bend position: c3 uses adj1, c4 uses adj1=0 + adj2
        g = c._element.spPr.find(qn('a:prstGeom'))
        for av in list(g):
            g.remove(av)
        av = etree.SubElement(g, qn('a:avLst'))
        if kind == "c4":
            g.set('prst', 'bentConnector4')
            for name, val in (('adj1', 0), ('adj2', p)):
                gd = etree.SubElement(av, qn('a:gd'))
                gd.set('name', name); gd.set('fmla', 'val %d' % int(round(val * 100000)))
        else:
            gd = etree.SubElement(av, qn('a:gd'))
            gd.set('name', 'adj1'); gd.set('fmla', 'val %d' % int(round(p * 100000)))
    if arrow:
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn('a:tailEnd'),
                                 {'type': 'triangle', 'w': 'lg', 'len': 'med'}))
    _glue(c, id1, idmap1[sa], id2, idmap2[sb])
    return c


def _plan_once(pg, pos, obstacles, forbid):
    segs, ports, out = [], {}, []

    def key(a, b):
        A, B = _box(pos[a]), _box(pos[b])
        dx, dy = abs(B["cx"] - A["cx"]), abs(B["cy"] - A["cy"])
        # direct (orthogonally aligned) links first -> longer spans first -> original order
        return (0 if (dx < 0.02 or dy < 0.02) else 1, -(dx + dy))

    for a, b in sorted(pg["links"], key=lambda q: key(q[0], q[1])):
        if a not in pos or b not in pos:
            continue
        kind, sa, sb, p, pts = plan_link(pos[a], pos[b], obstacles, segs,
                                         ports, a, b, forbid.get((a, b)))
        out.append((a, b, kind, sa, sb, p, pts))
        ports.setdefault((a, sa), {}).setdefault("out", []).append(b)
        ports.setdefault((b, sb), {}).setdefault("in", []).append(a)
        for i in range(len(pts) - 1):
            segs.append((pts[i], pts[i + 1]))
    # output in the original data order so that drawing order matches the data
    order = {tuple(l): i for i, l in enumerate(pg["links"])}
    out.sort(key=lambda r: order.get((r[0], r[1]), 999))
    return out


def _two_way(plan):
    """Find ports that carry both an incoming and an outgoing link; returns [(port, outgoing links, incoming links)]."""
    ins, outs = {}, {}
    for a, b, kind, sa, sb, p, pts in plan:
        ins.setdefault((b, sb), []).append((a, b))
        outs.setdefault((a, sa), []).append((a, b))
    return [(k, outs[k], ins[k]) for k in ins if k in outs]


def _hard_bad(plan, obstacles):
    """Defect count: segments crossing boxes + links with too short a last segment (used to choose among re-routing rounds)."""
    n = 0
    for a, b, kind, sa, sb, p, pts in plan:
        for i in range(len(pts) - 1):
            for ob in obstacles:
                n += _seg_hits(pts[i], pts[i + 1], ob)
        if _seg_len(pts[-2], pts[-1]) < 0.06:
            n += 3
    return n


def link_plan(pg, pos, extra=None):
    """Route all links on a slide; returns [(a,b,kind,sa,sb,p,pts)].

    Order: first the "skeleton" (direct same-row/same-column links, main cross-lane chain), then back-links,
    so that main links get their preferred ports and back-links take the next best.

    Then iterate for "port exclusivity": wherever a port has both an incoming and an outgoing link, move the outgoing link to another side and re-route,
    for at most 4 rounds; each round keeps the plan with the fewest bidirectional ports and the fewest defects.
    This is the main cause of "unreadable arrows": when an incoming and an outgoing link share a connection point,
    the result renders as one line passing along the box edge, and it is impossible to tell which end has the arrow.
    """
    # extra: start/end dots and their label blocks; links must not run over them,
    # otherwise an arrow ends up crossing a label's text
    obstacles = [dict(x=p["x"], y=p["y"], w=p["w"], h=p["h"]) for p in pos.values()]
    obstacles += list(extra or [])

    def span(l):
        """Manhattan distance between two node centres: the smaller it is, the more "skeleton-like" the link and the more it deserves its preferred port."""
        A, B = _box(pos[l[0]]), _box(pos[l[1]])
        return abs(B["cx"] - A["cx"]) + abs(B["cy"] - A["cy"])

    def score(plan):
        tw = len(_two_way(plan))
        total = sum(_seg_len(pts[i], pts[i + 1])
                    for a, b, k, sa, sb, p, pts in plan
                    for i in range(len(pts) - 1))
        return (tw, _hard_bad(plan, obstacles), round(total, 2))

    forbid = {}
    plan = _plan_once(pg, pos, obstacles, forbid)
    best, best_score = plan, score(plan)
    for _ in range(5):
        tw = _two_way(plan)
        if not tw:
            break
        improved = False
        for k, outs, ins in tw[:3]:
            users = [l for l in outs] + [l for l in ins]
            if len(users) < 2:
                continue
            # try "who changes side" one by one: same-port conflicts are resolved by comparing total cost, not by a fixed rule.
            # skeleton links (short spans) usually win and long back-links give way; where the reverse is cheaper, the reverse is used.
            for victim in users:
                f2 = {kk: set(vv) for kk, vv in forbid.items()}
                for l in users:
                    if l != victim:
                        f2.setdefault(l, set()).add(k)
                p2 = _plan_once(pg, pos, obstacles, f2)
                s2 = score(p2)
                if s2 < best_score:
                    best, best_score, plan, forbid = p2, s2, p2, f2
                    improved = True
        if not improved:
            break
    return _nudge(best, obstacles)


MIN_SEP = 0.095          # minimum visual distance between adjacent parallel links (1.15 pt line width ~ 0.016"; leaves enough gap)


def _seg_free(p1, p2, obstacles, margin=0.045):
    """Segment keeps at least margin from all boxes (end points touching edges are handled by the caller)."""
    for ob in obstacles:
        if _seg_hits(p1, p2, dict(x=ob["x"] - margin, y=ob["y"] - margin,
                                  w=ob["w"] + 2 * margin, h=ob["h"] + 2 * margin), 0):
            return False
    return True


def _nudge(plan, obstacles):
    """Separate two parallel lines that lie on top of each other so they do not render as one thick line.

    Only middle segments that do not touch a port are moved (moving the first/last segment would detach it from its port).
    """
    for _ in range(10):
        fixed = False
        segs = []
        for li, rec in enumerate(plan):
            pts = rec[6]
            for si in range(len(pts) - 1):
                p1, p2 = pts[si], pts[si + 1]
                if _seg_len(p1, p2) < 0.15:
                    continue
                if si == 0 or si == len(pts) - 2:
                    continue                     # segments touching a port are not moved
                vertical = abs(p1[0] - p2[0]) < 1e-6
                if vertical:
                    segs.append((li, si, "V", p1[0], min(p1[1], p2[1]), max(p1[1], p2[1])))
                elif abs(p1[1] - p2[1]) < 1e-6:
                    segs.append((li, si, "H", p1[1], min(p1[0], p2[0]), max(p1[0], p2[0])))
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                li, si, d, o1, lo1, hi1 = segs[i]
                lj, sj, d2, o2, lo2, hi2 = segs[j]
                if d != d2 or li == lj:
                    continue
                gap = abs(o1 - o2)
                if gap >= MIN_SEP or min(hi1, hi2) - max(lo1, lo2) < 0.15:
                    continue
                if _shift(plan, lj, sj, d, o1, obstacles):
                    fixed = True
        if not fixed:
            break
    _spread(plan, obstacles)
    return plan


def _spread(plan, obstacles):
    """When several parallel lines are squeezed into one narrow track, spread them evenly across the available width.

    When a single shift is limited by the track width, only re-spacing the whole group can separate them.
    """
    segs = []
    for li, rec in enumerate(plan):
        pts = rec[6]
        for si in range(1, len(pts) - 2):
            p1, p2 = pts[si], pts[si + 1]
            if _seg_len(p1, p2) < 0.3:
                continue
            if abs(p1[0] - p2[0]) < 1e-6:
                segs.append([li, si, "V", p1[0], min(p1[1], p2[1]), max(p1[1], p2[1])])
            elif abs(p1[1] - p2[1]) < 1e-6:
                segs.append([li, si, "H", p1[1], min(p1[0], p2[0]), max(p1[0], p2[0])])
    groups, used = [], set()
    for i in range(len(segs)):
        if i in used:
            continue
        grp, stack = [i], [i]
        used.add(i)
        while stack:
            k = stack.pop()
            for j in range(len(segs)):
                if j in used or segs[j][2] != segs[k][2]:
                    continue
                if abs(segs[j][3] - segs[k][3]) > 0.22:
                    continue
                if min(segs[j][5], segs[k][5]) - max(segs[j][4], segs[k][4]) < 0.15:
                    continue
                used.add(j)
                grp.append(j)
                stack.append(j)
        if len(grp) >= 2:
            groups.append(grp)
    for grp in groups:
        members = sorted((segs[i] for i in grp), key=lambda s: s[3])
        xs = [m[3] for m in members]
        if min(b - a for a, b in zip(xs, xs[1:])) >= MIN_SEP:
            continue
        d = members[0][2]
        lo_y = min(m[4] for m in members)
        hi_y = max(m[5] for m in members)
        lo_x, hi_x = min(xs), max(xs)
        m_ = 0.032
        left = None
        right = None
        for ob in obstacles:
            # only consider boxes intersecting this group's span
            if d == "V":
                o_lo, o_hi = ob["y"], ob["y"] + ob["h"]
                b_lo, b_hi = ob["x"], ob["x"] + ob["w"]
            else:
                o_lo, o_hi = ob["x"], ob["x"] + ob["w"]
                b_lo, b_hi = ob["y"], ob["y"] + ob["h"]
            if min(o_hi, hi_y) - max(o_lo, lo_y) < 0.05:
                continue
            if b_hi <= lo_x + 1e-6:
                left = b_hi + m_ if left is None else max(left, b_hi + m_)
            if b_lo >= hi_x - 1e-6:
                right = b_lo - m_ if right is None else min(right, b_lo - m_)
        if left is None or right is None or right - left < (len(members) - 1) * 0.06:
            continue
        n = len(members)
        targets = [left + (right - left) * k / (n - 1) for k in range(n)]
        ok = True
        for m, tv in zip(members, targets):
            li, si = m[0], m[1]
            pts = [list(q) for q in plan[li][6]]
            p1, p2 = pts[si], pts[si + 1]
            prev = pts[si - 1] if si > 0 else None
            nxt = pts[si + 2] if si + 2 < len(pts) else None
            cur = p1[0] if d == "V" else p1[1]
            for nb in (prev, nxt):
                if nb is None:
                    continue
                base = nb[0] if d == "V" else nb[1]
                if (tv - base) * (cur - base) <= 1e-9:
                    ok = False
            if not ok:
                break
            q1 = (tv, p1[1]) if d == "V" else (p1[0], tv)
            q2 = (tv, p2[1]) if d == "V" else (p2[0], tv)
            if not _seg_free(q1, q2, obstacles, margin=0.03):
                ok = False
                break
            # after moving, adjacent segments (especially the last one) must not become too short, or the arrow collapses again
            trial = [list(q) for q in pts]
            trial[si][0 if d == "V" else 1] = tv
            trial[si + 1][0 if d == "V" else 1] = tv
            if any(_seg_len(trial[k], trial[k + 1]) < 0.05 for k in range(len(trial) - 1)):
                ok = False
                break
            if _seg_len(trial[-2], trial[-1]) < 0.10:
                ok = False
                break
        if not ok:
            continue
        for m, tv in zip(members, targets):
            li, si = m[0], m[1]
            pts = [list(q) for q in plan[li][6]]
            pts[si][0 if d == "V" else 1] = tv
            pts[si + 1][0 if d == "V" else 1] = tv
            new = [tuple(q) for q in pts]
            if not _free(new, obstacles):
                continue
            plan[li] = plan[li][:6] + (new,)


def _shift(plan, li, si, d, ref, obstacles):
    """Shift segment si of link li in parallel to the nearest free position >= MIN_SEP from the reference line (trying both sides)."""
    rec = plan[li]
    pts = [list(q) for q in rec[6]]
    p1, p2 = pts[si], pts[si + 1]
    cur = p1[0] if d == "V" else p1[1]
    prev = pts[si - 1] if si > 0 else None
    nxt = pts[si + 2] if si + 2 < len(pts) else None
    signs = [1, -1] if cur >= ref else [-1, 1]
    for sign in signs:
        for delta in (MIN_SEP, MIN_SEP + 0.02, MIN_SEP + 0.035, MIN_SEP + 0.05):
            cand = ref + sign * delta
            # must not go beyond the far-end coordinate of the adjacent segment (or the polyline would turn back)
            ok = True
            for nb in (prev, nxt):
                if nb is None:
                    continue
                base = nb[0] if d == "V" else nb[1]
                if (cand - base) * (cur - base) <= 1e-9:
                    ok = False
            if not ok:
                continue
            q1 = (cand, p1[1]) if d == "V" else (p1[0], cand)
            q2 = (cand, p2[1]) if d == "V" else (p2[0], cand)
            if not _seg_free(q1, q2, obstacles):
                continue
            pts[si][0 if d == "V" else 1] = cand
            pts[si + 1][0 if d == "V" else 1] = cand
            new = [tuple(q) for q in pts]
            # overall re-check: no box crossing, no zero-length segment
            if any(abs(new[k + 1][0] - new[k][0]) < 1e-6 and abs(new[k + 1][1] - new[k][1]) < 1e-6
                   for k in range(len(new) - 1)):
                pts[si][0 if d == "V" else 1] = p1[0 if d == "V" else 1]
                pts[si + 1][0 if d == "V" else 1] = p2[0 if d == "V" else 1]
                continue
            if not _free(new, obstacles):
                pts[si][0 if d == "V" else 1] = p1[0 if d == "V" else 1]
                pts[si + 1][0 if d == "V" else 1] = p2[0 if d == "V" else 1]
                continue
            plan[li] = rec[:6] + (new,)
            return True
    return False


def ensure_connected(pg, pos):
    """Hard fallback: every task node (except business objects) must have at least one connector.

    If a link is missing in the data, it is attached here to the nearest upstream task in the same lane, and a notice is printed.
    """
    linked = set()
    for a, b in pg["links"]:
        linked.add(a)
        linked.add(b)
    acts = [nd for nd in pg["nodes"]
            if nd.get("kind", "act") != "doc" and nd["id"] in pos]
    add = []
    for nd in acts:
        if nd["id"] in linked:
            continue
        same = [o for o in acts if o["id"] != nd["id"] and o["lane"] == nd["lane"]]
        ups = [o for o in same if o["stage"] < nd["stage"]]
        pool = ups or same or [o for o in acts if o["id"] != nd["id"]]
        if not pool:
            continue
        o = min(pool, key=lambda q: (abs(pos[q["id"]]["x"] - pos[nd["id"]]["x"])
                                     + 3 * abs(pos[q["id"]]["y"] - pos[nd["id"]]["y"])))
        add.append((o["id"], nd["id"]))
        print("  ! isolated task %s '%s' auto-connected to %s" % (
            nd["id"], nd["text"].replace("\n", ""), o["id"]))
    if add:
        pg["links"] = list(pg["links"]) + add
        for a, b in add:
            linked.add(a); linked.add(b)
    return pg


def draw_links(tk, pg, pos, extra=None):
    ids = tk.ids
    els = []
    for a, b, kind, sa, sb, p, pts in link_plan(pg, pos, extra):
        c = tk_link(tk, pos[a], pos[b], kind, sa, sb, p,
                    ids.get(a), ids.get(b), IDX_RECT, IDX_RECT, pts=pts)
        els.append(c._element)
    tk.put_behind_nodes(els)


# ================= start/end events =================
TERM_D = 0.175                                   # dot diameter
TERM_LBL_H = 0.30                                # label block height (two lines at 9 pt)


def _wrap_chars(s, per=3):
    """Hard-wrap every per characters (Chinese labels have no spaces and must be broken manually)."""
    if s.isascii():
        return s
    s = s.replace("\n", "")
    n = len(s)
    if n <= per:
        return s
    lines = math.ceil(n / float(per))
    per = math.ceil(n / float(lines))
    return "\n".join(s[i:i + per] for i in range(0, n, per))


def _ensure_terminals(pg, pos, ys):
    """If the data gives no start/end, place them on the centre line of the row of the first/last stage's entry/exit task.

    Entry task = task with in-degree 0 in that stage; exit task = task with out-degree 0.
    This way the start/end dots always attach to the real ends of the chain, never to an isolated document.
    """
    ids = [nd["id"] for nd in pg["nodes"] if nd["id"] in pos]
    indeg = {i: 0 for i in ids}
    outdeg = {i: 0 for i in ids}
    for a, b in pg["links"]:
        if a in indeg:
            outdeg[a] += 1
        if b in indeg:
            indeg[b] += 1
    nstage = len(pg["stages"]["names"])
    acts = [nd for nd in pg["nodes"] if nd["id"] in pos]
    for key, stage, deg in (("start", 0, indeg), ("end", nstage - 1, outdeg)):
        if pg.get(key):
            continue
        pool = [nd for nd in acts if nd["stage"] == stage and pg["nodes"] and nd["kind"] != "doc"]
        pool = pool or [nd for nd in acts if nd["stage"] == stage]
        if not pool:
            pg[key] = None
            continue
        ends = [nd for nd in pool if deg.get(nd["id"], 0) == 0]
        nd = (ends or pool)[0]
        p = pos[nd["id"]]
        pg[key] = {"x": X0_LANE + 0.03, "y": p["y"] + p["h"] / 2}
        pg.setdefault(key + "_label", pg.get("_start_lbl", "Start") if key == "start" else pg.get("_end_lbl", "End"))


def place_terminals(pg, pos, ys):
    """Place the start/end dots in the gutter reserved in the first/last stage (GUT=0.50), with the label block below the dot."""
    out = {}
    for key in ("start", "end"):
        e = pg.get(key)
        if not e:
            continue
        side = "left" if key == "start" else "right"
        cy = e["y"]
        # snap: keep 0.10 above the dot and the whole label block inside its lane
        for y0, h in ys:
            if y0 - 0.01 <= cy <= y0 + h + 0.01:
                cy = min(max(cy, y0 + TERM_D / 2 + 0.04),
                         y0 + h - TERM_LBL_H - 0.10)
                break
        bx = X0_LANE + 0.03 if side == "left" else X0_LANE + W_LANE - 0.03 - (GUT - 0.06)
        out[key] = dict(cx=bx + (GUT - 0.06) / 2, cy=cy, bx=bx, bw=GUT - 0.06,
                        side=side, label=pg.get(key + "_label"))
    return out


def terminal_boxes(pg, pos, ys):
    """Return (start/end geometry, obstacle list): dots and label blocks are both handed to the router as obstacles.

    QA scripts must use the same function to obtain obstacles; otherwise the "check result" and the "actual drawing" use different geometry.
    """
    term = place_terminals(pg, pos, ys)
    out = []
    for key in ("start", "end"):
        t = term.get(key)
        if not t:
            continue
        out.append(dict(x=t["cx"] - TERM_D / 2, y=t["cy"] - TERM_D / 2,
                        w=TERM_D, h=TERM_D))
        out.append(dict(x=t["bx"], y=t["cy"] + TERM_D / 2 + 0.02,
                        w=t["bw"], h=TERM_LBL_H))
    return term, out


def draw_terminals(tk, pg, term):
    for key in ("start", "end"):
        t = term.get(key)
        if not t:
            continue
        cx, cy = t["cx"], t["cy"]
        sp = tk.box(cx - TERM_D / 2, cy - TERM_D / 2, TERM_D, TERM_D, "", 8,
                    RGBColor(0x2E, 0x75, 0xB6), line=RGBColor(0x0F, 0x2B, 0x5B),
                    lnw=1.1, shape=MSO_SHAPE.OVAL)
        tk.ids["__%s__" % key] = sp.shape_id
        tk.text(t["bx"], cy + TERM_D / 2 + 0.02, t["bw"], TERM_LBL_H,
                _wrap_chars(t["label"] or ""), 9, True, C_GRAY, ml=0,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.TOP, ls=0.9)


def draw_terminal_links(tk, pg, pos, term):
    """Dot -> first/last task: also exactly one elbow connector, glued at both ends."""
    for key in ("start", "end"):
        t = term.get(key)
        if not t:
            continue
        cy = t["cy"]
        stage = 0 if key == "start" else max(p["stage"] for p in pos.values())
        cands = [(abs(p["y"] + p["h"] / 2 - cy), nid, p)
                 for nid, p in pos.items() if p["stage"] == stage]
        if not cands:
            continue
        # the start attaches preferably to a task with no upstream (the real entry); otherwise to the vertically nearest one
        deg = {}
        for a, b in pg["links"]:
            deg[b] = deg.get(b, 0) + 1
            deg.setdefault(a, 0)
        if key == "start":
            entry = [c for c in cands if deg.get(c[1], 0) == 0]
            cands = entry or cands
        _, nid, p = min(cands)
        dot = dict(x=t["cx"] - TERM_D / 2, y=t["cy"] - TERM_D / 2,
                   w=TERM_D, h=TERM_D)
        obstacles = [dict(x=q["x"], y=q["y"], w=q["w"], h=q["h"]) for q in pos.values()]
        obstacles.append(dict(x=dot["x"], y=dot["y"], w=dot["w"], h=dot["h"]))
        if key == "start":
            kind, sa, sb, pp, _ = plan_link(dot, p, obstacles, [])
            tk_link(tk, dot, p, kind, sa, sb, pp, tk.ids.get("__start__"),
                    tk.ids.get(nid), IDX_OVAL, IDX_RECT)
        else:
            kind, sa, sb, pp, _ = plan_link(p, dot, obstacles, [])
            tk_link(tk, p, dot, kind, sa, sb, pp, tk.ids.get(nid),
                    tk.ids.get("__end__"), IDX_RECT, IDX_OVAL)


# ================= legend =================
def _legend_arrow(tk, x1, y, x2):
    """The "Flow" sample in the legend also uses an elbow connector (same shape family; here both ends have equal height so it renders as a straight line)."""
    from lxml import etree
    c = tk.slide.shapes.add_connector(MSO_CONNECTOR.ELBOW,
                                      Inches(x1), Inches(y), Inches(x2), Inches(y))
    c.line.color.rgb = C_FLOW
    c.line.width = Pt(1.15)
    c.shadow.inherit = False
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn('a:tailEnd'),
                             {'type': 'triangle', 'w': 'lg', 'len': 'med'}))


def draw_legend(tk, extra=""):
    y = LEGEND_Y
    tk.box(0.46, y + 0.02, 0.28, 0.15, "", 7, C_TEAL, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    lg = BP.T(tk.d, "b3_legend")
    tk.text(0.78, y, 0.55, 0.19, lg[0], 10, False, C_GRAY)
    tk.box(1.42, y + 0.01, 0.24, 0.17, "", 7, C_WHITE, line=C_TEAL,
           shape=MSO_SHAPE.FOLDED_CORNER)
    tk.text(1.72, y, 1.34, 0.19, lg[1], 10, False, C_GRAY)
    tk.box(3.06, y + 0.03, 0.16, 0.16, "", 7, RGBColor(0x2E, 0x75, 0xB6),
           line=RGBColor(0x0F, 0x2B, 0x5B), lnw=1.1, shape=MSO_SHAPE.OVAL)
    tk.text(3.28, y, 0.90, 0.19, lg[2], 10, False, C_GRAY)
    _legend_arrow(tk, 4.22, y + 0.11, 4.68)
    tk.text(4.74, y, 0.80, 0.19, lg[3], 10, False, C_GRAY)
    if extra:
        tk.text(5.62, y, 7.2, 0.19, extra, 9.5, False, C_LGRAY)


# ================= single value stream (one slide) =================
def build_stream(tk, pg, domain, series, idx, total):
    norm_page(pg)
    pg["_start_lbl"], pg["_end_lbl"] = BP.T(tk.d, "start"), BP.T(tk.d, "end")
    title = BP.T(tk.d, "b3_title", title=pg["title"], subtitle=pg.get("subtitle") or domain)
    tk.page_head(domain, series, title)
    pos, ys, xs = layout_nodes(pg)
    draw_stage_band(tk, pg["stages"], xs)
    draw_lanes(tk, pg["lanes"], ys)
    draw_nodes(tk, pg, pos)                 # place nodes first: connectors need shape_id to be glued
    ensure_connected(pg, pos)               # fallback: every task node must have a link
    _ensure_terminals(pg, pos, ys)          # fallback: if start/end events are missing, attach them to both ends of the chain
    # start/end dots + label blocks are also obstacles for routing, so links never run over a label
    term, keep = terminal_boxes(pg, pos, ys)
    draw_terminals(tk, pg, term)
    draw_links(tk, pg, pos, keep)           # single elbow connector, pushed below the nodes after drawing
    draw_terminal_links(tk, pg, pos, term)
    draw_legend(tk, pg.get("legend", ""))


# ================= overview slide =================
def build_overview(tk, ov, domain, series):
    tk.page_head(domain, series, BP.T(tk.d, "b3_ov_title", domain=domain))
    cols = list(zip(BP.T(tk.d, "b3_ov_cols"), [1.86, 2.62, 4.42, 1.42, 2.28]))
    x = 0.46
    for name, w in cols:
        tk.box(x, 1.06, w, 0.36, name, 11.5, C_TBL_HDR, line=C_TBL_HDR,
               fc=C_WHITE, bold=True)
        x += w
    nrow = max(1, len(ov["rows"]))
    rh = min(1.22, (6.40 - 1.45) / nrow - 0.03)
    ys = [(1.45 + i * (rh + 0.03), rh) for i in range(nrow)]
    for i, row in enumerate(ov["rows"]):
        y, h = ys[i]
        fill = C_ROW_1 if i == 0 else C_ROW_N
        x = 0.46
        for (name, w) in cols:
            tk.box(x, y, w, h, "", 9, fill, line=C_CELL_LN, lnw=0.75)
            x += w
        # name
        tk.text(0.51, y + 0.13, 1.76, h - 0.2, row["name"], 12, True, C_INK,
                anchor=MSO_ANCHOR.MIDDLE, ls=1.0)
        # trigger -> deliverable
        tk.text(2.38, y + 0.08, 2.50, h - 0.14, row["trigger"], 9.5, False, C_INK,
                ls=1.1, anchor=MSO_ANCHOR.MIDDLE)
        # stages
        tk.text(5.00, y + 0.08, 4.30, h - 0.14, row["stages"], 10 if i == 0 else 9.5,
                i == 0, C_INK, ls=1.15, anchor=MSO_ANCHOR.MIDDLE)
        # customer
        tk.text(9.41, y + 0.08, 1.32, h - 0.14, row["customer"], 10.5, False, C_INK,
                ls=1.1, anchor=MSO_ANCHOR.MIDDLE)
        # value
        tk.text(10.83, y + 0.08, 2.18, h - 0.14, row["value"], 9.5, False, C_INK,
                ls=1.12, anchor=MSO_ANCHOR.MIDDLE)
    # notes
    n = ov["note"]
    ny = 6.51
    tk.box(0.46, ny, 12.4, 0.66, "", 8, C_NOTE_BG, line=C_CELL_LN, lnw=0.75)
    tk.text(0.60, ny + 0.075, 12.15, 0.52, n, 9.5, False, C_GRAY, ls=1.15)


def build_b3_stream(data, out_path, with_overview=True):
    """Generate the B3 PPTX on its own (overview slide + one slide per value stream). generate_views.py calls this function directly."""
    prs = new_prs()
    domain = data["domain"]
    series = data.get("series", "")
    b3 = data["b3"]

    if with_overview and b3.get("overview"):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        apply_bg(slide, prs)
        build_overview(Tk(slide, prs, data), b3["overview"], domain, series)

    pages = b3["pages"]
    for i, pg in enumerate(pages, 1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        apply_bg(slide, prs)
        build_stream(Tk(slide, prs, data), pg, domain, series, i, len(pages))
    prs.save(out_path)
    return out_path


build = build_b3_stream


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Generate the B3 end-to-end value-stream PPTX")
    ap.add_argument("data", nargs="?", default="biz_data.json", help="path to biz_data.json")
    ap.add_argument("-o", "--out", default="outputs/B3-value-streams.pptx")
    ap.add_argument("--font", default=None, help="font name for East Asian text (default: profile font)")
    a = ap.parse_args()
    if a.font:
        FONT = a.font
    with open(a.data, encoding="utf-8") as f:
        d = json.load(f)
    if "b3" not in d:
        sys.exit("[ERROR] data file has no b3 section")
    print(build_b3_stream(d, a.out))
