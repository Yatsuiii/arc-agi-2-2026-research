"""Render EXP002's required figures from `artifacts/EXP002/exp002_report.json`.

Every figure reads that one immutable artifact; nothing here recomputes a
number the evaluation script did not already write out, per the
reproducibility requirement "generate figures directly from immutable
artifacts."

Run: `python -m src.analysis.exp002_figures`
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "artifacts" / "EXP002" / "exp002_report.json"
FIG_DIR = ROOT / "artifacts" / "EXP002" / "figures"

BASELINE_ORDER = [
    "B0_original_nvarc",
    "B1_raw_score",
    "B2_duplicate_frequency",
    "B3_augmentation_consensus",
    "B4_seed_consensus",
    "B5_score_weighted_consensus",
    "B6_transformation_consistency",
    "B7_learned_logistic",
    "B8_oracle",
]
SHORT_NAME = {name: name.split("_", 1)[1] for name in BASELINE_ORDER}


def fig_accuracy_comparison(report: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, split in zip(axes, ["full_corpus", "fold_c_only"]):
        names, accs = [], []
        for name in BASELINE_ORDER:
            entry = report["baseline_reports"][name].get(split)
            if entry is None or entry["accuracy_top2"] is None:
                continue
            names.append(SHORT_NAME[name])
            accs.append(entry["accuracy_top2"])
        colours = ["#c0392b" if n == "original_nvarc" else ("#27ae60" if n == "oracle" else "#2980b9") for n in names]
        ax.bar(names, accs, color=colours)
        ax.set_ylabel("accuracy@2")
        n = report["baseline_reports"]["B0_original_nvarc"][split]["n"] if split == "full_corpus" else report["corpus"]["n_fold_c_test_indices"]
        ax.set_title(f"{split} (n={n})")
        ax.tick_params(axis="x", rotation=60)
        ax.set_ylim(0, max(accs, default=1) * 1.2 + 0.02)
    fig.suptitle("Original vs. oracle vs. verifier accuracy@2 (RUN-001 archive, CONTAMINATED+PARTIAL)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "f1_accuracy_comparison.png", dpi=150)
    plt.close(fig)


def fig_recovered_headroom(report: dict) -> None:
    data = report["recovered_headroom_fold_c"]
    names = [SHORT_NAME[n] for n in BASELINE_ORDER if n in data and data[n] is not None]
    values = [data[n] for n in BASELINE_ORDER if n in data and data[n] is not None]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colours = ["#27ae60" if v > 0 else ("#7f8c8d" if v == 0 else "#c0392b") for v in values]
    ax.bar(names, values, color=colours)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("recovered headroom\n(verifier - original) / (oracle - original)")
    ax.set_title(f"Recovered selection headroom, Fold C (n={report['corpus']['n_fold_c_test_indices']})")
    ax.tick_params(axis="x", rotation=60)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "f2_recovered_headroom.png", dpi=150)
    plt.close(fig)


def fig_reliability_diagram(report: dict) -> None:
    calibration = report["baseline_reports"]["B7_learned_logistic"]["fold_c_only"]["calibration"]
    if calibration is None:
        return
    bins = calibration["reliability_bins"]
    confidences = [b["confidence"] for b in bins if b["confidence"] is not None]
    accuracies = [b["accuracy"] for b in bins if b["confidence"] is not None]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="grey", label="perfect calibration")
    ax.scatter(confidences, accuracies, color="#2980b9", zorder=3)
    ax.set_xlabel("mean predicted P(correct) in bin")
    ax.set_ylabel("observed accuracy in bin")
    ax.set_title(f"B7 reliability diagram, Fold C (n={calibration['n']})\nECE={calibration['expected_calibration_error']:.3f}")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "f3_reliability_diagram.png", dpi=150)
    plt.close(fig)


def fig_rank_distribution(report: dict) -> None:
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for name, colour in [("B0_original_nvarc", "#c0392b"), ("B8_oracle", "#27ae60")]:
        ranks = [r for r in report["baseline_reports"][name]["full_corpus"]["ranks_of_correct_candidate"] if r is not None]
        ax.hist(ranks, bins=range(1, max(ranks, default=1) + 2), alpha=0.6, label=SHORT_NAME[name], color=colour)
    ax.set_xlabel("rank of correct candidate (1 = top)")
    ax.set_ylabel("count of test indices")
    ax.set_title("Correct-candidate rank distribution, full corpus (n=94)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "f4_rank_distribution.png", dpi=150)
    plt.close(fig)


def fig_accuracy_by_family(report: dict) -> None:
    entry = report["baseline_reports"]["B0_original_nvarc"]["full_corpus"]["accuracy_by_task_family"]
    families = sorted({k for k in entry if not k.endswith("__n")})
    accs = [entry[f] if entry[f] is not None else 0 for f in families]
    ns = [entry[f"{f}__n"] for f in families]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar([f"{f}\n(n={n})" for f, n in zip(families, ns)], accs, color="#2980b9")
    ax.set_ylabel("B0 accuracy@2")
    ax.set_title("B0 accuracy by task family (size_relation proxy, docs/DATASET_AUDIT.md §6.4)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "f5_accuracy_by_family.png", dpi=150)
    plt.close(fig)


def fig_feature_ablation(report: dict) -> None:
    table = report["feature_auc_fit_dev"]
    items = sorted(
        ((name, stats["auc"], stats["n"]) for name, stats in table.items() if stats["auc"] is not None),
        key=lambda t: t[1],
    )
    names = [f"{name} (n={n})" for name, _, n in items]
    values = [v for _, v, _ in items]
    fig, ax = plt.subplots(figsize=(8, 6))
    colours = ["#27ae60" if v >= 0.6 else "#7f8c8d" for v in values]
    ax.barh(names, values, color=colours)
    ax.axvline(0.6, color="black", linestyle="--", linewidth=0.8, label="H1 threshold (0.60)")
    ax.axvline(0.5, color="grey", linestyle=":", linewidth=0.8, label="chance (0.50)")
    ax.set_xlabel("AUC (correct vs. incorrect candidate, Fold A+B)")
    ax.set_title("Feature ablation: per-feature discriminative AUC")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "f6_feature_ablation.png", dpi=150)
    plt.close(fig)


def fig_margin_vs_correctness(report: dict) -> None:
    entry = report["baseline_reports"]["B0_original_nvarc"]["full_corpus"]
    margins, hits = entry["margins"], entry["hits"]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    colours = ["#27ae60" if h else "#c0392b" for h in hits]
    ax.scatter(margins, [h + (0.02 * (i % 3 - 1)) for i, h in enumerate(hits)], c=colours, alpha=0.7)
    ax.set_xlabel("B0 confidence margin (top1 - top2 probability)")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["miss", "hit"])
    ax.set_title("B0 confidence margin vs. correctness, full corpus (n=94)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "f7_margin_vs_correctness.png", dpi=150)
    plt.close(fig)


def main() -> None:
    report = json.loads(REPORT_PATH.read_text())
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_accuracy_comparison(report)
    fig_recovered_headroom(report)
    fig_reliability_diagram(report)
    fig_rank_distribution(report)
    fig_accuracy_by_family(report)
    fig_feature_ablation(report)
    fig_margin_vs_correctness(report)
    print(f"wrote 7 figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
