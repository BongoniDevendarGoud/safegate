"""
SafeGate Dual-Stream Spatial-Frequency Neural Network Model.
Stream 1: Spatial convolutional feature extractor.
Stream 2: Frequency domain 2D FFT spectral profile extractor.
Fusion Head: Joint dense projection with calibrated sigmoid probability output.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SpatialConvolutionalStream(nn.Module):
    """Convolutional backbone extracting spatial facial blending and warping features."""

    def __init__(self, out_features: int = 64) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1)
        self.bn3 = nn.BatchNorm2d(64)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(64, out_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, 3, H, W]
        h = F.leaky_relu(self.bn1(self.conv1(x)), 0.1)
        h = F.leaky_relu(self.bn2(self.conv2(h)), 0.1)
        h = F.leaky_relu(self.bn3(self.conv3(h)), 0.1)
        h = self.pool(h).flatten(1)
        return self.fc(h)


class SpectralFrequencyStream(nn.Module):
    """Dense network extracting frequency-domain spectral falloff and artifact features."""

    def __init__(self, in_features: int = 64, out_features: int = 32) -> None:
        super().__init__()
        self.fc1 = nn.Linear(in_features, 64)
        self.fc2 = nn.Linear(64, out_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, in_features]
        h = F.relu(self.fc1(x))
        return F.relu(self.fc2(h))


class SpatialFrequencyDualStreamDetector(nn.Module):
    """
    Combined dual-stream neural architecture for real-time deepfake & manipulation detection.
    """

    def __init__(self) -> None:
        super().__init__()
        self.spatial_stream = SpatialConvolutionalStream(out_features=64)
        self.frequency_stream = SpectralFrequencyStream(in_features=64, out_features=32)
        self.classifier = nn.Sequential(
            nn.Linear(64 + 32, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(
        self,
        rgb_tensor: torch.Tensor,
        freq_profile: torch.Tensor,
    ) -> torch.Tensor:
        """
        Forward pass returning raw logits.
        rgb_tensor: [B, 3, H, W] normalized in [0, 1]
        freq_profile: [B, 64] azimuthal radial spectrum
        """
        feat_spatial = self.spatial_stream(rgb_tensor)
        feat_freq = self.frequency_stream(freq_profile)
        fused = torch.cat([feat_spatial, feat_freq], dim=1)
        logits = self.classifier(fused)
        return logits.squeeze(-1)

    def predict_probability(
        self,
        rgb_tensor: torch.Tensor,
        freq_profile: torch.Tensor,
    ) -> float:
        """Returns single-sample calibrated probability in [0.0, 1.0]."""
        self.eval()
        with torch.no_grad():
            logits = self.forward(rgb_tensor, freq_profile)
            prob = torch.sigmoid(logits).item()
        return float(prob)
