"""Unit tests for SafeGate benchmark dataset manifests."""

from pathlib import Path

from ml.eval.datasets import BENCHMARK_REGISTRY, DatasetManifest, DatasetSample


def test_benchmark_registry_specs() -> None:
    """Verify registry specifications for all required real datasets."""
    required = ["FaceForensics++", "Celeb-DF-v2", "DFDC", "CASIA-v2", "GenImage"]
    for name in required:
        assert name in BENCHMARK_REGISTRY
        spec = BENCHMARK_REGISTRY[name]
        assert spec.name != ""
        assert spec.license_type != ""
        assert spec.total_samples > 0
        assert spec.download_instructions != ""


def test_dataset_manifest_filtering_and_io(tmp_path: Path) -> None:
    """Verify dataset manifest creation, sample filtering, and save/load roundtrip."""
    samples = [
        DatasetSample(
            sample_id="ff-001",
            relative_path="videos/001.mp4",
            label=0,
            generator_or_method="pristine",
            compression_level="c23_hq",
            media_type="video",
            sha256="abc001",
        ),
        DatasetSample(
            sample_id="ff-002",
            relative_path="videos/002.mp4",
            label=1,
            generator_or_method="deepfakes",
            compression_level="c23_hq",
            media_type="video",
            sha256="abc002",
        ),
        DatasetSample(
            sample_id="ff-003",
            relative_path="videos/003.mp4",
            label=1,
            generator_or_method="face2face",
            compression_level="c40_lq",
            media_type="video",
            sha256="abc003",
        ),
    ]

    manifest = DatasetManifest(dataset_name="FaceForensics++", samples=samples)
    assert len(manifest.get_pristine()) == 1
    assert len(manifest.get_manipulated()) == 2
    assert len(manifest.filter_by_compression("c40_lq")) == 1
    assert len(manifest.filter_by_generator("deepfakes")) == 1

    manifest_path = tmp_path / "ff_manifest.json"
    manifest.save_manifest(manifest_path)
    assert manifest_path.exists()

    loaded = DatasetManifest.load_manifest(manifest_path)
    assert loaded.dataset_name == "FaceForensics++"
    assert len(loaded.samples) == 3
    assert loaded.samples[0].sample_id == "ff-001"
