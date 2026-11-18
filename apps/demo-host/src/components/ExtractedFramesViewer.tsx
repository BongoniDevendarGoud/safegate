import React, { useMemo, useState } from "react";

export interface FrameAnalysisItem {
  frame_index: number;
  timestamp_ms: number;
  color: "RED" | "YELLOW" | "GREEN" | string;
  deepfake_score: number;
  sensitive_score: number;
  uncertainty_score: number;
  cues?: Record<string, any>;
}

export interface ExtractedFramesViewerProps {
  uploadId?: string;
  totalFrames: number;
  redFrames: number;
  yellowFrames: number;
  greenFrames: number;
  frames: FrameAnalysisItem[];
  previewUrl?: string | null;
  isVideo?: boolean;
  onSeekToTimestamp?: (seconds: number) => void;
}

export const ExtractedFramesViewer: React.FC<ExtractedFramesViewerProps> = ({
  uploadId,
  totalFrames,
  redFrames,
  yellowFrames,
  greenFrames,
  frames = [],
  onSeekToTimestamp,
}) => {
  // Determine initial filter: if there are flagged frames, highlight them first
  const hasFlagged = redFrames > 0 || yellowFrames > 0;
  const [filter, setFilter] = useState<"FLAGGED" | "ALL" | "RED" | "YELLOW" | "GREEN">(
    hasFlagged ? "FLAGGED" : "ALL"
  );

  // Find initial selected frame: first RED frame, or first YELLOW, or first frame
  const initialSelected = useMemo(() => {
    const red = frames.find((f) => f.color === "RED");
    if (red) return red.frame_index;
    const yellow = frames.find((f) => f.color === "YELLOW");
    if (yellow) return yellow.frame_index;
    return frames[0]?.frame_index ?? 0;
  }, [frames]);

  const [selectedFrameIndex, setSelectedFrameIndex] = useState<number>(initialSelected);

  // Filter frames
  const filteredFrames = useMemo(() => {
    switch (filter) {
      case "FLAGGED":
        return frames.filter((f) => f.color === "RED" || f.color === "YELLOW");
      case "RED":
        return frames.filter((f) => f.color === "RED");
      case "YELLOW":
        return frames.filter((f) => f.color === "YELLOW");
      case "GREEN":
        return frames.filter((f) => f.color === "GREEN");
      case "ALL":
      default:
        return frames;
    }
  }, [frames, filter]);

  const selectedFrame = useMemo(() => {
    return frames.find((f) => f.frame_index === selectedFrameIndex) || frames[0];
  }, [frames, selectedFrameIndex]);

  const getColorHex = (color: string) => {
    switch (color) {
      case "RED":
        return "#ef4444";
      case "YELLOW":
        return "#f59e0b";
      case "GREEN":
        return "#10b981";
      default:
        return "#6b7280";
    }
  };

  const getFrameImageUrl = (frameIndex: number) => {
    const f = frames.find((x) => x.frame_index === frameIndex);
    if (f && (f as any).thumbnailUrl) {
      return (f as any).thumbnailUrl;
    }
    if (uploadId) {
      return `/v1/media/${uploadId}/frames/${frameIndex}`;
    }
    return "";
  };

  const handleSeek = (tsMs: number) => {
    if (onSeekToTimestamp) {
      onSeekToTimestamp(tsMs / 1000);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        backgroundColor: "#18181b",
        border: "1px solid #27272a",
        borderRadius: "12px",
        padding: "16px",
        marginTop: "16px",
        textAlign: "left",
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      {/* Header & Badges */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          borderBottom: "1px solid #27272a",
          paddingBottom: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "18px" }}>🎞️</span>
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#f4f4f5", margin: 0 }}>
              Extracted Frames & Forensic Inspector
            </h3>
          </div>
          <p style={{ fontSize: "12px", color: "#a1a1aa", margin: "4px 0 0 0" }}>
            100% full-sequence inspection ({totalFrames} frames extracted & analyzed).
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <span
            style={{
              padding: "4px 10px",
              borderRadius: "16px",
              backgroundColor: "#450a0a",
              color: "#fca5a5",
              border: "1px solid #7f1d1d",
              fontSize: "12px",
              fontWeight: 700,
            }}
          >
            🔴 {redFrames} RED (Manipulated)
          </span>
          <span
            style={{
              padding: "4px 10px",
              borderRadius: "16px",
              backgroundColor: "#451a03",
              color: "#fde68a",
              border: "1px solid #78350f",
              fontSize: "12px",
              fontWeight: 700,
            }}
          >
            🟡 {yellowFrames} YELLOW (Review)
          </span>
          <span
            style={{
              padding: "4px 10px",
              borderRadius: "16px",
              backgroundColor: "#052e16",
              color: "#86efac",
              border: "1px solid #14532d",
              fontSize: "12px",
              fontWeight: 700,
            }}
          >
            🟢 {greenFrames} GREEN (Authentic)
          </span>
        </div>
      </div>

      {/* Timeline Integrity Heatmap Strip */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#71717a", marginBottom: "4px" }}>
          <span>Timeline Scrubber: 0:00</span>
          <span>Click any slice to jump to that frame</span>
          <span>
            {frames.length > 0 ? `${(frames[frames.length - 1].timestamp_ms / 1000).toFixed(1)}s` : "End"}
          </span>
        </div>
        <div
          style={{
            display: "flex",
            height: "18px",
            backgroundColor: "#09090b",
            borderRadius: "6px",
            overflow: "hidden",
            border: "1px solid #3f3f46",
            cursor: "pointer",
            position: "relative",
          }}
          title="Timeline Integrity Bar"
        >
          {frames.map((f) => {
            const isSelected = f.frame_index === selectedFrameIndex;
            return (
              <div
                key={f.frame_index}
                onClick={() => {
                  setSelectedFrameIndex(f.frame_index);
                  handleSeek(f.timestamp_ms);
                }}
                style={{
                  flex: 1,
                  backgroundColor: getColorHex(f.color),
                  opacity: isSelected ? 1 : 0.75,
                  borderTop: isSelected ? "3px solid #ffffff" : "none",
                  borderBottom: isSelected ? "3px solid #ffffff" : "none",
                  boxSizing: "border-box",
                  transition: "opacity 0.15s ease",
                }}
                title={`Frame #${f.frame_index} (${(f.timestamp_ms / 1000).toFixed(2)}s): ${f.color} - Score: ${(f.deepfake_score * 100).toFixed(1)}%`}
              />
            );
          })}
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        {hasFlagged && (
          <button
            onClick={() => setFilter("FLAGGED")}
            style={{
              padding: "5px 12px",
              borderRadius: "6px",
              border: filter === "FLAGGED" ? "1px solid #ef4444" : "1px solid #3f3f46",
              backgroundColor: filter === "FLAGGED" ? "#450a0a" : "#27272a",
              color: filter === "FLAGGED" ? "#fca5a5" : "#d4d4d8",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ⚠️ Flagged Only ({redFrames + yellowFrames})
          </button>
        )}
        <button
          onClick={() => setFilter("ALL")}
          style={{
            padding: "5px 12px",
            borderRadius: "6px",
            border: filter === "ALL" ? "1px solid #38bdf8" : "1px solid #3f3f46",
            backgroundColor: filter === "ALL" ? "#082f49" : "#27272a",
            color: filter === "ALL" ? "#bae6fd" : "#d4d4d8",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          All Frames ({frames.length})
        </button>
        {redFrames > 0 && (
          <button
            onClick={() => setFilter("RED")}
            style={{
              padding: "5px 12px",
              borderRadius: "6px",
              border: filter === "RED" ? "1px solid #ef4444" : "1px solid #3f3f46",
              backgroundColor: filter === "RED" ? "#450a0a" : "#27272a",
              color: filter === "RED" ? "#fca5a5" : "#d4d4d8",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🔴 Red ({redFrames})
          </button>
        )}
        {yellowFrames > 0 && (
          <button
            onClick={() => setFilter("YELLOW")}
            style={{
              padding: "5px 12px",
              borderRadius: "6px",
              border: filter === "YELLOW" ? "1px solid #f59e0b" : "1px solid #3f3f46",
              backgroundColor: filter === "YELLOW" ? "#451a03" : "#27272a",
              color: filter === "YELLOW" ? "#fde68a" : "#d4d4d8",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🟡 Yellow ({yellowFrames})
          </button>
        )}
        {greenFrames > 0 && (
          <button
            onClick={() => setFilter("GREEN")}
            style={{
              padding: "5px 12px",
              borderRadius: "6px",
              border: filter === "GREEN" ? "1px solid #10b981" : "1px solid #3f3f46",
              backgroundColor: filter === "GREEN" ? "#052e16" : "#27272a",
              color: filter === "GREEN" ? "#86efac" : "#d4d4d8",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🟢 Green ({greenFrames})
          </button>
        )}
      </div>

      {/* Main Extracted Frames Gallery & Zoom Inspector Layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 340px",
          gap: "16px",
          minHeight: "320px",
        }}
      >
        {/* Left: Scrollable Frames Filmstrip Grid */}
        <div
          style={{
            maxHeight: "360px",
            overflowY: "auto",
            paddingRight: "8px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
            gap: "10px",
            alignContent: "start",
          }}
        >
          {filteredFrames.length === 0 ? (
            <div style={{ color: "#71717a", fontSize: "13px", padding: "20px" }}>
              No frames match the active filter.
            </div>
          ) : (
            filteredFrames.map((f) => {
              const isSelected = f.frame_index === selectedFrameIndex;
              const imgUrl = getFrameImageUrl(f.frame_index);

              return (
                <div
                  key={f.frame_index}
                  onClick={() => {
                    setSelectedFrameIndex(f.frame_index);
                    handleSeek(f.timestamp_ms);
                  }}
                  style={{
                    backgroundColor: "#09090b",
                    borderRadius: "8px",
                    overflow: "hidden",
                    border: isSelected
                      ? "2px solid #38bdf8"
                      : `2px solid ${getColorHex(f.color)}`,
                    cursor: "pointer",
                    position: "relative",
                    display: "flex",
                    flexDirection: "column",
                    boxShadow: isSelected ? "0 0 10px rgba(56, 189, 248, 0.4)" : "none",
                    transition: "transform 0.1s ease, border-color 0.15s ease",
                  }}
                >
                  {/* Thumbnail Image */}
                  <div
                    style={{
                      width: "100%",
                      height: "82px",
                      backgroundColor: "#18181b",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    {imgUrl ? (
                      <img
                        src={imgUrl}
                        alt={`Frame #${f.frame_index}`}
                        loading="lazy"
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          display: "block",
                        }}
                        onError={(e) => {
                          // Hide broken image placeholder
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : null}

                    {/* Badge Overlay */}
                    <div
                      style={{
                        position: "absolute",
                        top: "4px",
                        left: "4px",
                        backgroundColor: "rgba(0, 0, 0, 0.75)",
                        color: "#ffffff",
                        padding: "1px 5px",
                        borderRadius: "4px",
                        fontSize: "10px",
                        fontWeight: 700,
                      }}
                    >
                      #{f.frame_index}
                    </div>

                    <div
                      style={{
                        position: "absolute",
                        bottom: "4px",
                        right: "4px",
                        backgroundColor: getColorHex(f.color),
                        color: "#000000",
                        padding: "1px 5px",
                        borderRadius: "4px",
                        fontSize: "9px",
                        fontWeight: 800,
                      }}
                    >
                      {(f.timestamp_ms / 1000).toFixed(2)}s
                    </div>
                  </div>

                  {/* Frame Meta footer */}
                  <div
                    style={{
                      padding: "6px 8px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      backgroundColor: "#18181b",
                      fontSize: "11px",
                    }}
                  >
                    <span style={{ color: getColorHex(f.color), fontWeight: 700 }}>
                      {f.color}
                    </span>
                    <span style={{ color: "#a1a1aa", fontSize: "10px" }}>
                      {(f.deepfake_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right: Selected Frame Zoom & Forensic Inspector */}
        {selectedFrame && (
          <div
            style={{
              backgroundColor: "#09090b",
              borderRadius: "10px",
              border: `1px solid ${getColorHex(selectedFrame.color)}`,
              padding: "14px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              maxHeight: "360px",
              overflowY: "auto",
            }}
          >
            {/* Enlarged Frame View */}
            <div
              style={{
                width: "100%",
                height: "140px",
                backgroundColor: "#000000",
                borderRadius: "6px",
                overflow: "hidden",
                border: "1px solid #27272a",
                position: "relative",
              }}
            >
              {getFrameImageUrl(selectedFrame.frame_index) ? (
                <img
                  src={getFrameImageUrl(selectedFrame.frame_index)}
                  alt={`Frame #${selectedFrame.frame_index}`}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    display: "block",
                  }}
                />
              ) : null}
              <div
                style={{
                  position: "absolute",
                  bottom: "6px",
                  left: "6px",
                  backgroundColor: "rgba(0,0,0,0.85)",
                  color: "#f4f4f5",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                }}
              >
                Frame #{selectedFrame.frame_index} • {(selectedFrame.timestamp_ms / 1000).toFixed(3)}s
              </div>
            </div>

            {/* Diagnostic Details */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "12px", color: "#a1a1aa" }}>Classification:</span>
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 800,
                    color: getColorHex(selectedFrame.color),
                  }}
                >
                  {selectedFrame.color === "RED"
                    ? "🔴 SPLICED / MANIPULATED"
                    : selectedFrame.color === "YELLOW"
                    ? "🟡 SUSPICIOUS DISCONTINUITY"
                    : "🟢 CLEAN & AUTHENTIC"}
                </span>
              </div>

              {/* Manipulation Gauge */}
              <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                  <span style={{ color: "#d4d4d8" }}>Deepfake / Splice Score:</span>
                  <span style={{ fontWeight: 700, color: getColorHex(selectedFrame.color) }}>
                    {(selectedFrame.deepfake_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ height: "6px", backgroundColor: "#27272a", borderRadius: "3px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, Math.max(0, selectedFrame.deepfake_score * 100))}%`,
                      backgroundColor: getColorHex(selectedFrame.color),
                    }}
                  />
                </div>
              </div>

              {/* Uncertainty Gauge */}
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#a1a1aa" }}>
                <span>Model Uncertainty:</span>
                <span style={{ color: "#d4d4d8" }}>
                  {(selectedFrame.uncertainty_score * 100).toFixed(1)}%
                </span>
              </div>

              {/* Anomaly Cues */}
              {selectedFrame.cues && (
                <div
                  style={{
                    backgroundColor: "#18181b",
                    padding: "8px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    lineHeight: "1.4",
                    color: "#d4d4d8",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                    border: "1px solid #27272a",
                  }}
                >
                  <strong style={{ color: "#f4f4f5" }}>Forensic Cues:</strong>
                  {selectedFrame.cues.temporal?.frame_diff !== undefined && (
                    <div>• Frame Diff: {selectedFrame.cues.temporal.frame_diff.toFixed(2)}</div>
                  )}
                  {selectedFrame.cues.temporal?.acceleration !== undefined && (
                    <div>• Optical Flow Accel: {selectedFrame.cues.temporal.acceleration.toFixed(2)}</div>
                  )}
                  {selectedFrame.cues.gemini_ai?.explanation && (
                    <div style={{ color: "#93c5fd" }}>
                      • <strong>Gemini Vision:</strong> {selectedFrame.cues.gemini_ai.explanation}
                    </div>
                  )}
                </div>
              )}

              {/* Seek Button */}
              {onSeekToTimestamp && (
                <button
                  onClick={() => handleSeek(selectedFrame.timestamp_ms)}
                  style={{
                    marginTop: "6px",
                    padding: "6px 12px",
                    backgroundColor: "#27272a",
                    border: "1px solid #3f3f46",
                    borderRadius: "6px",
                    color: "#f4f4f5",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  ▶ Seek Preview to {(selectedFrame.timestamp_ms / 1000).toFixed(2)}s
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
