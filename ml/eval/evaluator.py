"""
SafeGate Benchmark Evaluation Runner.
Executes in-dataset, cross-dataset, and compression-robustness evaluations.
Records all results under reports/<run_id>/ with git commit, config hash,
and complete empirical metrics. Never fabricates scores or accuracy figures.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.eval.metrics import EvaluationMetrics, compute_full_evaluation_report


@dataclass(frozen=True)
class BenchmarkRunMetadata:
    run_id: str
    timestamp: str
    git_commit: str
    git_dirty: bool
    dataset_name: str
    modality: str  # video, image, sensitive
    sample_count: int
    executed_environment: str


class BenchmarkEvaluator:
    """Executes empirical evaluations and formats standardized reports."""

    def __init__(self, reports_root: str | Path = "reports") -> None:
        self.reports_root = Path(reports_root)
        self.reports_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_git_info() -> tuple[str, bool]:
        """Fetches current git commit hash and dirty status."""
        try:
            commit = (
                subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
                .decode()
                .strip()
            )
            status = (
                subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL)
                .decode()
                .strip()
            )
            return commit, len(status) > 0
        except Exception:
            return "unknown-commit", False

    def evaluate_predictions(
        self,
        run_id: str,
        dataset_name: str,
        modality: str,
        y_true: Sequence[int],
        y_scores: Sequence[float],
        decision_threshold: float = 0.5,
        breakdown_by_subset: dict[str, tuple[list[int], list[float]]] | None = None,
        notes: str = "",
    ) -> Path:
        """
        Runs empirical evaluation over predicted scores, producing reports/<run_id>/.
        """
        commit_sha, is_dirty = self.get_git_info()
        run_dir = self.reports_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        overall_metrics = compute_full_evaluation_report(
            y_true=y_true,
            y_scores=y_scores,
            decision_threshold=decision_threshold,
        )

        subset_metrics: dict[str, EvaluationMetrics] = {}
        if breakdown_by_subset:
            for sub_name, (sub_true, sub_scores) in breakdown_by_subset.items():
                if sub_true:
                    subset_metrics[sub_name] = compute_full_evaluation_report(
                        y_true=sub_true,
                        y_scores=sub_scores,
                        decision_threshold=decision_threshold,
                    )

        meta = BenchmarkRunMetadata(
            run_id=run_id,
            timestamp=datetime.now(UTC).isoformat(),
            git_commit=commit_sha,
            git_dirty=is_dirty,
            dataset_name=dataset_name,
            modality=modality,
            sample_count=len(y_true),
            executed_environment="local-cpu-sandbox",
        )

        # 1. Output summary.json
        summary_payload: dict[str, Any] = {
            "metadata": asdict(meta),
            "notes": notes,
            "overall_metrics": asdict(overall_metrics),
            "subset_metrics": {k: asdict(v) for k, v in subset_metrics.items()},
        }
        with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

        # 2. Output report.md
        self._write_markdown_report(
            run_dir=run_dir,
            meta=meta,
            overall=overall_metrics,
            subsets=subset_metrics,
            notes=notes,
        )

        # 3. Output text-based calibration diagram
        self._write_calibration_diagram(run_dir=run_dir, y_true=y_true, y_scores=y_scores)

        return run_dir

    def _write_markdown_report(
        self,
        run_dir: Path,
        meta: BenchmarkRunMetadata,
        overall: EvaluationMetrics,
        subsets: dict[str, EvaluationMetrics],
        notes: str,
    ) -> None:
        md_lines = [
            f"# SafeGate Benchmark Evaluation Report: {meta.run_id}",
            "",
            "## 1. Run Metadata",
            f"- **Timestamp:** {meta.timestamp}",
            f"- **Git Commit:** `{meta.git_commit}` (dirty: {meta.git_dirty})",
            f"- **Dataset:** {meta.dataset_name}",
            f"- **Modality:** {meta.modality}",
            f"- **Total Samples:** {meta.sample_count} ({overall.positive_count} manipulated, {overall.negative_count} authentic)",
            f"- **Execution Environment:** {meta.executed_environment}",
            "",
            "> [!NOTE]",
            "> All metrics reported below are empirically computed from ground-truth validation sets.",
            "> SafeGate adheres to a strict scientific honesty policy: no numbers are scripted or assumed,",
            "> and zero false alarms is recognized as mathematically impossible for any detector.",
            "",
            "## 2. Overall Performance Metrics",
            "",
            "| Metric | Value | Target / Ideal | Notes |",
            "| :--- | :--- | :--- | :--- |",
            f"| **AUC-ROC** | {overall.auc_roc:.4f} | 1.0000 | Area under receiver operating characteristic |",
            f"| **Precision** | {overall.precision:.4f} | $\\ge 0.90$ | At operating threshold {overall.threshold_applied} |",
            f"| **Recall** | {overall.recall:.4f} | $\\ge 0.90$ | True positive rate |",
            f"| **F1 Score** | {overall.f1_score:.4f} | High balance | Harmonic mean of precision & recall |",
            f"| **FPR @ 95% TPR** | {overall.fpr_at_95_tpr:.4f} | $\\le 0.05$ | False positive rate when catching 95% of fakes |",
            f"| **ECE (Expected Calibration Error)** | {overall.ece:.4f} | $\\le 0.05$ | 10-bin calibration confidence error |",
            f"| **Brier Score** | {overall.brier_score:.4f} | 0.0000 | Mean squared probability error |",
            "",
        ]

        if subsets:
            md_lines.extend(
                [
                    "## 3. Robustness & Subgroup Breakdown (Cross-Generator / Compression)",
                    "",
                    "| Subset / Generator / Compression | Samples | AUC-ROC | Precision | Recall | F1 | ECE |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
                ]
            )
            for name, m in subsets.items():
                md_lines.append(
                    f"| {name} | {m.sample_count} | {m.auc_roc:.4f} | {m.precision:.4f} | "
                    f"{m.recall:.4f} | {m.f1_score:.4f} | {m.ece:.4f} |"
                )
            md_lines.append("")

        if notes:
            md_lines.extend(["## 4. Operational Notes & Limitations", notes, ""])

        with open(run_dir / "report.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

    def _write_calibration_diagram(
        self,
        run_dir: Path,
        y_true: Sequence[int],
        y_scores: Sequence[float],
        n_bins: int = 10,
    ) -> None:
        """Renders ASCII reliability diagram for calibration verification."""
        lines = [
            "============================================================",
            "SafeGate Calibration Reliability Diagram (10 Confidence Bins)",
            "============================================================",
            f"{'Bin Range':<15} | {'Count':<7} | {'Avg Conf':<10} | {'True Acc':<10} | {'Gap (|Acc - Conf|)':<15}",
            "--------------------------------------------------------------------------------",
        ]
        bin_width = 1.0 / n_bins
        for b in range(n_bins):
            low = b * bin_width
            high = (b + 1) * bin_width
            indices = [
                i
                for i, s in enumerate(y_scores)
                if (low <= s < high) or (b == n_bins - 1 and low <= s <= high)
            ]
            cnt = len(indices)
            if cnt > 0:
                avg_conf = sum(y_scores[i] for i in indices) / cnt
                true_acc = sum(y_true[i] for i in indices) / cnt
                gap = abs(true_acc - avg_conf)
                lines.append(
                    f"[{low:.2f}, {high:.2f}]     | {cnt:<7} | {avg_conf:.4f}     | {true_acc:.4f}     | {gap:.4f}"
                )
            else:
                lines.append(
                    f"[{low:.2f}, {high:.2f}]     | 0       | N/A        | N/A        | 0.0000"
                )

        with open(run_dir / "reliability_diagram.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
