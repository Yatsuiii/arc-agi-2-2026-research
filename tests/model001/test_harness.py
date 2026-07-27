from __future__ import annotations

import gzip
import json
from pathlib import Path

from src.data001.generator import build_pilot_corpus
from src.model001.candidate_export import export_candidates
from src.model001.dataset import build_examples, length_stats, load_synthetic_tasks
from src.model001.evaluation import evaluate_topk
from src.model001.inference import MockGenerationModel
from src.model001.training import LoRAConfig, TrainingConfig, balanced_batches


class CharTokenizer:
    def encode(self, text: str):
        return list(text)


def test_dataset_and_evaluation_roundtrip(tmp_path: Path):
    corpus = build_pilot_corpus(tmp_path / "corpus", target_accept=12, max_attempts=24)
    tasks = load_synthetic_tasks(tmp_path / "corpus" / "tasks_train.jsonl.gz")
    programs = {row["program_id"]: type("Prog", (), {"program_id": row["program_id"]}) for row in corpus["programs"]}
    examples = build_examples(tasks[:4], programs_by_id=programs, split="train", include_trace=False)
    stats = length_stats(examples, CharTokenizer())
    assert stats["n_examples"] == len(examples)
    config = TrainingConfig(
        seed=7,
        batch_size=2,
        max_steps=3,
        learning_rate=1e-4,
        curriculum="tiered",
        target_mode="direct_grid",
        lora=LoRAConfig(),
    )
    assert config.config_hash()
    assert balanced_batches(examples, 2)
    model = MockGenerationModel()
    preds = {example.task_id: model.generate(example, k=2) for example in examples}
    report = evaluate_topk(examples, preds)
    assert report["top1_accuracy"] == 1.0


def test_candidate_export(tmp_path: Path):
    path = tmp_path / "candidates.jsonl.gz"
    export_candidates(path, [{"task_id": "t", "grid": [[1, 2]], "rank": 0}])
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        row = json.loads(next(handle))
    assert row["task_id"] == "t"
    assert row["grid"] == [[1, 2]]
