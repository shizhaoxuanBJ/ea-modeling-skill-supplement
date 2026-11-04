# -*- coding: utf-8 -*-
"""Method profile: separates the "method core" from the "organizational/industry context".

The method core (B1-B5 metamodel, process, judgment library, validator) is the same for all industries;
a profile carries only context parameters: names of the three layers, language and fonts, granularity baseline, naming style,
domain vocabulary, required input-contract items, layout limits, header branding, and industry negative-pattern packs.

Lookup order: --profile argument > biz_data.profile > generic-zh / generic-en chosen automatically from the language of the domain name.
A profile may declare "extends": "generic-zh" and override only what differs.
"""
import copy
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(HERE, "..", "profiles")
CJK = re.compile(r"[一-鿿]")

DEFAULT = {
    "id": "generic-zh",
    "lang": "zh",
    "layers": {"guide": "战略管控", "exec": "业务执行", "supp": "综合支撑"},
    "baseline": {"guide": [4, 21], "exec": [6, 30], "supp": [6, 23]},
    "naming": {"l2": "cn4", "l1_max": 6},
    "lexicon": {"doc_suffix_cn": [], "doc_noun_en": [], "verbs_en": []},
    "contract": {"views": {"b1": ["A1", "A3", "C1"], "b2": ["A3"], "b3": ["A2", "A3"],
                           "b4": ["B1"], "b5": ["A1", "A2", "B1"]}},
    "limits": {"streams": [2, 5], "b3_nodes_max": 30, "b3_lanes_max": 6, "b3_stages_max": 6,
               "l2_per_l1": [2, 10], "roles": [12, 18], "b5_rows_per_page": 22},
    "branding": {"series": "", "font_latin": "微软雅黑", "font_ea": "微软雅黑"},
    "patterns": ["negative-patterns.md"],
    "org_tiers_hint": [],
}

STR = {
    "zh": {
        "head_right": "{series} ｜ {domain}业务架构交付物",
        "b1_title": "业务架构 ：B1-业务能力框架视图（{domain}）",
        "b2_title": "业务架构 ：B2-业务组件视图（{domain}）",
        "b2_legend": "业务组件（本域全量）",
        "b2_shared": "共性组件识别待全部业务域梳理完成后统一判定（暂不标注颜色区分）",
        "b3_title": "业务架构 ：B3-端到端价值流图 · {title}（{subtitle}）",
        "b3_ov_title": "业务架构 ：B3-端到端价值流总览（{domain}）",
        "b3_ov_cols": ["价值流名称", "触发点 → 交付物", "经历的阶段", "客户", "交付的价值"],
        "b3_legend": ["任务", "业务对象(单据)", "起止事件", "顺序流"],
        "start": "开始", "end": "交付完成",
        "b4_title": "业务架构 ：B4-业务对象视图（{domain}）· 全量{n}项",
        "b4_legend": "业务对象（本域全量{n}项）",
        "b5_title": "业务架构 ：B5-业务对象-角色矩阵（{domain}）· {title}",
        "b5_cols": ["L2能力", "业务对象"],
        "b5_legend": ["产生方（每行唯一）", "使用方", "空白=无关 ｜ 列=组织角色（按级别分色） ｜ 行=业务对象（按L1竖排分组）"],
        "page_suffix": "（{i}/{n}）",
        "files": {"b1": "B1-业务能力框架视图", "b2": "B2-业务组件视图", "b3": "B3-端到端价值流图",
                  "b4": "B4-业务对象视图", "b5": "B5-业务对象-角色矩阵", "lists": "业务架构清单",
                  "fmt": "{name}（{domain}）"},
        "xlsx": {"cap": "能力清单", "cap_t": "B1 业务能力清单（{domain}）", "cap_h": ["层", "L1能力域", "L2能力项"],
                 "comp": "组件清单", "comp_t": "B2 业务组件清单（{domain}）",
                 "comp_h": ["层", "L1能力域", "L2能力项", "L3业务组件", "共性候选"], "yes": "是",
                 "obj": "对象清单", "obj_t": "B4 业务对象清单（{domain}）", "obj_h": ["层", "L1能力域", "L2能力组", "业务对象"],
                 "mx": "对象-角色矩阵", "mx_t": "B5 对象-角色矩阵清单（{domain}）",
                 "mx_h": ["L1能力域", "L2能力项", "业务对象", "产生方(C)", "使用方(U)"], "sep": "、",
                 "issues": "待决事项", "issues_t": "待决事项（provenance={mode}）",
                 "issues_h": ["级别", "规则", "视图", "对象/主题", "说明", "反面模式", "交由"],
                 "draft": "DRAFT · 未经文档佐证，仅作讨论稿"},
        "watermark": "DRAFT · 未经文档佐证",
    },
    "en": {
        "head_right": "{series} | {domain}",
        "b1_title": "B1 Capability Framework · {domain}",
        "b2_title": "B2 Business Components · {domain}",
        "b2_legend": "Business component (full domain set)",
        "b2_shared": "Shared components will be identified after all domains are mapped (not color-coded yet)",
        "b3_title": "B3 Value Stream · {subtitle}: {title}",
        "b3_ov_title": "B3 Value Stream Overview · {domain}",
        "b3_ov_cols": ["Value Stream", "Trigger → Deliverable", "Stages Traversed", "Customer", "Value Delivered"],
        "b3_legend": ["Task", "Business object", "Start / end", "Flow"],
        "start": "Start", "end": "End",
        "b4_title": "B4 Business Objects · {domain} ({n} objects)",
        "b4_legend": "Business object ({n} in domain)",
        "b5_title": "B5 Object-Role Matrix · {title}",
        "b5_cols": ["L2 Capability", "Business Object"],
        "b5_legend": ["Creator (one per row)", "User", "Blank = no involvement | columns = roles (shaded by tier) | rows = business objects (grouped by L1)"],
        "page_suffix": " ({i}/{n})",
        "files": {"b1": "B1-Capability Framework", "b2": "B2-Business Components", "b3": "B3-End-to-End Value Streams",
                  "b4": "B4-Business Objects", "b5": "B5-Object-Role Matrix", "lists": "Business Architecture Inventory",
                  "fmt": "{name} ({domain})"},
        "xlsx": {"cap": "Capabilities", "cap_t": "B1 Capability Inventory ({domain})", "cap_h": ["Layer", "L1 Capability", "L2 Capability"],
                 "comp": "Components", "comp_t": "B2 Component Inventory ({domain})",
                 "comp_h": ["Layer", "L1 Capability", "L2 Capability", "L3 Business Component", "Shared Candidate"], "yes": "Yes",
                 "obj": "Objects", "obj_t": "B4 Business Object Inventory ({domain})", "obj_h": ["Layer", "L1 Capability", "L2 Group", "Business Object"],
                 "mx": "Object-Role Matrix", "mx_t": "B5 Object-Role Matrix ({domain})",
                 "mx_h": ["L1 Capability", "L2 Capability", "Business Object", "Creator (C)", "Users (U)"], "sep": "; ",
                 "issues": "Open Issues", "issues_t": "Open issues (provenance={mode})",
                 "issues_h": ["Level", "Rule", "View", "Subject", "Message", "Pattern", "Route to"],
                 "draft": "DRAFT · not document-grounded; discussion draft only"},
        "watermark": "DRAFT · not document-grounded",
    },
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _read(name_or_path):
    p = name_or_path
    if not p.endswith(".json"):
        p = os.path.join(PROFILE_DIR, p + ".json")
    if not os.path.exists(p):
        raise SystemExit("[ERROR] profile not found: %s (available: %s)" % (name_or_path, ", ".join(list_profiles())))
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def list_profiles():
    if not os.path.isdir(PROFILE_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(PROFILE_DIR) if f.endswith(".json"))


def resolve(raw, seen=None):
    seen = seen or set()
    if raw.get("extends"):
        if raw["extends"] in seen:
            raise SystemExit("[ERROR] cyclic profile inheritance: %s" % raw["extends"])
        seen.add(raw["extends"])
        base = resolve(_read(raw["extends"]), seen)
    else:
        base = DEFAULT
    return _merge(base, {k: v for k, v in raw.items() if k != "extends"})


def load(d, cli=None):
    """Return the complete profile and attach it to d["_profile"] (shared by all scripts)."""
    name = cli or d.get("profile")
    if not name:
        name = "generic-zh" if CJK.search(d.get("domain", "")) else "generic-en"
    prof = resolve(_read(name)) if (os.path.isdir(PROFILE_DIR) or name.endswith(".json")) else copy.deepcopy(DEFAULT)
    prof["_name"] = name
    d["_profile"] = prof
    return prof


def get(d):
    return d.get("_profile") or load(d)


def T(d, key, **kw):
    lang = get(d).get("lang", "zh")
    s = STR[lang][key]
    return s.format(**kw) if isinstance(s, str) and kw else s


def X(d, key, **kw):
    s = STR[get(d).get("lang", "zh")]["xlsx"][key]
    return s.format(**kw) if isinstance(s, str) and kw else s
