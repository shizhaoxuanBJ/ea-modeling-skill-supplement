# -*- coding: utf-8 -*-
"""Maintain the cross-domain shared-object registry (run after the governance board confirms ownership).

  python registry.py list registry.json
  python registry.py add  registry.json --domain "Resource Management" --from biz_data.json   # register this domain's own objects
  python registry.py add  registry.json --domain Finance --name "VAT Invoice" --alias "Tax Invoice"
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_rules as MR  # noqa: E402


def load(p):
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"objects": []}


def save(p, reg):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "add"])
    ap.add_argument("registry")
    ap.add_argument("--domain")
    ap.add_argument("--from", dest="src")
    ap.add_argument("--name")
    ap.add_argument("--alias", action="append", default=[])
    a = ap.parse_args()
    reg = load(a.registry)
    idx = {MR.norm(o["name"]).lower(): o for o in reg["objects"]}
    alias = {MR.norm(x).lower(): o for o in reg["objects"] for x in o.get("aliases", [])}
    if a.cmd == "list":
        for o in sorted(reg["objects"], key=lambda o: (o["owner_domain"], o["name"])):
            print("%-14s %-40s %s" % (o["owner_domain"], o["name"], ", ".join(o.get("aliases", []))))
        print("%d entries" % len(reg["objects"]))
        return
    if not a.domain:
        sys.exit("add requires --domain")
    names = []
    if a.src:
        with open(a.src, encoding="utf-8") as f:
            d = json.load(f)
        refs = {MR.norm(x).lower() for x in d.get("external_refs", [])}
        names = [o for _, _, _, o in MR.b4_objects(d) if MR.norm(o).lower() not in refs]
    if a.name:
        names.append(a.name)
    added = skipped = 0
    for n in names:
        k = MR.norm(n).lower()
        hit = idx.get(k) or alias.get(k)
        if hit:
            if hit["owner_domain"] != a.domain:
                print("[CONFLICT] %s is already registered to %s; unchanged (needs a governance ruling)" % (n, hit["owner_domain"]))
            skipped += 1
            continue
        o = {"name": n, "owner_domain": a.domain, "aliases": list(a.alias) if a.name == n else []}
        reg["objects"].append(o)
        idx[k] = o
        added += 1
    save(a.registry, reg)
    print("registered %d, skipped %d -> %s" % (added, skipped, a.registry))


if __name__ == "__main__":
    main()
