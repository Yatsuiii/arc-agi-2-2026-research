"""Render EXP002-B's figures from `artifacts/EXP002B/exp002b_report.json`.

Run: `python -m src.analysis.exp002b_figures`
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "artifacts" / "EXP002B" / "exp002b_report.json"
FIG_DIR = ROOT / "artifacts" / "EXP002B" / "figures"

TRACK_ORDER = [
    "V0_frozen_selector",
    "V1_native_score_control",
    "V2_independent_heuristic",
    "V2_independent_learned",
    "V3_hybrid",
    "oracle",
]
COLOUR = {
    "V0_frozen_selector": "#c0392b",
    "oracle": "#27ae60",
}


def fig_accuracy_with_ci(report: dict) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    names, points, lo_err, hi_err = [], [], [], []
    for name in TRACK_ORDER:
        fc = report["track_reports"][name].get("fold_c_only")
        if not fc or not fc["accuracy_top2"]:
            continue
        acc = fc["accuracy_top2"]
        names.append(name)
        points.append(acc["point"])
        lo_err.append(acc["point"] - acc["ci_low"])
        hi_err.append(acc["ci_high"] - acc["point"])
    colours = [COLOUR.get(n, "#2980b9") for n in names]
    ax.bar(names, points, yerr=[lo_err, hi_err], capsize=4, color=colours)
    ax.set_ylabel("accuracy@2")
    ax.set_title(f"V0-V3 vs. oracle, Fold C, 95% bootstrap CI (n={report['corpus']['n_fold_c_test_indices']})")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "g1_track_accuracy_ci.png", dpi=150)
    plt.close(fig)


def fig_selective_accuracy(report: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for name in ["V0_frozen_selector", "V2_independent_learned"]:
        fc = report["track_reports"][name].get("fold_c_only")
        if not fc:
            continue
        curve = fc["selective_accuracy_by_coverage"]
        coverages = sorted((float(c) for c in curve), reverse=True)
        accs = [curve[str(c)]["accuracy"] if str(c) in curve else curve[c]["accuracy"] for c in coverages]
        ax.plot(coverages, accs, marker="o", label=name)
    ax.set_xlabel("coverage (fraction of test-indices kept, most confident first)")
    ax.set_ylabel("accuracy@2 among kept")
    ax.set_title("Selective accuracy vs. coverage, Fold C")
    ax.invert_xaxis()
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "g2_selective_accuracy.png", dpi=150)
    plt.close(fig)


def fig_feature_ablation(report: dict) -> None:
    table = report["feature_auc_independent_only_fit_dev"]
    items = sorted(
        ((name, stats["auc"], stats["n"]) for name, stats in table.items() if stats["auc"] is not None),
        key=lambda t: t[1],
    )
    names = [f"{name} (n={n})" for name, _, n in items]
    values = [v for _, v, _ in items]
    fig, ax = plt.subplots(figsize=(8, 5))
    colours = ["#27ae60" if v >= 0.6 else "#7f8c8d" for v in values]
    ax.barh(names, values, color=colours)
    ax.axvline(0.6, color="black", linestyle="--", linewidth=0.8, label="H1 threshold (0.60)")
    ax.axvline(0.5, color="grey", linestyle=":", linewidth=0.8, label="chance (0.50)")
    ax.set_xlabel("AUC (correct vs. incorrect candidate, Fold A+B)")
    ax.set_title("Strict score-independent feature ablation")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "g3_independent_feature_ablation.png", dpi=150)
    plt.close(fig)


def fig_singleton_confidence_before_after(report: dict) -> None:
    """The Part-1 fix's headline before/after: reported confidence on wrong
    singleton candidates, old (always 1.0) vs. new (backed off to the
    measured prior)."""
    v0 = report["track_reports"]["V0_frozen_selector"]["full_corpus"]["singleton_subset"]
    prior = report["corpus"]["singleton_prior_measured_on_fold_a"]
    error_rate = v0["error_rate"]

    fig, ax = plt.subplots(figsize=(6, 5))
    labels = ["old behaviour\n(pre-fix)", "new behaviour\n(this pass)"]
    reported_confidence = [1.0, v0["mean_correctness_confidence"]]
    false_confidence_at_08 = [error_rate, 0.0]  # old: every wrong singleton was >=0.8; new: none are
    x = range(len(labels))
    width = 0.35
    ax.bar([i - width / 2 for i in x], reported_confidence, width, label="reported correctness_confidence", color="#2980b9")
    ax.bar([i + width / 2 for i in x], false_confidence_at_08, width, label="false-confidence rate @0.8", color="#c0392b")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Singleton candidate sets (n={v0['n']}, {error_rate:.0%} actually wrong)\nempirical prior = {prior:.3f}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "g4_singleton_confidence_before_after.png", dpi=150)
    plt.close(fig)


def main() -> None:
    report = json.loads(REPORT_PATH.read_text())
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_accuracy_with_ci(report)
    fig_selective_accuracy(report)
    fig_feature_ablation(report)
    fig_singleton_confidence_before_after(report)
    print(f"wrote 4 figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
