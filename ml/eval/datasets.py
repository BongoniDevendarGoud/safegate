"""
SafeGate Evaluation Benchmark Dataset Manifests and Specification.
Defines schemas, integrity tracking, and instructions for real forensic datasets:
- Video Deepfakes: FaceForensics++ (FF++), Celeb-DF v2, DFDC
- Image Forensics: CASIA v2.0, Columbia Image Splicing, GenImage
All datasets require explicit terms-of-use compliance and license attribution.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class DatasetSample:
    sample_id: str
    relative_path: str
    label: Literal[0, 1]  # 0 = authentic / pristine, 1 = manipulated / deepfake
    generator_or_method: str  # e.g., 'pristine', 'deepfakes', 'face2face', 'midjourney'
    compression_level: str  # e.g., 'raw', 'c23_hq', 'c40_lq', 'uncompressed'
    media_type: Literal["video", "image"]
    sha256: str


@dataclass(frozen=True)
class BenchmarkDatasetSpec:
    name: str
    version: str
    license_type: str
    access_url: str
    citation: str
    total_samples: int
    pristine_samples: int
    manipulated_samples: int
    download_instructions: str


BENCHMARK_REGISTRY: dict[str, BenchmarkDatasetSpec] = {
    "FaceForensics++": BenchmarkDatasetSpec(
        name="FaceForensics++",
        version="v3_c23",
        license_type="Research Only (TUM / Google terms apply)",
        access_url="https://github.com/ondyari/FaceForensics",
        citation="Rossler et al., 'FaceForensics++: Learning to Detect Manipulated Facial Images', ICCV 2019",
        total_samples=5000,
        pristine_samples=1000,
        manipulated_samples=4000,
        download_instructions=(
            "1. Fill out the FaceForensics Google Form to request an access token.\n"
            "2. Run the official script: python download-FaceForensics.py <out_dir> -d all -c c23 -t videos\n"
            "3. Generate SafeGate manifest via `python -m ml.eval.datasets --build-manifest --dataset FF++`"
        ),
    ),
    "Celeb-DF-v2": BenchmarkDatasetSpec(
        name="Celeb-DF-v2",
        version="v2",
        license_type="Research Non-Commercial (SUNY Albany)",
        access_url="https://github.com/yuezunli/celeb-deepfakeforensics",
        citation="Li et al., 'Celeb-DF: A Large-scale Challenging Dataset for DeepFake Forensics', CVPR 2020",
        total_samples=5639,
        pristine_samples=590,
        manipulated_samples=5049,
        download_instructions=(
            "1. Request download link from authors via official form.\n"
            "2. Extract Celeb-real, Celeb-synthesis, and YouTube-real directories.\n"
            "3. Parse split files (List_of_testing_videos.txt) into SafeGate benchmark format."
        ),
    ),
    "DFDC": BenchmarkDatasetSpec(
        name="Deepfake Detection Challenge (DFDC)",
        version="full_preview",
        license_type="DFDC Challenge Terms (Meta / AWS / Partnership on AI)",
        access_url="https://ai.meta.com/datasets/dfdc/",
        citation="Dolhansky et al., 'The Deepfake Detection Challenge (DFDC) Dataset', arXiv:2006.07397 (2020)",
        total_samples=128154,
        pristine_samples=23654,
        manipulated_samples=104500,
        download_instructions=(
            "1. Download DFDC parts from Kaggle or AWS open dataset.\n"
            "2. Verify metadata.json files in each 10GB archive.\n"
            "3. Extract validation split for cross-dataset robustness evaluation."
        ),
    ),
    "CASIA-v2": BenchmarkDatasetSpec(
        name="CASIA Image Tampering Detection v2.0",
        version="v2.0",
        license_type="Academic Research (NLPR-PAT)",
        access_url="https://github.com/namtpham/casia2groundtruth",
        citation="Dong et al., 'CASIA Image Tampering Evaluation Database', IEEE ChinaSIP 2013",
        total_samples=12614,
        pristine_samples=7491,
        manipulated_samples=5123,
        download_instructions=(
            "1. Download CASIA2.0 dataset (Au for authentic, Tp for tampered/spliced/copy-move).\n"
            "2. Verify lossless TIFF and compressed JPEG subsets."
        ),
    ),
    "GenImage": BenchmarkDatasetSpec(
        name="GenImage: A Million-Scale Dataset for AI-Generated Image Detection",
        version="v1.0",
        license_type="Research / Open (NeurIPS 2023)",
        access_url="https://github.com/GenImage-Dataset/GenImage",
        citation="Zhu et al., 'GenImage: A Million-Scale Benchmark for Detecting AI-Generated Images', NeurIPS 2023",
        total_samples=1331167,
        pristine_samples=665583,
        manipulated_samples=665584,
        download_instructions=(
            "1. Download subsets across generative families: Midjourney, Stable Diffusion v1.4/v1.5, "
            "ADM, GLIDE, Wukong, VQDM, BigGAN.\n"
            "2. Used for evaluating cross-generator generalization on modern diffusion models."
        ),
    ),
}


class DatasetManifest:
    """Manages benchmark sample lists, splits, and cryptographic integrity."""

    def __init__(self, dataset_name: str, samples: list[DatasetSample]) -> None:
        self.dataset_name = dataset_name
        self.samples = samples

    def get_pristine(self) -> list[DatasetSample]:
        return [s for s in self.samples if s.label == 0]

    def get_manipulated(self) -> list[DatasetSample]:
        return [s for s in self.samples if s.label == 1]

    def filter_by_compression(self, compression: str) -> list[DatasetSample]:
        return [s for s in self.samples if s.compression_level == compression]

    def filter_by_generator(self, generator: str) -> list[DatasetSample]:
        return [s for s in self.samples if s.generator_or_method == generator]

    def save_manifest(self, out_path: str | Path) -> None:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset_name": self.dataset_name,
            "sample_count": len(self.samples),
            "samples": [asdict(s) for s in self.samples],
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_manifest(cls, manifest_path: str | Path) -> DatasetManifest:
        p = Path(manifest_path)
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        samples = [DatasetSample(**item) for item in data["samples"]]
        return cls(dataset_name=data["dataset_name"], samples=samples)
