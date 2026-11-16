import React, { useState } from "react";
import { FrameForensicPackage, ReviewPackageResponse } from "../types";

interface ForensicViewerProps {
  packageData: ReviewPackageResponse;
  onOpenActionModal: () => void;
}

export const ForensicViewer: React.FC<ForensicViewerProps> = ({
  packageData,
  onOpenActionModal,
}) => {
  const [selectedFrameIndex, setSelectedFrameIndex] = useState<number>(0);
  const [unblurOverride, setUnblurOverride] = useState<boolean>(false);

  const frames = packageData.frames || [];
  const activeFrame: FrameForensicPackage | undefined =
    frames[selectedFrameIndex] || frames[0];

  const getColorHex = (color: string) => {
    switch (color) {
      case "RED":
        return "#ef4444";
      case "YELLOW":
        return "#f59e0b";
      case "GREEN":
        return "#10b981";
      default:
        return "#64748b";
    }
  };

  return (
    <div
      style={{
        flex: 1,
        padding: "24px",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: "24px",
      }}
    >
      {/* Header & Action Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid #334155",
          paddingBottom: "16px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: 700 }}>{packageData.filename}</h1>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 600,
                padding: "3px 10px",
                borderRadius: "12px",
                backgroundColor: "#451a03",
                color: "#fbbf24",
                border: "1px solid #d97706",
              }}
            >
              STATUS: {packageData.verdict}
            </span>
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
            Upload ID: <code>{packageData.upload_id}</code> | Tenant: {packageData.tenant_id} | SHA-256:{" "}
            <code>{packageData.sha256_hash.slice(0, 16)}...</code>
          </div>
        </div>

        <button
          onClick={onOpenActionModal}
          style={{
            padding: "10px 20px",
            backgroundColor: "#2563eb",
            color: "#ffffff",
            fontWeight: 600,
            fontSize: "14px",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
          }}
        >
          Submit Moderation Action
        </button>
      </div>

      {/* Frame Timeline Scrub Strip */}
      <div
        style={{
          backgroundColor: "#1e293b",
          padding: "16px",
          borderRadius: "8px",
          border: "1px solid #334155",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "13px",
            marginBottom: "8px",
          }}
        >
          <span style={{ fontWeight: 600 }}>Multi-Branch Per-Frame Timeline</span>
          <span style={{ color: "#94a3b8" }}>
            Frame {activeFrame ? activeFrame.frame_index + 1 : 0} of {frames.length} (
            {activeFrame ? activeFrame.timestamp_seconds.toFixed(2) : "0.00"}s)
          </span>
        </div>

        {/* Timeline Bar */}
        <div
          style={{
            display: "flex",
            height: "36px",
            borderRadius: "4px",
            overflow: "hidden",
            backgroundColor: "#0f172a",
            cursor: "pointer",
            gap: "2px",
          }}
        >
          {frames.map((f, idx) => {
            const isSelected = idx === selectedFrameIndex;
            return (
              <div
                key={f.frame_index}
                onClick={() => setSelectedFrameIndex(idx)}
                style={{
                  flex: 1,
                  backgroundColor: getColorHex(f.color),
                  opacity: isSelected ? 1.0 : 0.65,
                  transform: isSelected ? "scaleY(1.15)" : "none",
                  transition: "all 0.1s ease",
                  borderTop: isSelected ? "3px solid #ffffff" : "none",
                }}
                title={`Frame ${f.frame_index}: ${f.color} (manip: ${f.manipulation_score.toFixed(2)})`}
              />
            );
          })}
        </div>
      </div>

      {/* Forensic Inspection Grid */}
      {activeFrame && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
          {/* Visual Frame Display with Wellness Blur */}
          <div
            style={{
              backgroundColor: "#1e293b",
              borderRadius: "8px",
              padding: "16px",
              border: "1px solid #334155",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "12px",
              }}
            >
              <h3 style={{ fontSize: "14px", fontWeight: 600 }}>Frame Evidence Preview</h3>
              <button
                onClick={() => setUnblurOverride(!unblurOverride)}
                style={{
                  fontSize: "12px",
                  padding: "4px 10px",
                  backgroundColor: unblurOverride ? "#374151" : "#1f2937",
                  color: "#e5e7eb",
                  border: "1px solid #4b5563",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                {unblurOverride ? "👁️ Hide / Re-blur" : "👁️ Unblur Evidence"}
              </button>
            </div>

            <div
              style={{
                width: "100%",
                height: "280px",
                backgroundColor: "#0f172a",
                borderRadius: "6px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                overflow: "hidden",
                border: `2px solid ${getColorHex(activeFrame.color)}`,
              }}
            >
              {activeFrame.thumbnail_blurred_b64 ? (
                <img
                  src={`data:image/jpeg;base64,${activeFrame.thumbnail_blurred_b64}`}
                  alt={`Frame ${activeFrame.frame_index}`}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    filter: unblurOverride ? "none" : "blur(18px)",
                    transition: "filter 0.2s ease",
                  }}
                />
              ) : (
                <div style={{ textAlign: "center", padding: "20px" }}>
                  <div style={{ fontSize: "36px", marginBottom: "8px" }}>🎞️</div>
                  <div style={{ fontSize: "13px", color: "#94a3b8" }}>
                    Frame {activeFrame.frame_index} ({activeFrame.timestamp_seconds.toFixed(2)}s)
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: getColorHex(activeFrame.color),
                      fontWeight: 600,
                      marginTop: "6px",
                    }}
                  >
                    Assigned: {activeFrame.color}
                  </div>
                </div>
              )}

              {!unblurOverride && (
                <div
                  style={{
                    position: "absolute",
                    backgroundColor: "rgba(15, 23, 42, 0.85)",
                    padding: "8px 16px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    color: "#f8fafc",
                    pointerEvents: "none",
                  }}
                >
                  🛡️ Visual Obfuscation Active (Wellness Mode)
                </div>
              )}
            </div>
          </div>

          {/* Forensic Scores & Cue Decomposition */}
          <div
            style={{
              backgroundColor: "#1e293b",
              borderRadius: "8px",
              padding: "16px",
              border: "1px solid #334155",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <h3 style={{ fontSize: "14px", fontWeight: 600 }}>Multi-Branch Model Scores</h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <div
                style={{
                  backgroundColor: "#0f172a",
                  padding: "12px",
                  borderRadius: "6px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>Manipulation</div>
                <div
                  style={{
                    fontSize: "18px",
                    fontWeight: 700,
                    color: activeFrame.manipulation_score > 0.5 ? "#ef4444" : "#10b981",
                  }}
                >
                  {(activeFrame.manipulation_score * 100).toFixed(1)}%
                </div>
              </div>

              <div
                style={{
                  backgroundColor: "#0f172a",
                  padding: "12px",
                  borderRadius: "6px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>Sensitivity (Blood/Nudity)</div>
                <div
                  style={{
                    fontSize: "18px",
                    fontWeight: 700,
                    color: activeFrame.sensitivity_score > 0.35 ? "#f59e0b" : "#10b981",
                  }}
                >
                  {(activeFrame.sensitivity_score * 100).toFixed(1)}%
                </div>
              </div>

              <div
                style={{
                  backgroundColor: "#0f172a",
                  padding: "12px",
                  borderRadius: "6px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>Uncertainty (σ)</div>
                <div
                  style={{
                    fontSize: "18px",
                    fontWeight: 700,
                    color: activeFrame.uncertainty >= 0.35 ? "#f59e0b" : "#94a3b8",
                  }}
                >
                  {(activeFrame.uncertainty * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Individual Branch Cues */}
            <div>
              <h4 style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "8px" }}>
                Individual Detector Branch Telemetry
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {Object.entries(activeFrame.cues || {}).map(([key, val]) => (
                  <div
                    key={key}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "12px",
                      padding: "6px 8px",
                      backgroundColor: "#0f172a",
                      borderRadius: "4px",
                    }}
                  >
                    <span style={{ color: "#cbd5e1" }}>{key}</span>
                    <span style={{ fontWeight: 600, color: val > 0.5 ? "#f87171" : "#a7f3d0" }}>
                      {typeof val === "number" ? val.toFixed(3) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
