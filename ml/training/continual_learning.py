"""
SafeGate Continual Learning and Model Governance Engine.
Implements the human-in-the-loop active learning queue, data drift detection,
and strict candidate-model promotion gating.
Never auto-deploys unvalidated models into production.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ml.eval.metrics import EvaluationMetrics


@dataclass(frozen=True)
class ActiveLearningSample:
    sample_id: str
    media_sha256: str
    frame_index: int
    model_score: float
    model_uncertainty: float
    human_verdict: str  # 'ALLOW' or 'BLOCK'
    reviewer_notes: str
    added_at: str


@dataclass(frozen=True)
class PromotionGateResult:
    approved: bool
    incumbent_auc: float
    candidate_auc: float
    incumbent_fpr95: float
    candidate_fpr95: float
    reasons: list[str]
    evaluated_at: str


class ActiveLearningPool:
    """Manages curated edge cases from human reviewer feedback for targeted retraining."""

    def __init__(self, pool_file: str | Path = "data/active_learning_pool.json") -> None:
        self.pool_file = Path(pool_file)
        self.samples: list[ActiveLearningSample] = []
        self._load()

    def _load(self) -> None:
        if self.pool_file.exists():
            try:
                with open(self.pool_file, encoding="utf-8") as f:
                    data = json.load(f)
                self.samples = [ActiveLearningSample(**item) for item in data]
            except Exception:
                self.samples = []

    def _save(self) -> None:
        self.pool_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pool_file, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.samples], f, indent=2)

    def ingest_feedback(
        self,
        media_sha256: str,
        frame_index: int,
        model_score: float,
        model_uncertainty: float,
        human_verdict: str,
        reviewer_notes: str,
    ) -> bool:
        """
        Ingests reviewer feedback if the sample is an informative edge case:
        - High uncertainty (uncertainty >= 0.35)
        - Disagreement between model score (> 0.5) and human verdict ('ALLOW'), or vice versa.
        """
        is_disagreement = (model_score >= 0.6 and human_verdict == "ALLOW") or (
            model_score < 0.4 and human_verdict == "BLOCK"
        )
        is_high_uncertainty = model_uncertainty >= 0.35

        if not (is_disagreement or is_high_uncertainty):
            return False  # Not an informative edge case

        sample_id = f"al-{media_sha256[:8]}-f{frame_index}"
        # Deduplicate
        if any(s.sample_id == sample_id for s in self.samples):
            return False

        sample = ActiveLearningSample(
            sample_id=sample_id,
            media_sha256=media_sha256,
            frame_index=frame_index,
            model_score=model_score,
            model_uncertainty=model_uncertainty,
            human_verdict=human_verdict,
            reviewer_notes=reviewer_notes,
            added_at=datetime.now(UTC).isoformat(),
        )
        self.samples.append(sample)
        self._save()
        return True


class ModelEvaluationGate:
    """
    Enforces strict regression-testing before any candidate model can be promoted.
    A candidate model MUST:
    1. Match or exceed incumbent AUC-ROC (margin <= 0.005)
    2. Not increase False Positive Rate @ 95% TPR by more than 0.01
    3. Maintain calibration error (ECE <= 0.10)
    """

    @classmethod
    def evaluate_promotion(
        cls,
        incumbent_metrics: EvaluationMetrics,
        candidate_metrics: EvaluationMetrics,
        max_auc_drop: float = 0.005,
        max_fpr_increase: float = 0.01,
    ) -> PromotionGateResult:
        reasons: list[str] = []
        approved = True

        # Check AUC
        auc_diff = candidate_metrics.auc_roc - incumbent_metrics.auc_roc
        if auc_diff < -max_auc_drop:
            approved = False
            reasons.append(
                f"Candidate AUC ({candidate_metrics.auc_roc:.4f}) dropped by "
                f"{abs(auc_diff):.4f} relative to incumbent ({incumbent_metrics.auc_roc:.4f})."
            )

        # Check FPR @ 95% TPR
        fpr_diff = candidate_metrics.fpr_at_95_tpr - incumbent_metrics.fpr_at_95_tpr
        if fpr_diff > max_fpr_increase:
            approved = False
            reasons.append(
                f"Candidate FPR@95%TPR ({candidate_metrics.fpr_at_95_tpr:.4f}) increased by "
                f"{fpr_diff:.4f} beyond acceptable tolerance."
            )

        # Check Calibration Error
        if candidate_metrics.ece > 0.10:
            approved = False
            reasons.append(
                f"Candidate ECE ({candidate_metrics.ece:.4f}) is poorly calibrated (> 0.10)."
            )

        if approved:
            reasons.append(
                "Candidate passed all regression benchmarks and improved or maintained accuracy."
            )

        return PromotionGateResult(
            approved=approved,
            incumbent_auc=incumbent_metrics.auc_roc,
            candidate_auc=candidate_metrics.auc_roc,
            incumbent_fpr95=incumbent_metrics.fpr_at_95_tpr,
            candidate_fpr95=candidate_metrics.fpr_at_95_tpr,
            reasons=reasons,
            evaluated_at=datetime.now(UTC).isoformat(),
        )


def compute_population_stability_index(
    baseline_scores: Sequence[float],
    current_scores: Sequence[float],
    n_bins: int = 10,
) -> float:
    """
    Computes Population Stability Index (PSI) to detect data distribution drift.
    PSI < 0.10: No significant distribution change.
    0.10 <= PSI < 0.25: Moderate shift; alert team for review.
    PSI >= 0.25: Significant drift; trigger model re-calibration or retrain.
    """
    if not baseline_scores or not current_scores:
        return 0.0

    bin_width = 1.0 / n_bins
    psi = 0.0

    base_len = len(baseline_scores)
    curr_len = len(current_scores)

    for b in range(n_bins):
        low = b * bin_width
        high = (b + 1) * bin_width

        base_count = sum(
            1
            for s in baseline_scores
            if (low <= s < high) or (b == n_bins - 1 and low <= s <= high)
        )
        curr_count = sum(
            1 for s in current_scores if (low <= s < high) or (b == n_bins - 1 and low <= s <= high)
        )

        # Use Laplace (additive) smoothing to prevent zero-frequency log divergence
        base_prop = (base_count + 1) / (base_len + n_bins)
        curr_prop = (curr_count + 1) / (curr_len + n_bins)

        psi += (curr_prop - base_prop) * math.log(curr_prop / base_prop)

    return float(round(psi, 4))
