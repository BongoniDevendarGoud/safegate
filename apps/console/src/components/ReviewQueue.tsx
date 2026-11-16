import React from "react";
import { ReviewQueueItem } from "../types";

interface ReviewQueueProps {
  items: ReviewQueueItem[];
  selectedId: string | null;
  onSelect: (uploadId: string) => void;
  isLoading: boolean;
  onRefresh: () => void;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({
  items,
  selectedId,
  onSelect,
  isLoading,
  onRefresh,
}) => {
  return (
    <div
      style={{
        width: "360px",
        borderRight: "1px solid #334155",
        backgroundColor: "#0f172a",
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 42px)",
      }}
    >
      <div
        style={{
          padding: "16px",
          borderBottom: "1px solid #334155",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: 600 }}>Triage Queue</h2>
          <span style={{ fontSize: "12px", color: "#94a3b8" }}>
            {items.length} items requiring human review
          </span>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          style={{
            padding: "6px 12px",
            backgroundColor: "#1e293b",
            color: "#f8fafc",
            border: "1px solid #475569",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "12px",
          }}
        >
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto" }}>
        {items.length === 0 ? (
          <div style={{ padding: "32px 16px", textAlign: "center", color: "#64748b" }}>
            No uploads currently pending human review.
          </div>
        ) : (
          items.map((item) => {
            const isSelected = item.upload_id === selectedId;
            return (
              <div
                key={item.upload_id}
                onClick={() => onSelect(item.upload_id)}
                style={{
                  padding: "14px 16px",
                  borderBottom: "1px solid #1e293b",
                  backgroundColor: isSelected ? "#1e293b" : "transparent",
                  borderLeft: isSelected ? "4px solid #f59e0b" : "4px solid transparent",
                  cursor: "pointer",
                  transition: "background 0.15s ease",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "4px",
                  }}
                >
                  <span
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: isSelected ? "#f8fafc" : "#e2e8f0",
                      wordBreak: "break-all",
                    }}
                  >
                    {item.filename}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      backgroundColor: "#451a03",
                      color: "#fbbf24",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {item.yellow_frame_count} Yellow
                  </span>
                </div>

                <div
                  style={{
                    fontSize: "11px",
                    color: "#94a3b8",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span>Tenant: {item.tenant_id}</span>
                  <span>{item.total_frames} frames</span>
                </div>

                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  ID: {item.upload_id.slice(0, 8)}...
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
