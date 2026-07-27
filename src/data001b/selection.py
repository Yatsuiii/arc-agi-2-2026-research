from __future__ import annotations

import gzip
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from src.data001.program import Operation, Program
from src.data001.provenance import canonical_json, d4_normalized_grid_hash, grid_hash, normalized_grid_hash, pair_hash
from src.data001.task_schema import ExamplePair, SyntheticTask
from src.data001.target_formats import prompt_text
from src.data001b.descriptors import (
    coverage_report,
    describe_task,
    descriptor_signature,
    load_reference_tasks,
    load_synthetic_descriptors,
)
from src.data001b.families import FAMILY_SPECS, family_variants, generate_family_task


def write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_jsonl_gz(path: Path) -> list[dict]:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def parse_task_row(row: dict) -> SyntheticTask:
    return SyntheticTask(
        task_id=row["task_id"],
        train=[ExamplePair(**pair) for pair in row["train"]],
        test=[ExamplePair(**pair) for pair in row["test"]],
        family=row["family"],
        family_bucket=row["family_bucket"],
        curriculum_tier=row["curriculum_tier"],
        program_id=row["program_id"],
        provenance=row["provenance"],
        metadata=row["metadata"],
    )


def token_cost(task: SyntheticTask) -> dict[str, int]:
    prompt = prompt_text(task)
    direct_target = canonical_json(task.test[0].output)
    trace_target = canonical_json(task.metadata.get("trace", {}))
    tokenizer = re.compile(r"\d+|[A-Za-z_]+|\[|\]|\{|\}|:|,|\n")
    direct = len(tokenizer.findall(prompt + "\n" + direct_target))
    trace = len(tokenizer.findall(prompt + "\n" + trace_target))
    return {"direct": direct, "trace": trace}


def scene_graph_hash(task: SyntheticTask) -> str:
    desc = describe_task(task)
    payload = {
        "grid_scale": desc["grid_scale"],
        "colour_structure": desc["colour_structure"],
        "object_structure": desc["object_structure"],
        "relational_structure": desc["relational_structure"],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def transformation_trace_hash(task: SyntheticTask) -> str:
    trace = task.metadata.get("trace", {})
    return hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()


def delta_signature(task: SyntheticTask) -> str:
    train = []
    for pair in task.train:
        train.append(
            {
                "input_shape": [len(pair.input), len(pair.input[0])],
                "output_shape": [len(pair.output), len(pair.output[0])],
                "input_hash": d4_normalized_grid_hash(pair.input),
                "output_hash": d4_normalized_grid_hash(pair.output),
            }
        )
    return hashlib.sha256(json.dumps(train, sort_keys=True).encode()).hexdigest()


def correspondence_signature(task: SyntheticTask) -> str:
    trace = task.metadata.get("trace", {})
    examples = trace.get("examples", [])
    summary = [sorted(example.keys()) for example in examples[:2]]
    return hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()


def panel_layout_signature(task: SyntheticTask) -> str:
    desc = describe_task(task)
    return hashlib.sha256(json.dumps(desc["grid_scale"], sort_keys=True).encode()).hexdigest()


def composition_tree_hash(task: SyntheticTask) -> str:
    payload = {
        "family": task.family,
        "bucket": task.family_bucket,
        "depth": task.metadata.get("effective_depth"),
        "variant": task.metadata.get("variant"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def exact_task_signature(task: SyntheticTask) -> str:
    pairs = []
    for pair in task.train + task.test:
        pairs.append(pair_hash({"input": pair.input, "output": pair.output}))
    return "|".join(sorted(pairs))


def near_duplicate_signature(task: SyntheticTask) -> tuple:
    return (
        task.family_bucket,
        task.metadata.get("effective_depth", 1),
        tuple(task.metadata.get("cached_grid_scale", ())),
        tuple(task.metadata.get("cached_colour_structure", ())),
        str(task.metadata.get("scene_graph_hash", scene_graph_hash(task)))[:12],
        str(task.metadata.get("delta_signature", delta_signature(task)))[:12],
    )


def load_reference_signatures() -> dict[str, set]:
    refs = load_reference_tasks()
    all_desc = refs["arc_train"] + refs["clean_dev"] + refs["acq001_full"]
    exact = set()
    structural = set()
    for desc in all_desc:
        structural.add(descriptor_signature(desc))
    return {"exact": exact, "structural": structural}


def generate_pool(out_dir: Path, attempt_budget: int = 32000, target_valid: int = 25000) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    reference = load_reference_tasks()
    structural_ref = {descriptor_signature(desc) for group in reference.values() for desc in group}
    tasks = []
    programs = []
    quarantined = []
    rejection_counts = Counter()
    family_counts = Counter()
    depth_counts = Counter()
    seen_exact = set()
    seen_near = Counter()
    serial = 0
    attempts = 0
    family_ids = list(FAMILY_SPECS)
    while attempts < attempt_budget and len(tasks) < target_valid:
        family_id = family_ids[serial % len(family_ids)]
        spec = FAMILY_SPECS[family_id]
        variants = family_variants(spec)
        variant = variants[(serial // len(family_ids)) % len(variants)]
        serial += 1
        attempts += 1
        bundle = generate_family_task(family_id, serial, variant)
        task = bundle.task
        exact_sig = exact_task_signature(task)
        if exact_sig in seen_exact:
            rejection_counts["duplicate_exact"] += 1
            continue
        desc = describe_task(task)
        if descriptor_signature(desc) in structural_ref and task.family_bucket.endswith(spec.validation_variant):
            # conservative structural quarantine only on the closer
            # validation-like variants.
            quarantined.append(
                {
                    "task_id": task.task_id,
                    "family_bucket": task.family_bucket,
                    "similarity_reason": "reference_descriptor_signature",
                    "threshold_crossed": "descriptor_signature",
                    "kind": "structural",
                    "nearest_reference_identity": "descriptor_signature_match",
                    "disposition": "quarantine",
                }
            )
            rejection_counts["quarantined_structural"] += 1
            continue
        sig = near_duplicate_signature(task)
        if seen_near[sig] >= 4:
            rejection_counts["near_duplicate_cap"] += 1
            continue
        if task.train[0].input == task.train[0].output:
            rejection_counts["identity"] += 1
            continue
        seen_exact.add(exact_sig)
        seen_near[sig] += 1
        family_counts[task.family] += 1
        depth_counts[str(task.metadata.get("effective_depth", 1))] += 1
        task.metadata["token_cost"] = token_cost(task)
        task.metadata["scene_graph_hash"] = scene_graph_hash(task)
        task.metadata["trace_hash"] = transformation_trace_hash(task)
        task.metadata["delta_signature"] = delta_signature(task)
        task.metadata["correspondence_signature"] = correspondence_signature(task)
        task.metadata["panel_layout_signature"] = panel_layout_signature(task)
        task.metadata["composition_tree_hash"] = composition_tree_hash(task)
        task.metadata["cached_grid_scale"] = desc["grid_scale"]
        task.metadata["cached_colour_structure"] = desc["colour_structure"]
        task.metadata["cached_descriptor_signature"] = list(descriptor_signature(desc))
        tasks.append(task.to_dict())
        programs.append(bundle.program.to_dict())

    write_jsonl_gz(out_dir / "tasks.jsonl.gz", tasks)
    write_jsonl_gz(out_dir / "programs.jsonl.gz", programs)
    write_jsonl_gz(out_dir.parent / "quarantined_tasks.jsonl.gz", quarantined)
    summary = {
        "attempts": attempts,
        "accepted_pool": len(tasks),
        "rejected": attempts - len(tasks),
        "quarantine_count": len(quarantined),
        "rejection_reasons": dict(rejection_counts),
        "family_distribution": dict(family_counts),
        "depth_distribution": dict(depth_counts),
    }
    (out_dir / "generation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "pool_manifest.json").write_text(
        json.dumps(
            {
                "generator_version": "data001b.v1",
                "attempt_budget": attempt_budget,
                "target_valid": target_valid,
                "accepted_pool": len(tasks),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"summary": summary, "tasks": tasks, "programs": programs, "quarantined": quarantined}


def select_dataset(pool_tasks: list[SyntheticTask], pool_programs: dict[str, Program], out_dir: Path, target_size: int = 10000, token_budget: int = 24_000_000) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    for task in pool_tasks:
        task.metadata["token_cost"] = token_cost(task)
    target_validation = max(1200, round(target_size * 0.15))
    target_train = target_size - target_validation
    by_bucket = defaultdict(list)
    for task in pool_tasks:
        by_bucket[task.family_bucket].append(task)
    validation_buckets = {f"{family_id}:{spec.validation_variant}" for family_id, spec in FAMILY_SPECS.items()}
    train_candidates = [task for task in pool_tasks if task.family_bucket not in validation_buckets]
    val_candidates = [task for task in pool_tasks if task.family_bucket in validation_buckets]

    selected_train, train_trace = _greedy_select(train_candidates, target_train, token_budget=int(token_budget * 0.85))
    selected_val, val_trace = _greedy_select(val_candidates, target_validation, token_budget=int(token_budget * 0.15))
    selected = selected_train + selected_val
    write_jsonl_gz(out_dir / "tasks_train.jsonl.gz", [task.to_dict() for task in selected_train])
    write_jsonl_gz(out_dir / "tasks_validation.jsonl.gz", [task.to_dict() for task in selected_val])
    write_jsonl_gz(out_dir / "programs.jsonl.gz", [pool_programs[task.program_id].to_dict() for task in selected])
    write_jsonl_gz(out_dir / "selection_trace.jsonl.gz", train_trace + val_trace)

    family_manifest = {
        "train_buckets": sorted({task.family_bucket for task in selected_train}),
        "validation_buckets": sorted({task.family_bucket for task in selected_val}),
        "family_counts": dict(Counter(task.family for task in selected)),
    }
    dataset_manifest = {
        "selected_total": len(selected),
        "selected_train": len(selected_train),
        "selected_validation": len(selected_val),
        "direct_grid_token_count": sum(task.metadata["token_cost"]["direct"] for task in selected),
        "trace_token_count": sum(task.metadata["token_cost"]["trace"] for task in selected),
        "token_budget": token_budget,
        "selection_objective": "frozen_greedy_quota_diversity_token_penalty_v1",
    }
    (out_dir / "family_manifest.json").write_text(json.dumps(family_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "dataset_manifest.json").write_text(json.dumps(dataset_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"train": selected_train, "validation": selected_val, "trace": train_trace + val_trace, "manifest": dataset_manifest}


def _greedy_select(candidates: list[SyntheticTask], target_size: int, token_budget: int) -> tuple[list[SyntheticTask], list[dict]]:
    candidates = sorted(candidates, key=lambda task: (task.family, task.task_id))
    family_min = max(100, target_size // max(1, len(FAMILY_SPECS) * 3))
    depth_targets = {1: round(target_size * 0.4), 2: round(target_size * 0.4), 3: target_size - round(target_size * 0.8)}
    selected: list[SyntheticTask] = []
    trace: list[dict] = []
    family_counts = Counter()
    depth_counts = Counter()
    total_tokens = 0

    prepared = []
    signature_freq = Counter()
    for task in candidates:
        desc = describe_task(task)
        sig = descriptor_signature(desc)
        signature_freq[sig] += 1
        prepared.append({"task": task, "desc": desc, "sig": sig, "dup": near_duplicate_signature(task)})

    for item in prepared:
        task = item["task"]
        desc = item["desc"]
        rarity = 1.0 / signature_freq[item["sig"]]
        depth = int(task.metadata.get("effective_depth", 1))
        token_cost_norm = task.metadata["token_cost"]["direct"] / 3000.0
        family_bonus = 1.0 if task.metadata["size_relation"] in {"same", "larger"} else 0.6
        depth_bonus = 1.0 if depth >= 2 else 0.7
        diff_bonus = 1.0
        if desc["grid_scale"][0] in {"lg", "xl"}:
            diff_bonus += 0.6
        if desc["colour_structure"][0] in {"7-8", "9-10"}:
            diff_bonus += 0.6
        if desc["object_structure"][0] in {"7-10", "11+"}:
            diff_bonus += 0.6
        item["base_score"] = (
            4.0 * rarity
            + 2.5 * family_bonus
            + 1.5 * depth_bonus
            + 1.5 * rarity
            + 1.0 * diff_bonus
            - 1.5 * token_cost_norm
        )
        item["score_density"] = item["base_score"] / max(1.0, token_cost_norm)

    by_family = defaultdict(list)
    by_depth = defaultdict(list)
    for item in prepared:
        by_family[item["task"].family].append(item)
        by_depth[int(item["task"].metadata.get("effective_depth", 1))].append(item)
    for items in by_family.values():
        items.sort(key=lambda item: (-item["score_density"], item["task"].metadata["token_cost"]["direct"], item["task"].task_id))
    for items in by_depth.values():
        items.sort(key=lambda item: (-item["score_density"], item["task"].metadata["token_cost"]["direct"], item["task"].task_id))

    chosen_ids = set()
    recent_dup = set()

    def try_select(item, reason: str) -> bool:
        nonlocal total_tokens
        task = item["task"]
        if task.task_id in chosen_ids:
            return False
        if total_tokens + task.metadata["token_cost"]["direct"] > token_budget:
            trace.append({"task_id": task.task_id, "action": "reject_token_budget", "score": round(item["base_score"], 4)})
            return False
        if item["dup"] in recent_dup:
            trace.append({"task_id": task.task_id, "action": "reject_near_duplicate", "score": round(item["base_score"], 4)})
            return False
        selected.append(task)
        chosen_ids.add(task.task_id)
        recent_dup.add(item["dup"])
        family_counts[task.family] += 1
        depth_counts[int(task.metadata.get("effective_depth", 1))] += 1
        total_tokens += task.metadata["token_cost"]["direct"]
        trace.append(
            {
                "task_id": task.task_id,
                "action": "select",
                "reason": reason,
                "score": round(item["base_score"], 4),
                "score_density": round(item["score_density"], 4),
                "family": task.family,
                "depth": task.metadata.get("effective_depth", 1),
                "direct_tokens": task.metadata["token_cost"]["direct"],
            }
        )
        return True

    # Pass 1: minimum family representation with token-efficient tasks.
    for family, items in sorted(by_family.items()):
        for item in items:
            if family_counts[family] >= family_min or len(selected) >= target_size:
                break
            try_select(item, "family_quota")

    # Pass 2: minimum depth representation.
    for depth, items in sorted(by_depth.items()):
        for item in items:
            if depth_counts[depth] >= depth_targets[depth] or len(selected) >= target_size:
                break
            try_select(item, "depth_quota")

    # Pass 3: global fill by score density.
    ranked = sorted(prepared, key=lambda item: (-item["score_density"], item["task"].metadata["token_cost"]["direct"], item["task"].task_id))
    for item in ranked:
        if len(selected) >= target_size:
            break
        try_select(item, "global_fill")
    return selected, trace
