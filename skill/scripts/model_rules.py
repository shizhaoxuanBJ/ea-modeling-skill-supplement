# -*- coding: utf-8 -*-
"""Content-rule validation (added in v3): input contract / code-checkable negative patterns from the judgment library / cross-domain registry / governance rulings.

Division of labour with generate_views.validate():
  validate()      -- structure and cross-view consistency (B2=B1, B4⊆B1, B5⊆B4, unique C, ...)
  model_rules.run -- content rules: missing contract items, naming/granularity/duplicates, real document names, cross-domain ownership, responsibility gaps

Every result carries a code (rule ID) and a pattern (negative-pattern ID in negative-patterns.md);
levels: ERROR (blocks) / CONFLICT (to the governance board) / WARN (agent self-review) / INFO / RULED (already ruled).
"""
import hashlib
import json
import os
import re

import bizprofile as BP

LAYERS = ("guide", "exec", "supp")
BASELINE = {}   # loaded from profile.baseline by configure()

CJK = re.compile(r"[一-鿿]")   # the *_CN patterns below are Chinese-language word lists used to check Chinese input; *_EN patterns check English input
SYS_CN = re.compile(r"(模块|ERP|SAP|OA系统)")                       # specific system/module names -> ERROR
SYS_EN = re.compile(r"\b(Module|ERP|SAP)\b")
GEN_SYS_CN = re.compile(r"(系统|平台)")                             # generic "system/platform" -> WARN (e.g. "system development" is a legitimate IT capability)
GEN_SYS_EN = re.compile(r"\b(System|Platform|App)\b", re.I)
DEPT_CN = re.compile(r"(部|处|科|室)$")
DEPT_EN = re.compile(r"\b(Dept|Department|Office|Bureau)\b", re.I)
CRUD_CN = re.compile(r"^(新增|查询|修改|删除|编辑|导出|导入|查看)")
CRUD_EN = re.compile(r"^(Add|Query|Edit|Delete|View|Export|Import|Search|Update|Create)\b")
RULE_CN = re.compile(r"(制度|办法|标准|定额|规定|细则)$")
RULE_EN = re.compile(r"(Policy|Policies|Standard|Standards|Norm|Norms|Regulation|Regulations)$")
EXEC_VERB_CN = re.compile(r"^(编制|填报|录入|领用|发放|登记|收料|发料|入库|出库)")
EXEC_VERB_EN = {"compile", "issue", "prepare", "record", "register", "receive", "pay",
                "deliver", "post", "enter", "fill"}
DOC_SUFFIX_CN = re.compile(r"(单|表|书|证|台账|报表|记录|清单|名录|名册|合同|协议|计划|方案|报告|凭证|发票|通知|卡|册|簿|函|令|库|目录|矩阵|看板|日志|图|纪要)$")
DOC_NOUN_EN = {"form", "note", "sheet", "report", "plan", "order", "record", "register", "ledger",
               "list", "contract", "agreement", "certificate", "cert.", "card", "voucher", "invoice",
               "notice", "request", "approval", "checklist", "scorecard", "statement", "library",
               "catalog", "matrix", "table", "bulletin", "alert", "dashboard", "policy", "norms",
               "documents", "takeoff", "log", "slip", "review", "assessment", "opinion", "payroll",
               "measurement", "settlement", "analysis", "roster", "templates", "blacklist", "minutes",
               "receipt", "acceptance", "manual", "budget", "schedule", "file", "book", "map"}
VERBS_EN = {
    "set", "maintain", "standardize", "plan", "define", "govern", "supervise", "benchmark", "control",
    "manage", "monitor", "assess", "enforce", "forecast", "compile", "balance", "approve", "register",
    "qualify", "run", "award", "sign", "purchase", "contract", "inspect", "receive", "mobilize",
    "induct", "issue", "count", "dispatch", "track", "settle", "pay", "demobilize", "dispose",
    "retire", "evaluate", "process", "account", "depreciate", "verify", "review", "handle", "certify",
    "staff", "operate", "provide", "audit", "investigate", "prepare", "record", "collect", "create",
    "check", "sample", "post", "store", "transport", "accept", "deliver", "conduct", "raise",
    "analyze", "analyse", "reconcile", "calculate", "confirm", "return", "clear", "release",
    "identify", "appraise", "sell", "score", "apply", "draft", "publish", "measure", "revise",
    "compile", "negotiate", "call", "justify", "tender", "select", "file", "rectify", "arrange",
    "schedule", "repair", "perform", "execute", "litigate", "train", "assign", "support",
    "aggregate", "trigger", "rank", "hold", "flag", "share", "warn", "report", "map", "extract",
    "match", "transfer", "classify", "grade", "enroll", "deliver", "regulate", "allocate", "build",
    "design", "develop", "deploy", "coordinate", "organize", "organise", "close", "dispose", "use",
}


def is_cn(s):
    return bool(CJK.search(s or ""))


def norm(s):
    s = str(s or "")
    if is_cn(s):
        return re.sub(r"\s+", "", s)
    s = re.sub(r"-\n", "-", s)
    return re.sub(r"\s+", " ", s.replace("\n", " ")).strip()


def tokens(s):
    s = norm(s).lower()
    if is_cn(s):
        s = re.sub(r"\W", "", s)
        return {s[i:i + 2] for i in range(len(s) - 1)} or {s}
    stop = {"and", "of", "the", "by", "to", "for", "with", "into", "on", "&", "-"}
    return {w for w in re.split(r"[\s/&\-()]+", s) if w and w not in stop}


def jacc(a, b):
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / float(len(ta | tb) or 1)


def first_word_is_verb(s):
    w = norm(s).split(" ")[0].lower()
    return w in VERBS_EN or w.endswith(("ize", "ise", "ify", "ate"))


def looks_like_doc(s):
    s = norm(s)
    if is_cn(s):
        return bool(DOC_SUFFIX_CN.search(s))
    words = s.lower().split(" ")
    return any(w.strip("()") in DOC_NOUN_EN for w in words[-2:])


ACT_SUFFIX_CN = re.compile(r"(管理|策划|审核|审批|验收|评价|编制|分析|控制|监督|计量|核算|考核|组织|实施|处置|调度|维护|登记)$")


def looks_like_action(s):
    s = norm(s)
    if is_cn(s):
        return bool(ACT_SUFFIX_CN.search(s)) and not DOC_SUFFIX_CN.search(s)
    return first_word_is_verb(s) and not looks_like_doc(s)


class Issues:
    def __init__(self):
        self.items = []

    def add(self, level, code, view, subject, message, pattern=""):
        h = hashlib.md5(("%s|%s" % (code, subject)).encode("utf-8")).hexdigest()[:8]
        self.items.append(dict(id=h, level=level, code=code, view=view, subject=subject,
                               pattern=pattern, message=message,
                               to="governance board" if level == "CONFLICT" else ""))


# ---------------- 1. input contract ----------------
def check_contract(d, data_path, iss, manifest_path=None):
    VIEWS_REQ = BP.get(d)["contract"]["views"]
    prov = d.get("provenance") or {"mode": "draft"}
    mode = prov.get("mode", "draft")
    blocked = set()
    if mode not in ("documents", "interview", "draft"):
        iss.add("ERROR", "CON-MODE", "*", mode, "provenance.mode must be documents / interview / draft")
        return mode, blocked
    mpath = manifest_path or prov.get("manifest")
    items = {}
    if mpath:
        if not os.path.isabs(mpath):
            mpath = os.path.join(os.path.dirname(os.path.abspath(data_path)), mpath)
        if os.path.exists(mpath):
            with open(mpath, encoding="utf-8") as f:
                items = json.load(f).get("items", {})
        elif mode != "draft":
            iss.add("ERROR", "CON-FILE", "*", mpath, "input manifest file not found (input-contract.md §2)")

    def ok(code):
        it = items.get(code) or {}
        if mode == "interview":
            return bool(it.get("interview")) or bool(it.get("files"))
        return bool(it.get("files")) or bool(it.get("interview"))

    present = [v for v in ("b1", "b2", "b3", "b4", "b5") if v == "b1" or v in d]
    for v in present:
        miss = [c for c in VIEWS_REQ[v] if not ok(c)]
        if not miss:
            continue
        if mode == "draft":
            iss.add("WARN", "CON-MISS", v.upper(), ",".join(miss),
                    "missing required materials %s; draft mode generates anyway but marks every slide DRAFT" % "/".join(miss), "NP-SRC-01")
        else:
            iss.add("ERROR", "CON-MISS", v.upper(), ",".join(miss),
                    "missing required materials %s (input-contract.md §1); this view is not generated" % "/".join(miss), "NP-SRC-01")
            blocked.add(v)
    if mode == "draft":
        iss.add("WARN", "CON-DRAFT", "*", d.get("domain", ""),
                "provenance.mode=draft (or not declared): content is not document-grounded; discussion draft only", "NP-SRC-01")
    return mode, blocked


# ---------------- 2. B1 capabilities ----------------
def check_b1(d, iss):
    lay = d["layers"]
    for k in LAYERS:
        blocks = lay[k]["blocks"]
        n_l2 = 0
        all_l2 = []
        for b in blocks:
            l1, l2s = b["l1"], b.get("l2", [])
            n_l2 += len(l2s)
            for name, lvl in [(l1, "L1")] + [(x, "L2") for x in l2s]:
                if SYS_CN.search(name) or SYS_EN.search(name):
                    iss.add("ERROR", "B1-SYS", "B1", name, "%s name contains a specific system/module name" % lvl, "NP-B1-02")
                elif GEN_SYS_CN.search(name) or GEN_SYS_EN.search(name):
                    iss.add("WARN", "B1-SYS", "B1", name, "%s name contains \"system/platform\"; check that the capability is not named after a system" % lvl, "NP-B1-02")
                if (is_cn(name) and DEPT_CN.search(name)) or (not is_cn(name) and DEPT_EN.search(name)):
                    iss.add("ERROR", "B1-DEPT", "B1", name, "%s name contains a department name" % lvl, "NP-B1-02")
            if is_cn(l1) and len(l1) > NAMING.get("l1_max", 6):
                iss.add("WARN", "B1-L1LEN", "B1", l1, "L1 longer than %d characters" % NAMING.get("l1_max", 6), "NP-B1-03")
            for x in l2s:
                if is_cn(x) and NAMING.get("l2") == "cn4" and len(x) != 4:
                    iss.add("WARN", "B1-L2LEN", "B1", x, "L2 is not a four-character name", "NP-B1-03")
                if not is_cn(x) and NAMING.get("l2") != "free" and not first_word_is_verb(x):
                    iss.add("WARN", "B1-L2VERB", "B1", x, "L2 does not start with a verb (should be a verb-object phrase)", "NP-B1-03")
                if k == "guide" and ((is_cn(x) and EXEC_VERB_CN.search(x)) or
                                     (not is_cn(x) and norm(x).split(" ")[0].lower() in EXEC_VERB_EN)):
                    iss.add("WARN", "B1-GUIDEVERB", "B1", x, "execution action in the %s layer" % lay["guide"].get("label", "guide"), "NP-B1-06")
            lo, hi = LIM["l2_per_l1"]
            if len(l2s) > hi or len(l2s) < lo:
                iss.add("WARN", "B1-GRAIN", "B1", l1, "number of L2 under this L1 = %d (recommended %d-%d)" % (len(l2s), lo, hi), "NP-B1-07")
            all_l2 += l2s
        bl1, bl2 = BASELINE[k]   # from profile.baseline (size of the reference domain)
        if len(blocks) > bl1 * 1.5 or n_l2 > bl2 * 1.5:
            iss.add("WARN", "B1-BASE", "B1", lay[k].get("label", k),
                    "%d L1 / %d L2 exceeds 150%% of the baseline (%d/%d); consider merging" % (len(blocks), n_l2, bl1, bl2), "NP-B1-07")
        for i in range(len(all_l2)):
            for j in range(i + 1, len(all_l2)):
                a, b = all_l2[i], all_l2[j]
                if a == b:
                    iss.add("ERROR", "B1-DUP", "B1", a, "duplicate L2 name within a layer", "NP-B1-04")
                elif jacc(a, b) >= 0.6:
                    iss.add("WARN", "B1-OVERLAP", "B1", "%s / %s" % (a, b), "two L2 names in the same layer are very similar; check for overlap", "NP-B1-04")


# ---------------- 3. B2 components ----------------
def check_b2(d, iss):
    if "b2" not in d:
        return
    where = {}
    for k in LAYERS:
        for b in d["b2"]["layers"][k]:
            for x in b.get("l2s", []):
                for c in x.get("comps", []):
                    n = c["name"]
                    if norm(n).lower() == norm(x["l2"]).lower():
                        iss.add("WARN" if k == "supp" else "ERROR", "B2-SAME", "B2", n,
                                "component has the same name as its L2 (empty decomposition)" + ("; acceptable in the support layer, but a concrete task is better" if k == "supp" else ""),
                                "NP-B2-01")
                    if (is_cn(n) and RULE_CN.search(n)) or (not is_cn(n) and RULE_EN.search(n) and not first_word_is_verb(n)):
                        iss.add("WARN", "B2-RULE", "B2", n, "component looks like a regulation/standard/quota itself (rules are attributes, not components)", "NP-B2-02")
                    if (is_cn(n) and CRUD_CN.search(n)) or (not is_cn(n) and CRUD_EN.search(n)):
                        iss.add("WARN", "B2-CRUD", "B2", n, "component looks like a create/read/update/delete operation of a system page", "NP-B2-03")
                    where.setdefault(norm(n), []).append(x["l2"])
    for n, l2s in where.items():
        if len(l2s) > 1:
            iss.add("WARN", "B2-DUP", "B2", n, "component repeated under several L2: %s - keep it under the accountable L2, or treat it as a shared-component candidate (decided later per R-001)"
                    % ", ".join(l2s), "NP-B2-04")


# ---------------- 4. B3 value streams ----------------
def check_b3(d, iss, b4_objs):
    if "b3" not in d:
        return
    pages = d["b3"]["pages"]
    lo, hi = LIM["streams"]
    if len(pages) > hi or len(pages) < lo:
        iss.add("WARN", "B3-COUNT", "B3", str(len(pages)), "%d value streams (recommended %d-%d)" % (len(pages), lo, hi), "NP-B3-02")
    objs_norm = {norm(o).lower(): o for o in b4_objs}
    for pg in pages:
        st = pg["stages"]
        names = st["names"] if isinstance(st, dict) else st
        t = pg.get("title", "")
        if len(pg["nodes"]) > LIM["b3_nodes_max"]:
            iss.add("WARN", "B3-SIZE", "B3", t, "%d nodes on one slide > %d; the specification requires splitting (b3-flow-spec §10)" % (len(pg["nodes"]), LIM["b3_nodes_max"]), "NP-B3-06")
        if len(names) > LIM["b3_stages_max"] or len(pg["lanes"]) > LIM["b3_lanes_max"]:
            iss.add("WARN", "B3-SIZE", "B3", t, "%d stages / %d lanes (recommended <=%d / <=%d)" % (len(names), len(pg["lanes"]), LIM["b3_stages_max"], LIM["b3_lanes_max"]), "NP-B3-06")
        for n in pg["nodes"]:
            txt = norm(n["text"])
            if SYS_CN.search(txt) or SYS_EN.search(txt) or GEN_SYS_CN.search(txt) or GEN_SYS_EN.search(txt):
                iss.add("WARN", "B3-SYS", "B3", txt, "node is written as a system/module name", "NP-B3-04")
            if n.get("kind") == "doc" and b4_objs and txt.lower() not in objs_norm:
                best = max(b4_objs, key=lambda o: jacc(o, txt)) if b4_objs else ""
                iss.add("WARN", "B3-DOCNAME", "B3", txt,
                        "document node is not the real name of a B4 object%s" % (" (closest: %s)" % best if best and jacc(best, txt) > 0.3 else ""),
                        "NP-B3-05")


# ---------------- 5. B4 objects ----------------
def b4_objects(d):
    out = []
    if "b4" not in d:
        return out
    for k in LAYERS:
        for b in d["b4"]["layers"][k]:
            for g in b.get("groups", []):
                for o in g.get("objs", []):
                    out.append((k, b["l1"], g["g"], o))
    return out


def check_b4(d, iss, objs):
    names_cap = set()
    for k in LAYERS:
        for b in d["layers"][k]["blocks"]:
            names_cap.add(norm(b["l1"]).lower())
            names_cap.update(norm(x).lower() for x in b.get("l2", []))
    if "b2" in d:
        for k in LAYERS:
            for b in d["b2"]["layers"][k]:
                for x in b.get("l2s", []):
                    names_cap.update(norm(c["name"]).lower() for c in x.get("comps", []))
    names = [o for _, _, _, o in objs]
    for o in names:
        if norm(o).lower() in names_cap:
            iss.add("WARN", "B4-ACT", "B4", o, "object has the same name as a capability/component: either the component should be an action (e.g. \"Fill in Site Log\") or the object is not a document", "NP-B4-01")
        elif looks_like_action(o):
            iss.add("WARN", "B4-ACT", "B4", o, "object name looks like an action/capability rather than a real document name", "NP-B4-01")
        if SYS_CN.search(o) or SYS_EN.search(o) or GEN_SYS_CN.search(o) or GEN_SYS_EN.search(o):
            iss.add("WARN", "B4-SYS", "B4", o, "object looks like a system/platform", "NP-B4-04")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if jacc(names[i], names[j]) >= 0.75:
                iss.add("WARN", "B4-ALIKE", "B4", "%s / %s" % (names[i], names[j]),
                        "two object names are very similar; check whether they are the same document", "NP-B4-02")


# ---------------- 6. B5 role matrix ----------------
def check_b5(d, iss, objs):
    if "b5" not in d:
        return
    roles = d["b5"]["roles"]
    lo, hi = LIM["roles"]
    if not (lo <= len(roles) <= hi):
        iss.add("WARN", "B5-ROLES", "B5", str(len(roles)), "%d role columns (recommended %d-%d)" % (len(roles), lo, hi), "")
    for r in roles:
        nm = norm(r["name"])
        if SYS_CN.search(nm) or SYS_EN.search(nm):
            iss.add("WARN", "B5-ROLESYS", "B5", nm, "role name looks like a system name", "NP-B5-05")
    rows = {r["object"] for r in d["b5"]["rows"]}
    for _, l1, _, o in objs:
        if o not in rows:
            iss.add("CONFLICT", "B5-GAP", "B5", o, "B4 object has no row in B5: producer undefined (responsibility gap)", "NP-B5-04")
    for r in d["b5"]["rows"]:
        if not r.get("c"):
            iss.add("CONFLICT", "B5-NOC", "B5", r["object"], "no producer (C)", "NP-B5-01")


# ---------------- 7. cross-domain registry ----------------
def is_external(level):
    return bool(re.search(r"(外部|供应|External|Partner|Third)", level or "", re.I))   # Chinese terms: "external", "supplier"


def check_registry(d, iss, objs, registry_path):
    if not registry_path:
        return
    if not os.path.exists(registry_path):
        iss.add("WARN", "REG-FILE", "B4", registry_path, "cross-domain registry not found; cross-domain comparison skipped")
        return
    with open(registry_path, encoding="utf-8") as f:
        reg = json.load(f).get("objects", [])
    by_name = {norm(e["name"]).lower(): e for e in reg}
    by_alias = {norm(a).lower(): e for e in reg for a in e.get("aliases", [])}
    dom = d.get("domain", "")
    refs = {norm(x).lower() for x in d.get("external_refs", [])}
    lvl = {r["key"]: r["level"] for r in d.get("b5", {}).get("roles", [])}
    crow = {r["object"]: r.get("c") for r in d.get("b5", {}).get("rows", [])}
    for _, _, _, o in objs:
        key = norm(o).lower()
        e = by_name.get(key)
        if e is None and key in by_alias:
            e2 = by_alias[key]
            iss.add("WARN", "REG-ALIAS", "B4", o, "matches a registry alias; the standard name is '%s' (owned by %s)" % (e2["name"], e2["owner_domain"]),
                    "NP-B4-02")
            e = e2
        if e is None:
            iss.add("INFO", "REG-NEW", "B4", o, "not in the registry; register after the governance board confirms ownership", "")
            continue
        if e["owner_domain"] != dom and key not in refs:
            c = crow.get(o)
            if c is None or not is_external(lvl.get(c, "")):
                iss.add("CONFLICT", "REG-C3", "B4", o,
                        "registry assigns ownership to '%s', but this domain lists it as its own object%s; use an external_refs reference, or ask the governance board to change the ownership"
                        % (e["owner_domain"], " (B5 producer is a role of this domain)" if c else ""), "NP-B4-05")


# ---------------- 8. rulings ----------------
def apply_rulings(d, iss, rulings_path):
    if not rulings_path or not os.path.exists(rulings_path):
        return
    with open(rulings_path, encoding="utf-8") as f:
        rulings = json.load(f).get("rulings", [])
    for r in rulings:
        if not r.get("writeback"):
            iss.add("WARN", "RUL-NOWB", "*", r.get("id", "?"), "ruling has no writeback (not turned into a rule or negative pattern)", "")
        for s in r.get("suppress", []):
            if s.get("domain") and s["domain"] != d.get("domain"):
                continue
            for it in iss.items:
                if it["code"] == s.get("code") and norm(it["subject"]).lower() == norm(s.get("subject", "")).lower():
                    it["level"] = "RULED"
                    it["message"] += " | ruled under %s: %s" % (r["id"], r.get("decision", ""))


# ---------------- entry point ----------------
NAMING, LIM = {}, {}


def configure(d):
    """Load baseline, naming style, limits and domain vocabulary from the profile (extends rather than replaces the built-in word lists)."""
    global BASELINE, DOC_SUFFIX_CN
    prof = BP.get(d)
    BASELINE = {k: tuple(v) for k, v in prof["baseline"].items()}
    NAMING.clear(); NAMING.update(prof["naming"])
    LIM.clear(); LIM.update(prof["limits"])
    lex = prof.get("lexicon", {})
    if lex.get("doc_suffix_cn"):
        DOC_SUFFIX_CN = re.compile(DOC_SUFFIX_CN.pattern[:-2] + "|" + "|".join(map(re.escape, lex["doc_suffix_cn"])) + ")$")
    DOC_NOUN_EN.update(w.lower() for w in lex.get("doc_noun_en", []))
    VERBS_EN.update(w.lower() for w in lex.get("verbs_en", []))
    return prof


def run(d, data_path, registry_path=None, rulings_path=None, manifest_path=None):
    configure(d)
    iss = Issues()
    mode, blocked = check_contract(d, data_path, iss, manifest_path)
    objs = b4_objects(d)
    check_b1(d, iss)
    check_b2(d, iss)
    check_b4(d, iss, objs)
    check_b3(d, iss, [o for _, _, _, o in objs])
    check_b5(d, iss, objs)
    check_registry(d, iss, objs, registry_path)
    apply_rulings(d, iss, rulings_path)
    return mode, blocked, iss.items


ORDER = {"ERROR": 0, "CONFLICT": 1, "WARN": 2, "RULED": 3, "INFO": 4}


def summarize(items):
    c = {}
    for it in items:
        c[it["level"]] = c.get(it["level"], 0) + 1
    return c


def print_issues(items, show_info=False):
    for it in sorted(items, key=lambda x: (ORDER[x["level"]], x["view"], x["code"])):
        if it["level"] == "INFO" and not show_info:
            continue
        print("[%s] %-11s %-4s %s | %s%s" % (it["level"], it["code"], it["view"], it["subject"], it["message"],
                                          (" (%s)" % it["pattern"]) if it["pattern"] else ""))
    s = summarize(items)
    print("Total: " + "  ".join("%s %d" % (k, s.get(k, 0)) for k in ORDER))


def write_conflicts(items, outdir, mode):
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, "conflicts.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"provenance_mode": mode, "summary": summarize(items),
                   "issues": sorted(items, key=lambda x: (ORDER[x["level"]], x["view"], x["code"]))},
                  f, ensure_ascii=False, indent=1)
    return p
