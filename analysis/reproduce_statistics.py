"""Recompute the statistics reported in the paper from the aggregated data in ../data.

Usage:   python reproduce_statistics.py [path/to/data]
Requires: numpy, scipy
"""
import csv
import os
import sys

import numpy as np
from scipy import stats

DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def icc_2k(Y):
    """ICC(2,k): two-way random effects, absolute agreement, mean of k raters (Shrout & Fleiss 1979)."""
    n, k = Y.shape
    gm = Y.mean()
    msr = k * ((Y.mean(1) - gm) ** 2).sum() / (n - 1)
    msc = n * ((Y.mean(0) - gm) ** 2).sum() / (k - 1)
    sse = ((Y - Y.mean(1, keepdims=True) - Y.mean(0, keepdims=True) + gm) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (msc - mse) / n)


# 1) Blind expert ratings (Sect. 6.1, "Quality")
rows = read("expert_ratings.csv")
r2 = np.array([r["round"] == "2" for r in rows])
for dim in ("syntax", "semantics"):
    X = np.array([[float(r[f"E{i}_{dim}"]) for i in range(1, 6)] for r in rows])
    m = X.mean(1)
    a, b = m[r2], m[~r2]
    u = stats.mannwhitneyu(b, a, alternative="two-sided", method="exact")
    rb = 2 * u.statistic / (len(a) * len(b)) - 1
    print(f"{dim:9s}: Round 2 {a.mean():.2f} (SD {a.std(ddof=1):.2f}, n={len(a)}), Round 3 {b.mean():.2f} (SD {b.std(ddof=1):.2f}, n={len(b)}); "
          f"Mann-Whitney U={u.statistic:.0f}, exact p={u.pvalue:.1e}, rank-biserial r={rb:.2f}; "
          f"ICC(2,5) all={icc_2k(X):.3f}, Round 2={icc_2k(X[r2]):.2f}, Round 3={icc_2k(X[~r2]):.2f}")

# 2) Round-2 same-domain similarity (Sect. 6.1, "Consistency")
pairs = read("round2_same_domain_pairs.csv")
sim = np.array([1 - float(p["GED"]) / (float(p["size_1"]) + float(p["size_2"])) for p in pairs])
print(f"Round-2 same-domain similarity: {len(sim)} pairs, mean {sim.mean():.1%}, SD {sim.std(ddof=1) * 100:.1f} pp, "
      f"range {sim.min():.1%}-{sim.max():.1%}")

# 3) Cross-domain conflicts (Sect. 6.1, "Cross-Domain Composability")
c = read("cross_domain_conflicts.csv")
tot = [sum(int(r[k]) for r in c) for k in ("C1_granularity", "C2_interface_direction", "C3_master_data_ownership", "round2_total", "round3_total")]
print("Cross-domain conflicts, Round 2: C1 %d, C2 %d, C3 %d, total %d; Round 3 total %d" % tuple(tot))

# 4) Inter-coder agreement (Sect. 3)
for r in read("coding_agreement.csv"):
    po, pe = int(r["agreements"]) / int(r["units"]), float(r["expected_agreement_Pe"])
    print(f"{r['task']}: Po={po:.3f}, Pe={pe:.3f}, Cohen's kappa={(po - pe) / (1 - pe):.2f}")
