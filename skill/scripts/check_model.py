# -*- coding: utf-8 -*-
"""Validate only, no drawing: structural consistency (validate) + content rules (model_rules); writes conflicts.json.

Usage:
  python check_model.py biz_data.json [--registry registry.json] [--rulings ../rulings.json]
                        [--manifest inputs.json] [--outdir outputs] [--info]
Exit code: 0 = no ERROR; 2 = ERROR present (suitable for automation)
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bizprofile as BP  # noqa: E402
import model_rules as MR  # noqa: E402
from generate_views import validate, apply_profile  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--registry", default=None)
    ap.add_argument("--rulings", default=os.path.join(HERE, "..", "rulings.json"))
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--info", action="store_true", help="also list INFO items (e.g. objects awaiting registration)")
    ap.add_argument("--profile", default=None, help="method profile (default: biz_data.profile)")
    a = ap.parse_args()
    with open(a.data, encoding="utf-8") as f:
        d = json.load(f)
    BP.load(d, a.profile)
    prof = apply_profile(d)
    print("profile: %s (lang=%s) | judgment library: %s" % (prof["_name"], prof["lang"], ", ".join(prof.get("patterns", []))))
    errors, warns = validate(d)
    for e in errors:
        print("[ERROR] STRUCT      %s" % e)
    for w in warns:
        print("[WARN]  STRUCT      %s" % w)
    mode, blocked, items = MR.run(d, a.data, a.registry, a.rulings, a.manifest)
    print("-- content rules (provenance=%s) --" % mode)
    MR.print_issues(items, a.info)
    if a.outdir:
        print("written:", MR.write_conflicts(items, a.outdir, mode))
    bad = errors or any(it["level"] == "ERROR" for it in items)
    sys.exit(2 if bad else 0)


if __name__ == "__main__":
    main()
