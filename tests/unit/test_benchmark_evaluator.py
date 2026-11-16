"""Unit tests for SafeGate benchmark evaluator and report generation."""

import json
from pathlib import Path

from ml.eval.evaluator import BenchmarkEvaluator


def test_benchmark_evaluator_report_generation(tmp_path: Path) -> None:
    """Verifies report creation, summary.json, report.md, and reliability diagram."""
    evaluator = BenchmarkEvaluator(reports_root=tmp_path / "reports")

    y_true = [0, 0, 0, 0, 1, 1, 1, 1]
    y_scores = [0.08, 0.12, 0.22, 0.18, 0.82, 0.79, 0.91, 0.88]

    breakdown = {
        "c23_hq": ([0, 0, 1, 1], [0.08, 0.12, 0.82, 0.79]),
        "c40_lq": ([0, 0, 1, 1], [0.22, 0.18, 0.91, 0.88]),
    }

    run_dir = evaluator.evaluate_predictions(
        run_id="test-run-001",
        dataset_name="FaceForensics++",
        modality="video",
        y_true=y_true,
        y_scores=y_scores,
        decision_threshold=0.5,
        breakdown_by_subset=breakdown,
        notes="Plumbing unit test verification run.",
    )

    assert run_dir.exists()
    summary_file = run_dir / "summary.json"
    report_file = run_dir / "report.md"
    diag_file = run_dir / "reliability_diagram.txt"

    assert summary_file.exists()
    assert report_file.exists()
    assert diag_file.exists()

    with open(summary_file, encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata"]["run_id"] == "test-run-001"
    assert data["overall_metrics"]["auc_roc"] == 1.0
    assert "c23_hq" in data["subset_metrics"]

    with open(report_file, encoding="utf-8") as f:
        md_text = f.read()

    assert "FaceForensics++" in md_text
    assert "AUC-ROC" in md_text
    assert "c23_hq" in md_text
