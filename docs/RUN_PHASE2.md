# Phase 2: Model Training, Evaluation, and Registration Guide

## Current State & Honest Assessment
- **Real Trained Model Status:** **NOT CURRENTLY LOADED.**
- The existing codebase provides the end-to-end security architecture, streaming frame extractor, spatial/frequency/temporal feature extractors, temperature calibration, temporal confirmation, RFC 7807 error system, tamper-evident HMAC audit ledger, and Instagram middleware.
- However, **no deep learning model checkpoint (PyTorch / ONNX) is loaded**.
- In strict adherence to our **zero-false-allow fail-closed invariant**, the system **refuses to return ALLOW** without a registered, evaluated model checkpoint. All clean uploads route to `HUMAN_REVIEW` with reason `NO_VALIDATED_MODEL`.

---

## Prerequisites & Environment Setup

Install ML training dependencies:
```bash
python -m pip install torch torchvision timm albumentations scikit-learn pyyaml
```

---

## Step 1: Benchmark Dataset Acquisition

Download standard academic deepfake benchmark datasets (e.g. FaceForensics++, Celeb-DF v2, or GenImage):

```bash
# FaceForensics++ (c23 high-quality compressed split)
python -m ml.eval.datasets --dataset faceforensics --output-dir ./data/faceforensics

# Celeb-DF v2
python -m ml.eval.datasets --dataset celeb_df --output-dir ./data/celeb_df
```

Generate standard train/val/test split manifests:
```bash
python -m ml.training.continual_learning --prepare-splits --data-dir ./data/faceforensics --output-dir ./data/manifests/
```

---

## Step 2: Backbone Model Training

Train the dual-stream spatial-frequency neural backbone (EfficientNet-B4 + 2D FFT Spectral Residual Branch):

```bash
# Run training across 25 epochs with Cosine Annealing learning rate schedule
python -m ml.training.train \
  --backbone efficientnet_b4 \
  --train-manifest ./data/manifests/train.jsonl \
  --val-manifest ./data/manifests/val.jsonl \
  --epochs 25 \
  --batch-size 32 \
  --lr 1e-4 \
  --weight-decay 1e-5 \
  --output-dir ./models/checkpoints/
```

---

## Step 3: Empirical Threshold Optimization & Temperature Scaling

Optimize decision thresholds on the held-out validation set to guarantee $\text{FPR} \le 0.01$ (at least 95% TPR):

```bash
python -m ml.eval.thresholds \
  --checkpoint ./models/checkpoints/best_model.pt \
  --val-manifest ./data/manifests/val.jsonl \
  --target-fpr 0.01 \
  --output-config ./configs/calibrated_thresholds.yaml
```

This updates:
- `deepfake_manipulation_score.red_block_threshold` (e.g. `0.82`)
- `deepfake_manipulation_score.yellow_review_threshold` (e.g. `0.42`)
- `temperature_scaling_factor` (e.g. `1.18`)

---

## Step 4: Full Benchmark Evaluation & Report Generation

Run the evaluation engine across in-dataset and cross-dataset benchmarks to generate registered evaluation reports:

```bash
python -m ml.eval.evaluator \
  --checkpoint ./models/checkpoints/best_model.pt \
  --test-manifest ./data/manifests/test.jsonl \
  --thresholds-config ./configs/calibrated_thresholds.yaml \
  --output-reports ./reports/run_phase2_final/
```

Metrics computed and logged:
- **AUC-ROC** (Target: $\ge 0.95$)
- **FPR@95%TPR** (Target: $\le 0.05$)
- **Expected Calibration Error (ECE)** (Target: $\le 0.04$)
- **Brier Score** (Target: $\le 0.06$)

---

## Step 5: Model Registration into SafeGate Production

Compute the cryptographic SHA-256 checksum of the validated checkpoint and register it in `models/model_manifest.json`:

```bash
python -c "
import hashlib, json
from pathlib import Path

ckpt = Path('models/checkpoints/best_model.pt')
sha = hashlib.sha256(ckpt.read_bytes()).hexdigest()
manifest = {
    'model_name': 'SafeGate-SpatialFreq-DualStream',
    'version': '1.0.0',
    'checkpoint_path': str(ckpt),
    'sha256_checksum': sha,
    'status': 'VALIDATED',
    'evaluation_run_id': 'run_phase2_final',
    'calibrated_thresholds_path': 'configs/calibrated_thresholds.yaml'
}
Path('models/model_manifest.json').write_text(json.dumps(manifest, indent=2))
print(f'Registered model checkpoint with SHA-256: {sha}')
"
```

Once registered:
1. `pipeline.detector_type = "model"`
2. `pipeline.has_validated_model = True`
3. `pipeline.has_calibrated_thresholds = True`
4. The policy engine will begin clearing authentic, clean media to `ALLOW`.
