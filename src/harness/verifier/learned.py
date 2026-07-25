"""B7 — a small, interpretable learned verifier: logistic regression over features.

`experiments/EXP002/PLAN.md` item 1: start with logistic regression; escalate
to gradient-boosted trees or a small MLP only if simpler models fail and
enough clean data exists. **No large model, ever** — that prohibition is
structural here, not just documentation: this class has no code path that
loads a checkpoint or calls out to any model bigger than what `sklearn.linear_model`
provides.

`fit()` is the one place in the verifier package allowed to see ground truth
— exactly as a training split is allowed to see labels. `rank()` never does.
"""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression

from src.harness.schemas import TaskEvidence, VerificationResult
from src.harness.verifier.base import Verifier, build_result_from_probabilities


class LearnedVerifier(Verifier):
    name = "B7_learned_logistic"

    def __init__(self, feature_names: list[str], C: float = 1.0):
        self.feature_names = feature_names
        self.model = LogisticRegression(C=C, max_iter=1000)
        self._fitted = False

    def vectorize(self, features: dict[str, float | None]) -> list[float]:
        """Missing/`None` features become 0.0. Logistic regression needs a
        fixed-width vector; a feature the archive could not compute for this
        grid (see `features/generation.py` module docstring) is treated as
        "no evidence either way" rather than dropped, which would change the
        vector's width per-example."""
        return [
            features.get(name) if features.get(name) is not None else 0.0
            for name in self.feature_names
        ]

    def fit(self, feature_rows: list[dict[str, float | None]], labels: list[bool]) -> None:
        if len(feature_rows) != len(labels):
            raise ValueError("feature_rows and labels must be the same length")
        if len(set(labels)) < 2:
            raise ValueError("logistic regression needs both classes present in the fit set")
        X = [self.vectorize(row) for row in feature_rows]
        self.model.fit(X, labels)
        self._fitted = True

    def predict_proba_one(self, features: dict[str, float | None]) -> float:
        if not self._fitted:
            raise RuntimeError("LearnedVerifier.predict_proba_one called before fit()")
        return float(self.model.predict_proba([self.vectorize(features)])[0][1])

    def rank(self, evidence: TaskEvidence) -> VerificationResult:
        if not self._fitted:
            raise RuntimeError("LearnedVerifier.rank called before fit()")
        probabilities = {
            sha1: self.predict_proba_one(features)
            for sha1, features in evidence.features_by_grid.items()
        }
        return build_result_from_probabilities(
            evidence.task_id,
            evidence.test_index,
            probabilities,
            self.name,
            provenance={name: "learned" for name in self.feature_names},
        )

    def feature_importances(self) -> dict[str, float]:
        """Coefficient magnitude per feature — the feature-ablation table's input."""
        if not self._fitted:
            raise RuntimeError("feature_importances called before fit()")
        return dict(zip(self.feature_names, self.model.coef_[0]))
