# -*- coding: utf-8 -*-
"""Generator for all business-architecture views B1-B5 (industry-agnostic, single data-driven entry point; industry/organization differences live in profiles/).

Usage:
  python generate_views.py --data biz_data.json --outdir outputs [--views b1,b2,b3,b4,b5,lists]

Structure of the unified data file biz_data.json (UTF-8):
{
  "domain": "Resource Management", "series": "Example Group · EA-based platform programme",
  "layers": {                       # B1 capability framework (three fixed layers)
    "guide": {"label":"Strategic Control","blocks":[{"l1":"..","l2":["..",".."]}]},
    "exec":  {"label":"Business Execution","blocks":[...]},
    "supp":  {"label":"Integrated Support","blocks":[...]}
  },
  "intro": ["intro line 1","intro line 2"], "note": "B1 footer note",
  "b2": {"note":"...", "layers": {"guide":[{"l1":"..","l2s":[{"l2":"..","comps":[{"name":"..","shared":false}]}]}],
          "exec":[...], "supp":[...]}},
  "b3": {"overview":{"rows":[{name,trigger,stages,customer,value}],"note":".."},
         "pages":[{"title":"..","stages":{"names":[".."],"weights":[1.0]},   # a plain list of names is also accepted
        "lanes":[".."], "start":{"x":1.8,"y":4.7}, "end":{...},
        "nodes":[{"id":"n1","stage":0,"lane":0,"text":"..","kind":"act|doc"}],
        "links":[["n1","n2"],...]}]},   # order of links = skeleton order: main chain first, back-links after
  "b4": {"note":"...", "supp_skip_group": true,
        "layers": {"guide":[{"l1":"..","groups":[{"g":"..","objs":[".."]}]}], "exec":[...], "supp":[...]}},
  "b5": {"roles":[{"key":"PM","level":"Project","name":"Project Manager"}],
        "pages":[{"title":"..","l1s":["Planning","Resourcing"]}],
        "rows":[{"l1":"..","l2":"..","object":"..","c":"PM","u":["SE","QM"]}]}
}

Cross-view consistency checks (ERROR blocks / WARN informs):
  - the three layer labels must equal the labels defined in the profile (profile.layers)
  - L1/L2 of B2 must be identical to B1 (compared level by level)
  - L1 of B4 ⊆ L1 of B1; group names should match L2 names of B1/B2 (WARN)
  - B5 row objects ⊆ B4 objects; l1/l2 must exist in B1; c/u must be valid role keys; c must not appear in u
  - B3 stage names should match the L1 names of the B1 execution layer (WARN)
Outputs: B1/B2/B3/B4/B5 PPTX + business-architecture inventory .xlsx (capabilities/components/objects/role matrix)
"""
import argparse
import json
import math
import os
import sys

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

# ---------- common colour palette ----------
C_LABEL   = RGBColor(0x0D, 0x6F, 0xB8)
C_HEAD    = RGBColor(0x7B, 0xC0, 0xEE)
C_STAGE   = RGBColor(0xAF, 0xDC, 0xF8)
C_CELL_LN = RGBColor(0x9D, 0xC3, 0xE6)
C_INK     = RGBColor(0x1F, 0x4E, 0x79)
C_GRAY    = RGBColor(0x59, 0x59, 0x59)
C_TITLE   = RGBColor(0x0F, 0x2B, 0x5B)
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_LGRAY   = RGBColor(0x7F, 0x7F, 0x7F)
import bizprofile as BP
FONT = "微软雅黑"      # Microsoft YaHei; overwritten by apply_profile() from the profile
EA_FONT = "微软雅黑"  # Microsoft YaHei (East Asian font name)
LANG = "zh"
# ---------- English text fitting (measured with Arial-metric font) ----------
from PIL import ImageFont as _IF
_FP = {False: "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
       True: "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"}
_FC = {}
def text_w(s, size, bold=False):
    """Estimate text width (inches): CJK characters as 1 em, everything else with Arial metrics."""
    f = _FC.get(bold) or _FC.setdefault(bold, _IF.truetype(_FP[bold], 200))
    cjk = sum(1 for c in s if "\u2e80" <= c <= "\u9fff" or "\uff00" <= c <= "\uffef")
    rest = "".join(c for c in s if not ("\u2e80" <= c <= "\u9fff" or "\uff00" <= c <= "\uffef"))
    return (cjk * (1.05 if bold else 1.0) + f.getlength(rest) / 200.0) * size / 72.0
def _wrap(s, size, w, bold):
    out = []
    for para in str(s).split("\n"):
        if " " not in para and any("\u2e80" <= c <= "\u9fff" for c in para):   # CJK text: wrap per character
            cur = ""
            for ch in para:
                if cur and text_w(cur + ch, size, bold) > w:
                    out.append(cur); cur = ch
                else:
                    cur += ch
            out.append(cur)
            continue
        cur = ""
        for word in para.split(" "):
            t = (cur + " " + word).strip()
            if cur and text_w(t, size, bold) > w:
                out.append(cur); cur = word
            else:
                cur = t
        out.append(cur)
    return out
def wrap_fit(s, w, h, sizes, bold=False, lh=1.2, maxlines=9):
    """Largest size whose word-wrapped text fits w x h; returns (size, text with explicit breaks)."""
    for sz in sizes:
        ls = _wrap(s, sz, w, bold)
        if len(ls) <= maxlines and all(text_w(l, sz, bold) <= w for l in ls) \
                and len(ls) * sz * lh / 72.0 <= h + 0.003:
            return sz, "\n".join(ls)
    sz = sizes[-1]
    return sz, "\n".join(_wrap(s, sz, w, bold))

SW, SH = 13.333, 7.5
FIXED_LAYERS = {"guide": "战略管控", "exec": "业务执行", "supp": "综合支撑"}   # keys are fixed; default Chinese labels (Strategic Control / Business Execution / Integrated Support) are replaced by profile.layers
LAYOUT = {   # only a few layout constants depend on the language (English words are longer)
    "zh": dict(b1_rowh=0.29, b1_base=(1.90, 2.26, 1.42), b1_intro=(0.56, 11.5), b1_note=(7.16, 9.5),
               b5_l2w=1.10, b5_obw=1.70),
    "en": dict(b1_rowh=0.34, b1_base=(1.50, 1.90, 1.40), b1_intro=(0.60, 10.5), b1_note=(7.02, 9.0),
               b5_l2w=1.45, b5_obw=1.85),
}


def apply_profile(d):
    """Load language, fonts and layer labels from the profile into module globals; return the profile."""
    global FONT, EA_FONT, LANG
    prof = BP.get(d)
    LANG = prof.get("lang", "zh")
    FONT = prof["branding"].get("font_latin") or FONT
    EA_FONT = prof["branding"].get("font_ea") or EA_FONT
    FIXED_LAYERS.update(prof["layers"])
    if not d.get("series") and prof["branding"].get("series"):
        d["series"] = prof["branding"]["series"]
    import b3_flow
    b3_flow.FONT, b3_flow.EA_FONT = FONT, EA_FONT
    return prof


def L(key):
    return LAYOUT[LANG][key]


# ================= validation =================
def validate(d):
    errors, warns = [], []
    if "layers" not in d or not all(k in d["layers"] for k in FIXED_LAYERS):
        errors.append("missing layers (the B1 three-layer capability framework is the basis of all views)")
        return errors, warns
    for k, v in FIXED_LAYERS.items():
        lab = d["layers"][k].get("label", v)
        if lab != v:
            errors.append("layer labels must match the profile (%s): layer %s currently has label=%s" % ("/".join(FIXED_LAYERS.values()), k, lab))
    for k in FIXED_LAYERS:
        if not d["layers"][k].get("blocks"):
            errors.append("layers.%s.blocks is empty" % k)
    b1 = {k: {b["l1"]: b.get("l2", []) for b in d["layers"][k]["blocks"]} for k in FIXED_LAYERS}

    # B2 consistency
    if "b2" in d:
        for k in FIXED_LAYERS:
            got = {b["l1"]: [x["l2"] for x in b.get("l2s", [])] for b in d["b2"]["layers"][k]}
            if set(got) != set(b1[k]):
                errors.append("B2 layer %s: L1 set differs from B1: extra=%s missing=%s"
                              % (k, sorted(set(got) - set(b1[k])), sorted(set(b1[k]) - set(got))))
                continue
            for l1, l2s in got.items():
                if set(l2s) != set(b1[k][l1]):
                    errors.append("B2 L1 '%s': L2 differs from B1: extra=%s missing=%s"
                                  % (l1, sorted(set(l2s) - set(b1[k][l1])), sorted(set(b1[k][l1]) - set(l2s))))
            for b in d["b2"]["layers"][k]:
                for x in b.get("l2s", []):
                    if not x.get("comps"):
                        warns.append("B2 L2 '%s' has no components" % x["l2"])

    # B4 consistency
    b4_objs = set()
    if "b4" in d:
        for k in FIXED_LAYERS:
            for b in d["b4"]["layers"][k]:
                if b["l1"] not in b1[k]:
                    errors.append("B4 layer %s: L1 '%s' is not in B1" % (k, b["l1"]))
                l2set = set(b1[k].get(b["l1"], []))
                for g in b.get("groups", []):
                    if g["g"] not in l2set:
                        warns.append("B4 group '%s' (%s/%s) is not an L2 name of B1" % (g["g"], k, b["l1"]))
                    for o in g.get("objs", []):
                        if o in b4_objs:
                            errors.append("B4 duplicate object name: %s" % o)
                        b4_objs.add(o)

    # B5 consistency
    if "b5" in d:
        roles = {r["key"] for r in d["b5"]["roles"]}
        all_l1 = {l1 for k in FIXED_LAYERS for l1 in b1[k]}
        l2_of = {}
        for k in FIXED_LAYERS:
            for l1, l2s in b1[k].items():
                for l2 in l2s:
                    l2_of[l2] = l1
        seen = set()
        for row in d["b5"]["rows"]:
            o = row["object"]
            if "b4" in d and o not in b4_objs:
                errors.append("B5 object '%s' is not in the B4 object set" % o)
            if o in seen:
                errors.append("B5 object appears more than once: %s" % o)
            seen.add(o)
            if row["l1"] not in all_l1:
                errors.append("B5 row l1 '%s' is not in B1 (object %s)" % (row["l1"], o))
            if l2_of.get(row["l2"]) != row["l1"]:
                errors.append("B5 row l2 '%s' does not belong to l1 '%s' (object %s)" % (row["l2"], row["l1"], o))
            if row["c"] not in roles:
                errors.append("B5 object '%s': invalid C role key: %s" % (o, row["c"]))
            for u in row.get("u", []):
                if u not in roles:
                    errors.append("B5 object '%s': invalid U role key: %s" % (o, u))
            if row["c"] in row.get("u", []):
                errors.append("B5 object '%s': the C role also appears in U" % o)

    # B3 consistency
    if "b3" in d:
        exec_l1 = set(b1["exec"])
        for pg in d["b3"]["pages"]:
            st = pg["stages"]
            names = st["names"] if isinstance(st, dict) else st
            for s in names:
                if s not in exec_l1:
                    warns.append("B3 stage '%s' is not an L1 of the B1 execution layer" % s)
            nstage, nlane = len(names), len(pg["lanes"])
            ids = set()
            for n in pg["nodes"]:
                if not (0 <= n["stage"] < nstage):
                    errors.append("B3 node %s: stage out of range" % n["id"])
                if not (0 <= n["lane"] < nlane):
                    errors.append("B3 node %s: lane out of range" % n["id"])
                ids.add(n["id"])
            for a, b in pg["links"]:
                if a not in ids or b not in ids:
                    errors.append("B3 link refers to a non-existent node: %s->%s" % (a, b))
    return errors, warns


# ================= drawing helpers =================
CUR = {}


def toolkit(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    def set_font(run, size, bold=False, color=C_INK):
        f = run.font
        f.size = Pt(size); f.bold = bold; f.name = FONT; f.color.rgb = color
        rPr = run._r.get_or_add_rPr()
        ea = rPr.find(qn('a:ea'))
        if ea is None:
            ea = rPr.makeelement(qn('a:ea'), {}); rPr.append(ea)
        ea.set('typeface', EA_FONT)

    def add_text(x, y, w, h, text, size, bold=False, color=C_INK,
                 align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, wrap=True):
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = wrap
        tf.margin_left = tf.margin_right = Inches(0.02)
        tf.margin_top = tf.margin_bottom = Inches(0.005)
        tf.vertical_anchor = anchor
        for i, ln in enumerate(text.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run(); r.text = ln
            set_font(r, size, bold, color)
        return tb

    def add_rect(x, y, w, h, text, size, fill, line=None, bold=False, lnw=0.4,
                 fc=C_INK, wrap=False, align=PP_ALIGN.CENTER, fit=None, lh=1.2, maxlines=9):
        if fit and text:
            size, text = wrap_fit(text, w - 0.05, h, fit, bold, lh=lh, maxlines=maxlines)
        sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill is None: sp.fill.background()
        else: sp.fill.solid(); sp.fill.fore_color.rgb = fill
        if line is None: sp.line.fill.background()
        else: sp.line.color.rgb = line; sp.line.width = Pt(lnw)
        sp.shadow.inherit = False
        tf = sp.text_frame
        tf.word_wrap = wrap
        tf.margin_left = tf.margin_right = Inches(0.006)
        tf.margin_top = tf.margin_bottom = Inches(0)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        for i, ln in enumerate(text.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run(); r.text = ln
            set_font(r, size, bold, fc)
        return sp

    def add_shape(x, y, w, h, shape, text, size, fill, line=None, lnw=0.75,
                  fc=C_WHITE, bold=True):
        sp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill is None: sp.fill.background()
        else: sp.fill.solid(); sp.fill.fore_color.rgb = fill
        if line is None: sp.line.fill.background()
        else: sp.line.color.rgb = line; sp.line.width = Pt(lnw)
        sp.shadow.inherit = False
        tf = sp.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.01)
        tf.margin_top = tf.margin_bottom = Inches(0)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        for i, ln in enumerate(text.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run(); r.text = ln
            set_font(r, size, bold, fc)
        return sp

    def band_label(x, y, h, text, color=C_LABEL, w=0.66, fs=14):
        sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        sp.fill.solid(); sp.fill.fore_color.rgb = color
        sp.line.fill.background(); sp.shadow.inherit = False
        tf = sp.text_frame
        tf.word_wrap = False
        tf._txBody.bodyPr.set('vert', 'eaVert')
        tf.margin_left = tf.margin_right = Inches(0.004)
        tf.margin_top = tf.margin_bottom = Inches(0.008)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        lines = [text]
        if text_w(text, 9, True) > h - 0.12 and " " in text:
            lines = text.split(" ", 1)
        for s_ in (fs, 13, 12, 11, 10, 9, 8, 7.5, 7, 6.5, 6):
            if max(text_w(l, s_, True) for l in lines) <= h - 0.12: fs = s_; break
        for k, l in enumerate(lines):
            if k: p = tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
            r = p.add_run(); r.text = l
            set_font(r, fs, True, C_WHITE)
        return sp

    def band_frame(x, y, w, h, color=C_LABEL):
        sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        sp.fill.background()
        sp.line.color.rgb = color; sp.line.width = Pt(1.0)
        sp.shadow.inherit = False
        return sp

    def seg(x1, y1, x2, y2, head=True, color=RGBColor(0x9E, 0x30, 0x39)):
        ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                        Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        ln.line.color.rgb = color; ln.line.width = Pt(1.1); ln.shadow.inherit = False
        if head:
            lnPr = ln.line._get_or_add_ln()
            lnPr.append(lnPr.makeelement(qn('a:tailEnd'),
                                         {'type': 'triangle', 'w': 'med', 'len': 'med'}))
        return ln

    def page_head(domain, series, view_title):
        add_text(8.62, 0.12, 4.23, 0.28, BP.T(CUR, "head_right", series=series, domain=domain),
                 8.5, False, C_LGRAY, align=PP_ALIGN.RIGHT)
        fs = 17
        for fs in (17, 16, 15, 14, 13, 12, 11):
            if text_w(view_title, fs, True) <= 7.9:
                break
        add_text(0.46, 0.08, 8.0, 0.42, view_title, fs, True, C_TITLE)

    return slide, dict(set_font=set_font, add_text=add_text, add_rect=add_rect,
                       add_shape=add_shape, band_label=band_label, band_frame=band_frame,
                       seg=seg, page_head=page_head)


def new_prs():
    prs = Presentation()
    prs.slide_width = Inches(SW); prs.slide_height = Inches(SH)
    return prs


# ================= B1 capability framework =================
def build_b1(d, out):
    prs = new_prs(); slide, tk = toolkit(prs)
    domain = d["domain"]; series = d.get("series", "")
    tk["page_head"](domain, series, BP.T(d, "b1_title", domain=domain))
    intro = d.get("intro", [])
    if intro:
        _fs, _txt = wrap_fit("\n".join(intro), 12.36, 0.54, [L("b1_intro")[1], 11, 10.5, 10, 9.5, 9], True, lh=1.18)
        tk["add_text"](0.46, L("b1_intro")[0], 12.42, 0.56, _txt, _fs, True, C_INK)

    BX, BW, LX = 1.17, 11.79, 0.38
    ROWH, ROWG, SUBG = L("b1_rowh"), 0.03, 0.05

    def layer_h(key, base):
        blocks = d["layers"][key]["blocks"]
        n = max((math.ceil(len(b.get("l2", [])) / 2) for b in blocks), default=0)
        return max(base, 0.16 + 0.38 + 0.06 + n * (ROWH + ROWG))

    def draw_layer(y, h, key, head_fill, head_size=13.5, cell_size=11.5):
        lay = d["layers"][key]
        tk["band_label"](LX, y, h, lay["label"])
        tk["band_frame"](BX, y, BW, h)
        blocks = lay["blocks"]; cols = len(blocks)
        colw = (BW - 0.16 - (cols - 1) * 0.08) / cols
        for i, b in enumerate(blocks):
            x = BX + 0.08 + i * (colw + 0.08)
            tk["add_rect"](x, y + 0.08, colw, 0.38, b["l1"], head_size, head_fill, bold=True,
                           fit=(head_size, 13, 12.5, 12, 11.5, 11, 10.5, 10))
            l2s = b.get("l2", []); n = len(l2s); nleft = math.ceil(n / 2)
            subw = (colw - SUBG) / 2
            for j, item in enumerate(l2s):
                col = 0 if j < nleft else 1
                row = j if col == 0 else j - nleft
                tk["add_rect"](x + col * (subw + SUBG), y + 0.52 + row * (ROWH + ROWG),
                               subw, ROWH, item, cell_size, C_WHITE, line=C_CELL_LN,
                               fit=(cell_size, 11, 10.5, 10, 9.5, 9, 8.5, 8, 7.5), lh=1.15)

    gb, eb, sb = L("b1_base"); gh = layer_h("guide", gb); eh = layer_h("exec", eb); sh = layer_h("supp", sb)
    gap = 0.09 if gh + eh + sh + 0.18 <= 6.86 else max(0.04, (6.86 - gh - eh - sh) / 2)
    gy = 1.16; ey = gy + gh + gap; sy = ey + eh + gap
    draw_layer(gy, gh, "guide", C_HEAD)
    draw_layer(ey, eh, "exec", C_STAGE, head_size=13, cell_size=12)
    draw_layer(sy, sh, "supp", C_HEAD, head_size=13, cell_size=12)
    note = d.get("note", "")
    if note:
        tk["add_text"](0.46, L("b1_note")[0], 12.42, 0.40, note, L("b1_note")[1], False, C_GRAY)
    prs.save(out); return out


# ================= B2 business components =================
C_L2HEAD = RGBColor(0xD5, 0xB5, 0xA7)
C_COMP   = RGBColor(0xDA, 0xEA, 0xF8)
C_COMP_LN= RGBColor(0xB8, 0xD4, 0xF0)
C_SHARED = RGBColor(0xA7, 0xC8, 0xA7)
C_GREEN  = RGBColor(0x54, 0x82, 0x35)
ROW2, L2H, RGAP, BGAP = 0.135, 0.15, 0.01, 0.02

def build_b2(d, out):
    prs = new_prs(); slide, tk = toolkit(prs)
    domain = d["domain"]; series = d.get("series", "")
    tk["page_head"](domain, series, BP.T(d, "b2_title", domain=domain))

    BX, BW, LX = 1.14, 12.12, 0.40

    def comp_font(txt, w):
        for s in (7.0, 6.5, 6.0, 5.5, 5.0, 4.5):
            if text_w(txt, s) <= w - 0.03: return s
        return 4.5

    def block_h(n):
        ccols = 2 if n > 3 else 1
        return L2H + 0.012 + math.ceil(n / ccols) * (ROW2 + RGAP) + BGAP

    def render_group(x0, y0, w, avail, l1, l2s, l1_fill, fs=10.5):
        tk["add_rect"](x0, y0, w, 0.22, l1, fs, l1_fill, bold=True, fit=(fs, 10, 9.5, 9, 8.5, 8, 7.5, 7), lh=1.0, maxlines=1)
        ys = y0 + 0.26; av = avail - 0.26
        blocks = [(x["l2"], [ (c["name"], c.get("shared", False)) for c in x["comps"]]) for x in l2s]
        heights = [block_h(len(c)) for _, c in blocks]
        ncols = 1
        while ncols <= 4:
            colw = (w - 0.02 - (ncols - 1) * 0.05) / ncols
            cols = [[] for _ in range(ncols)]; colh = [0.0] * ncols; ci = 0
            for (l2, comps), h in zip(blocks, heights):
                placed = False
                for k in range(ci, ncols):
                    if colh[k] + h <= av + 0.001:
                        cols[k].append((l2, comps, h)); colh[k] += h; placed = True; break
                if not placed:
                    if ci + 1 < ncols:
                        ci += 1; cols[ci].append((l2, comps, h)); colh[ci] += h
                    else:
                        cols[ncols - 1].append((l2, comps, h)); colh[ncols - 1] += h
            if max(colh) <= av + 0.001 or ncols == 4: break
            ncols += 1
        for ci, col in enumerate(cols):
            if not col: continue
            cx = x0 + 0.01 + ci * (colw + 0.05); cy = ys
            for l2, comps, h in col:
                tk["add_rect"](cx, cy, colw, L2H, l2, 6.5, C_L2HEAD, fit=(6.5, 6, 5.5, 5, 4.5), lh=1.0, maxlines=1)
                n = len(comps); ccols = 2 if n > 3 else 1
                cw = (colw - 0.008 - (ccols - 1) * 0.025) / ccols
                nrows = math.ceil(n / ccols)
                for k, (c, shd) in enumerate(comps):
                    col_i = k // nrows; row_i = k % nrows
                    tk["add_rect"](cx + col_i * (cw + 0.025), cy + L2H + 0.012 + row_i * (ROW2 + RGAP),
                                   cw, ROW2, c, comp_font(c, cw), C_SHARED if shd else C_COMP,
                                   line=C_COMP_LN)
                cy += h
        return (max(colh) + 0.26) if any(cols) else 0.26

    # three layers (adaptive height: by each layer's tallest group)
    def layer_geometry(key):
        lay = d["b2"]["layers"][key]
        maxh = 0.0
        for b in lay:
            hs = sum(block_h(len(x["comps"])) for x in b["l2s"])
            # if a single column cannot hold everything, estimate with the engine: start with 4 sub-columns
            hl = [block_h(len(x["comps"])) for x in b["l2s"]]
            n_ = len(hl)
            if key == "supp":
                best = min(max(sum(hl[:i]), sum(hl[i:j]), sum(hl[j:]))
                           for i in range(n_ + 1) for j in range(i, n_ + 1))
            else:
                best = min(max(sum(hl[:i]), sum(hl[i:])) for i in range(n_ + 1))
            maxh = max(maxh, 0.26 + best)
        return maxh + 0.11

    gh = layer_geometry("guide"); eh = layer_geometry("exec"); sh = layer_geometry("supp")
    total = gh + eh + sh
    avail = 6.74 - 0.62 - 0.16
    if total > avail:  # scale down proportionally
        k = avail / total; gh *= k; eh *= k; sh *= k
    else:
        k = 1 + (avail - total) / total; gh *= k; eh *= k; sh *= k
    gy = 0.62; ey = gy + gh + 0.08; sy = ey + eh + 0.08

    tk["band_label"](LX, gy, gh, d["layers"]["guide"]["label"])
    tk["band_frame"](BX, gy, BW, gh)
    g = d["b2"]["layers"]["guide"]; n = len(g)
    w = (BW - 0.12 - (n - 1) * 0.08) / n
    for i, b in enumerate(g):
        render_group(BX + 0.06 + i * (w + 0.08), gy + 0.05, w, gh - 0.10, b["l1"], b["l2s"], C_STAGE)

    tk["band_label"](LX, ey, eh, d["layers"]["exec"]["label"])
    tk["band_frame"](BX, ey, BW, eh)
    g = d["b2"]["layers"]["exec"]; n = len(g)
    w = (BW - 0.12 - (n - 1) * 0.06) / n
    for i, b in enumerate(g):
        render_group(BX + 0.06 + i * (w + 0.06), ey + 0.05, w, eh - 0.10, b["l1"], b["l2s"], C_STAGE)

    tk["band_label"](LX, sy, sh, d["layers"]["supp"]["label"], color=C_GREEN)
    tk["band_frame"](BX, sy, BW, sh)
    g = d["b2"]["layers"]["supp"]; n = len(g)
    wt = [max(2, len(b["l2s"])) for b in g]
    ws_ = [(BW - 0.12 - (n - 1) * 0.07) * t / sum(wt) for t in wt]
    for i, b in enumerate(g):
        render_group(BX + 0.06 + sum(ws_[:i]) + i * 0.07, sy + 0.04, ws_[i], sh - 0.08, b["l1"], b["l2s"], C_GREEN, fs=10)

    tk["add_rect"](0.46, 6.82, 0.20, 0.14, "", 6, C_COMP, line=C_COMP_LN)
    tk["add_text"](0.70, 6.79, 2.8, 0.2, BP.T(d, "b2_legend"), 8, False, C_GRAY)
    tk["add_text"](3.80, 6.79, 9.2, 0.2, BP.T(d, "b2_shared"),
                   8, False, C_GRAY)
    note = d["b2"].get("note", "")
    if note:
        tk["add_text"](0.46, 7.04, 12.6, 0.42, note, 9, False, C_GRAY)
    prs.save(out); return out


# ================= B3 value streams (swimlanes) =================
C_STAGE3 = RGBColor(0x4B, 0xAC, 0xC6)
C_LANE_BG = RGBColor(0xFF, 0xFF, 0xEB)
C_LANE_LN = RGBColor(0x66, 0x66, 0x66)
C_FLOW = RGBColor(0x9E, 0x30, 0x39)

def build_b3(d, out):
    """B3 is delegated entirely to b3_flow (single connectors + port gluing + scored routing + parallel-track separation).

    The old naive approach here ("one line per segment") could not guarantee arrow direction, avoid merged lines or box crossings,
    and has been retired. Layout and routing rules: see b3-flow-spec.md.
    """
    import b3_flow
    return b3_flow.build_b3_stream(d, out)


# ================= B4 business objects =================
C_CELL4  = RGBColor(0xDC, 0xE7, 0xF2)
C_GREEN4 = RGBColor(0x4E, 0x8B, 0x2E)
C_GL2    = RGBColor(0xEA, 0xEA, 0xEA)

def build_b4(d, out):
    prs = new_prs(); slide, tk = toolkit(prs)
    domain = d["domain"]; series = d.get("series", "")
    n_all = sum(len(g["objs"]) for k in FIXED_LAYERS
                for b in d["b4"]["layers"][k] for g in b["groups"])
    tk["page_head"](domain, series,
                    BP.T(d, "b4_title", domain=domain, n=n_all))
    BX, BW, LX = 1.10, 12.16, 0.40
    skip = d["b4"].get("supp_skip_group", True)

    def dom_h(b, skip_group):
        y = 0.33 if not skip_group else 0.30
        for g in b["groups"]:
            objs = g["objs"]; n = len(objs)
            ccols = 3 if (skip_group or n >= 8) else (2 if n > 2 else 1)
            if not skip_group: y += 0.185
            y += math.ceil(n / ccols) * 0.16 + 0.008
        return y + 0.04

    def render_band(y0, h, key, hd_fill, label_color=C_LABEL):
        lay = d["b4"]["layers"][key]; skip_group = (key == "supp" and skip)
        tk["band_label"](LX, y0, h, d["layers"][key]["label"], color=label_color, w=0.60, fs=11.5)
        tk["band_frame"](BX, y0, BW, h)
        n = len(lay)
        weights = [max(len(g["objs"]) for g in b["groups"]) for b in lay]
        tw = sum(weights)
        dws = [(BW - 0.10 - (n - 1) * 0.06) * w / tw for w in weights]
        for i, b in enumerate(lay):
            dw = dws[i]; x = BX + 0.05 + sum(dws[:i]) + i * 0.06
            tk["add_rect"](x, y0 + 0.04, dw, 0.24, b["l1"], 10, hd_fill, fc=C_WHITE, bold=True, fit=(10, 9.5, 9, 8.5, 8, 7.5, 7), lh=1.0, maxlines=1)
            y = y0 + (0.30 if skip_group else 0.33)
            for g in b["groups"]:
                objs = g["objs"]; no = len(objs)
                if not skip_group:
                    tk["add_rect"](x, y, dw, 0.17, g["g"], 7, C_GL2,
                                   line=RGBColor(0xCC, 0xCC, 0xCC), fit=(7, 6.5, 6, 5.5, 5), lh=1.0, maxlines=1)
                    y += 0.185
                ccols = min(3, no) if skip_group else (3 if no >= 8 else (2 if no > 2 else 1))
                cw = (dw - 0.02 - (ccols - 1) * 0.03) / ccols
                for fs in (7.0, 6.5, 6.0, 5.5, 5.0, 4.5):
                    if max(text_w(o, fs) for o in objs) <= cw - 0.04: break
                nrows = math.ceil(no / ccols)
                for k, o in enumerate(objs):
                    col = k // nrows; row = k % nrows
                    tk["add_rect"](x + 0.005 + col * (cw + 0.03), y + row * 0.16, cw, 0.15,
                                   o, fs, C_CELL4, line=C_CELL_LN)
                y += nrows * 0.16 + 0.008

    gh = max(dom_h(b, False) for b in d["b4"]["layers"]["guide"]) + 0.06
    eh = max(dom_h(b, False) for b in d["b4"]["layers"]["exec"])
    sh = max(dom_h(b, True) for b in d["b4"]["layers"]["supp"]) + 0.02
    total = gh + eh + sh
    avail = 7.30 - 0.50
    if total > avail:
        k = avail / total; gh *= k; eh *= k; sh *= k
        warns_scale = True
    else:
        warns_scale = False
    gy = 0.50; ey = gy + gh + 0.06; sy = ey + eh + 0.06
    render_band(gy, gh, "guide", RGBColor(0x7B, 0xB0, 0x5E))
    render_band(ey, eh, "exec", RGBColor(0x2E, 0x75, 0xB6))
    render_band(sy, sh, "supp", RGBColor(0x8F, 0xB8, 0x74), label_color=C_GREEN4)
    LY = 7.36
    tk["add_rect"](0.46, LY, 0.20, 0.12, "", 6.5, C_CELL4, line=C_CELL_LN)
    tk["add_text"](0.74, LY, 2.4, 0.10, BP.T(d, "b4_legend", n=n_all), 7.5, False, C_GRAY)
    note = d["b4"].get("note", "")
    if note:
        tk["add_text"](3.30, LY, 9.7, 0.10, note, 7.5, False, C_GRAY)
    if warns_scale:
        print("[WARN] B4: total height of the three layers exceeds the slide; scaled down to %.0f%% - consider fewer objects or groups" % (k * 100))
    prs.save(out); return out


# ================= B5 object-role matrix =================
C_C5 = RGBColor(0xC7, 0xDC, 0xF1)
C_HDR5 = RGBColor(0x0D, 0x6F, 0xB8)
C_L2_5 = RGBColor(0xEA, 0xEA, 0xEA)
C_LINE5 = RGBColor(0xBF, 0xBF, 0xBF)

def build_b5(d, out):
    prs = new_prs()
    domain = d["domain"]; series = d.get("series", "")
    roles = d["b5"]["roles"]; ncol = len(roles)
    per_page = BP.get(d)["limits"]["b5_rows_per_page"]
    vpages = []
    for pg in d["b5"]["pages"]:
        rows_all = [r for r in d["b5"]["rows"] if r["l1"] in pg["l1s"]]
        if not rows_all:
            print("[WARN] B5 page '%s' has no matching rows" % pg["title"]); continue
        chunks = [rows_all[i:i + per_page] for i in range(0, len(rows_all), per_page)]
        for ci, ch in enumerate(chunks, 1):
            t = pg["title"] + (BP.T(d, "page_suffix", i=ci, n=len(chunks)) if len(chunks) > 1 else "")
            vpages.append((t, ch))
    for ptitle, rows in vpages:
        slide, tk = toolkit(prs)
        tk["page_head"](domain, series, BP.T(d, "b5_title", domain=domain, title=ptitle))
        RCW, L2W, OBW = 0.42, L("b5_l2w"), L("b5_obw")
        X0 = 0.46
        total_w = 0.30 + L2W + OBW + ncol * RCW
        rcw = min(0.62, (12.87 - X0 - 0.30 - L2W - OBW) / ncol)
        # two header rows: level row + role row
        hy = 0.62
        tk["add_rect"](X0, hy, 0.30, 0.24, "", 8, C_HDR5)
        tk["add_rect"](X0 + 0.30, hy, L2W, 0.24, BP.T(d, "b5_cols")[0], 9, C_HDR5, fc=C_WHITE)
        tk["add_rect"](X0 + 0.30 + L2W, hy, OBW, 0.24, BP.T(d, "b5_cols")[1], 9, C_HDR5, fc=C_WHITE)
        x = X0 + 0.30 + L2W + OBW
        # level colour bars
        lvls = []
        for r in roles:
            if not lvls or lvls[-1][0] != r["level"]:
                lvls.append([r["level"], 1])
            else:
                lvls[-1][1] += 1
        xx = x
        for i, (lv, cnt) in enumerate(lvls):
            fill = RGBColor(0xDB, 0xE8, 0xCE) if i % 2 == 0 else RGBColor(0xD2, 0xE4, 0xFA)
            tk["add_rect"](xx, hy, cnt * rcw, 0.24, lv, 9, fill, bold=True, fit=(9, 8.5, 8, 7.5, 7), lh=1.0, maxlines=1)
            xx += cnt * rcw
        for i, r in enumerate(roles):
            tk["add_rect"](x + i * rcw, hy + 0.26, rcw, 0.34,
                           r["name"].replace("\\n", "\n"), 7.5, C_HDR5, fc=C_WHITE, fit=(7.5, 7, 6.5, 6, 5.5), lh=1.1)
        # rows
        ry = hy + 0.62
        rh = 0.26
        cur_l1 = None; l1_y0 = None; l1_rows = 0
        rkeys = [r["key"] for r in roles]

        def vlabel(y0, n, text):
            sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(X0), Inches(y0),
                                        Inches(0.30), Inches(n * rh))
            sp.fill.solid(); sp.fill.fore_color.rgb = C_STAGE3
            sp.line.color.rgb = C_HDR5; sp.line.width = Pt(0.75); sp.shadow.inherit = False
            tf = sp.text_frame; tf.word_wrap = False
            tf._txBody.bodyPr.set('vert', 'eaVert' if LANG == 'zh' else 'vert270')
            tf.margin_left = tf.margin_right = Inches(0.01)
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            r = p.add_run(); r.text = text
            fs_ = 6
            for s_ in (9, 8.5, 8, 7.5, 7, 6.5, 6):
                if text_w(text, s_, True) <= n * rh - 0.08: fs_ = s_; break
            tk["set_font"](r, fs_, True, C_INK)
        supp_l1s = {b["l1"] for b in d["layers"]["supp"]["blocks"]}
        for row in rows:
            gk = d["layers"]["supp"]["label"] if row["l1"] in supp_l1s else row["l1"]
            if gk != cur_l1:
                if cur_l1 is not None:
                    vlabel(l1_y0, l1_rows, cur_l1)
                cur_l1 = gk; l1_y0 = ry; l1_rows = 0
            tk["add_rect"](X0 + 0.30, ry, L2W, rh, row["l2"], 8, C_L2_5, line=C_LINE5, fit=(8, 7.5, 7, 6.5, 6), lh=1.1)
            tk["add_rect"](X0 + 0.30 + L2W, ry, OBW, rh, row["object"], 9, C_WHITE, line=C_LINE5, fit=(9, 8.5, 8, 7.5, 7, 6.5), lh=1.1)
            uset = set(row.get("u", []))
            for i, k in enumerate(rkeys):
                if k == row["c"]:
                    tk["add_rect"](x + i * rcw, ry, rcw, rh, "C", 9, C_C5, line=C_LINE5, bold=True)
                elif k in uset:
                    tk["add_rect"](x + i * rcw, ry, rcw, rh, "U", 9, C_WHITE, line=C_LINE5,
                                   fc=C_GRAY)
                else:
                    tk["add_rect"](x + i * rcw, ry, rcw, rh, "", 8, C_WHITE, line=C_LINE5)
            ry += rh; l1_rows += 1
        if cur_l1 is not None:
            vlabel(l1_y0, l1_rows, cur_l1)
        # legend
        ly = min(7.20, ry + 0.08)
        tk["add_rect"](X0, ly, 0.20, 0.14, "C", 8, C_C5, line=C_LINE5, bold=True)
        tk["add_text"](X0 + 0.24, ly - 0.02, 2.2, 0.2, BP.T(d, "b5_legend")[0], 8, False, C_GRAY)
        tk["add_rect"](X0 + 2.2, ly, 0.20, 0.14, "U", 8, C_WHITE, line=C_LINE5, fc=C_GRAY)
        tk["add_text"](X0 + 2.44, ly - 0.02, 2.2, 0.2, BP.T(d, "b5_legend")[1], 8, False, C_GRAY)
        tk["add_text"](X0 + 4.6, ly - 0.02, 8.0, 0.2,
                       BP.T(d, "b5_legend")[2], 8, False, C_GRAY)
    prs.save(out); return out


# ================= inventory xlsx =================
def build_lists_xlsx(d, out):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = Workbook()
    HEADF = '0F2B5B'; INKX = '1F4E79'
    thin = Side(style='thin', color='9DC3E6')
    BOR = Border(left=thin, right=thin, top=thin, bottom=thin)
    Fx = FONT

    def sheet(ws, title, headers, rows, widths):
        t = ws.cell(1, 1, title)
        t.font = Font(name=Fx, size=13, bold=True, color=HEADF)
        for c, h in enumerate(headers, 1):
            cell = ws.cell(3, c, h)
            cell.font = Font(name=Fx, size=10.5, bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=HEADF)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = BOR
        for ri, row in enumerate(rows, 4):
            for c, v in enumerate(row, 1):
                cell = ws.cell(ri, c, v)
                cell.font = Font(name=Fx, size=10, color=INKX)
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                cell.border = BOR
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[chr(64 + i)].width = w
        ws.freeze_panes = 'A4'

    # capability list
    ws = wb.active; ws.title = BP.X(d, "cap")
    rows = []
    for k in FIXED_LAYERS:
        for b in d["layers"][k]["blocks"]:
            for l2 in b.get("l2", []):
                rows.append([d["layers"][k]["label"], b["l1"], l2])
    sheet(ws, BP.X(d, "cap_t", domain=d["domain"]), BP.X(d, "cap_h"), rows, [20, 26, 34])

    # component list
    if "b2" in d:
        ws = wb.create_sheet(BP.X(d, "comp"))
        rows = []
        for k in FIXED_LAYERS:
            for b in d["b2"]["layers"][k]:
                for x in b["l2s"]:
                    for c in x["comps"]:
                        rows.append([d["layers"][k]["label"], b["l1"], x["l2"],
                                     c["name"], BP.X(d, "yes") if c.get("shared") else ""])
        sheet(ws, BP.X(d, "comp_t", domain=d["domain"]), BP.X(d, "comp_h"), rows, [20, 26, 34, 38, 16])

    # object list
    if "b4" in d:
        ws = wb.create_sheet(BP.X(d, "obj"))
        rows = []
        for k in FIXED_LAYERS:
            for b in d["b4"]["layers"][k]:
                for g in b["groups"]:
                    for o in g["objs"]:
                        rows.append([d["layers"][k]["label"], b["l1"], g["g"], o])
        sheet(ws, BP.X(d, "obj_t", domain=d["domain"]), BP.X(d, "obj_h"), rows, [20, 26, 34, 36])

    # role-matrix list
    if "b5" in d:
        ws = wb.create_sheet(BP.X(d, "mx"))
        rk = {r["key"]: "%s · %s" % (r["level"], r["name"].replace("-\n", "").replace("\n", " ")) for r in d["b5"]["roles"]}
        rows = []
        for row in d["b5"]["rows"]:
            rows.append([row["l1"], row["l2"], row["object"],
                         rk.get(row["c"], row["c"]),
                         BP.X(d, "sep").join(rk.get(u, u) for u in row.get("u", []))])
        sheet(ws, BP.X(d, "mx_t", domain=d["domain"]), BP.X(d, "mx_h"), rows, [24, 32, 34, 30, 70])
    wb.save(out); return out


# ================= main entry =================
BUILDERS = {"b1": build_b1, "b2": build_b2, "b3": build_b3, "b4": build_b4, "b5": build_b5}
NAMES = {"b1": "B1-Capability Framework", "b2": "B2-Business Components", "b3": "B3-End-to-End Value Streams",
         "b4": "B4-Business Objects", "b5": "B5-Object-Role Matrix"}


def stamp_draft(path, d):
    """Draft mode: add a semi-transparent diagonal watermark to every slide (takes no layout space, does not cover content)."""
    prs = Presentation(path)
    text = BP.T(d, "watermark")
    for slide in prs.slides:
        tb = slide.shapes.add_textbox(Inches(2.2), Inches(3.05), Inches(9.0), Inches(1.4))
        tb.rotation = -18
        tf = tb.text_frame; tf.word_wrap = False
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = text
        f = r.font; f.size = Pt(54); f.bold = True; f.name = FONT
        f.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        clr = r._r.get_or_add_rPr().find(qn("a:solidFill")).find(qn("a:srgbClr"))
        alpha = clr.makeelement(qn("a:alpha"), {"val": "22000"}); clr.append(alpha)
        rPr = r._r.get_or_add_rPr()
        ea = rPr.makeelement(qn("a:ea"), {"typeface": FONT}); rPr.append(ea)
    prs.save(path)


def add_issue_sheet(xlsx, items, mode, d):
    """Append an "Open Issues" sheet to the inventory xlsx; in draft mode, add a note under every sheet title."""
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = load_workbook(xlsx)
    if mode == "draft":
        for ws in wb.worksheets:
            c = ws.cell(2, 1, BP.X(d, "draft"))
            c.font = Font(bold=True, color="C00000")
    ws = wb.create_sheet(BP.X(d, "issues"))
    hdr = BP.X(d, "issues_h")
    ws.cell(1, 1, BP.X(d, "issues_t", mode=mode)).font = Font(bold=True, size=13)
    for i, h in enumerate(hdr, 1):
        c = ws.cell(3, i, h); c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="0F2B5B")
    fill = {"ERROR": "F8CBAD", "CONFLICT": "FFE699", "WARN": "FFFFFF", "RULED": "E2EFDA", "INFO": "F2F2F2"}
    import model_rules as MR
    rows = sorted(items, key=lambda x: (MR.ORDER[x["level"]], x["view"], x["code"]))
    for ri, it in enumerate(rows, 4):
        vals = [it["level"], it["code"], it["view"], it["subject"], it["message"], it["pattern"], it["to"]]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(ri, ci, v)
            c.alignment = Alignment(wrap_text=True, vertical="center")
            c.fill = PatternFill("solid", fgColor=fill[it["level"]])
    for col, w in zip("ABCDEFG", [10, 13, 6, 36, 70, 12, 10]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A4"
    wb.save(xlsx)


def main():
    import model_rules as MR
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--views", default="b1,b2,b3,b4,b5,lists",
                    help="comma-separated: b1,b2,b3,b4,b5,lists (lists = inventory xlsx)")
    ap.add_argument("--registry", default=None, help="cross-domain shared-object registry (governance.md §3)")
    ap.add_argument("--rulings", default=os.path.join(here, "..", "rulings.json"))
    ap.add_argument("--manifest", default=None, help="input manifest inputs.json (default: provenance.manifest)")
    ap.add_argument("--profile", default=None, help="method profile: a name under profiles/ or a json path (default: biz_data.profile)")
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        d = json.load(f)
    BP.load(d, args.profile)
    prof = apply_profile(d)
    global CUR
    CUR = d
    print("profile: %s (lang=%s)" % (prof["_name"], prof["lang"]))
    errors, warns = validate(d)
    for w in warns:
        print("[WARN] %s" % w)
    if errors:
        for e in errors:
            print("[ERROR] %s" % e)
        sys.exit(1)
    mode, blocked, items = MR.run(d, args.data, args.registry, args.rulings, args.manifest)
    MR.print_issues(items)
    hard = [it for it in items if it["level"] == "ERROR" and it["code"] != "CON-MISS"]
    if hard:
        print("[ERROR] content rules failed (see above); no views generated")
        sys.exit(1)
    os.makedirs(args.outdir, exist_ok=True)
    print("conflicts:", MR.write_conflicts(items, args.outdir, mode))
    todo = [v.strip() for v in args.views.split(",") if v.strip()]
    for v in todo:
        if v == "lists":
            fn = BP.T(d, "files"); out = os.path.join(args.outdir, fn["fmt"].format(name=fn["lists"], domain=d["domain"]) + ".xlsx")
            build_lists_xlsx(d, out)
            add_issue_sheet(out, items, mode, d)
            print("saved:", out)
        elif v in BUILDERS:
            if v != "b1" and v not in d:
                print("[SKIP] data has no %s section; skipped" % v); continue
            if v in blocked:
                print("[SKIP] %s lacks required input materials (see CON-MISS); not generated" % v.upper()); continue
            fn = BP.T(d, "files"); out = os.path.join(args.outdir, fn["fmt"].format(name=fn[v], domain=d["domain"]) + ".pptx")
            BUILDERS[v](d, out)
            if mode == "draft":
                stamp_draft(out, d)
            print("saved:", out)
        else:
            print("[ERROR] unknown view: %s" % v); sys.exit(1)
    if blocked:
        sys.exit(2)


if __name__ == "__main__":
    main()
