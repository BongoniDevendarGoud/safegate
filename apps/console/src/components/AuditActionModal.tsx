import React, { useState } from "react";
import { ReviewerActionRequest } from "../types";

interface AuditActionModalProps {
  uploadId: string;
  reviewerId: string;
  onClose: () => void;
  onSubmit: (actionData: ReviewerActionRequest) => Promise<void>;
  isSubmitting: boolean;
}

export const AuditActionModal: React.FC<AuditActionModalProps> = ({
  uploadId,
  reviewerId,
  onClose,
  onSubmit,
  isSubmitting,
}) => {
  const [action, setAction] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [category, setCategory] = useState<string>("False Positive - Authentic");
  const [notes, setNotes] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes.trim()) {
      setErrorMsg("Auditable justification notes are mandatory.");
      return;
    }
    setErrorMsg(null);
    try {
      await onSubmit({
        action,
        reviewer_id: reviewerId,
        category,
        notes: notes.trim(),
      });
      onClose();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to record moderation action.");
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: "#1e293b",
          border: "1px solid #475569",
          borderRadius: "8px",
          width: "500px",
          maxWidth: "90%",
          padding: "24px",
          boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
        }}
      >
        <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>
          Submit Human Moderation Verdict
        </h2>
        <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
          Upload: <code>{uploadId}</code>. This decision is cryptographically signed and permanently
          recorded in the HMAC-SHA256 audit ledger.
        </p>

        {errorMsg && (
          <div
            style={{
              padding: "8px 12px",
              backgroundColor: "#7f1d1d",
              color: "#fecaca",
              borderRadius: "4px",
              fontSize: "12px",
              marginBottom: "12px",
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              Action
            </label>
            <div style={{ display: "flex", gap: "12px" }}>
              <button
                type="button"
                onClick={() => {
                  setAction("APPROVE");
                  setCategory("False Positive - Authentic");
                }}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: "6px",
                  border: action === "APPROVE" ? "2px solid #10b981" : "1px solid #475569",
                  backgroundColor: action === "APPROVE" ? "#064e3b" : "#0f172a",
                  color: "#f8fafc",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ✅ APPROVE (Allow)
              </button>
              <button
                type="button"
                onClick={() => {
                  setAction("REJECT");
                  setCategory("Deepfake Manipulation");
                }}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: "6px",
                  border: action === "REJECT" ? "2px solid #ef4444" : "1px solid #475569",
                  backgroundColor: action === "REJECT" ? "#7f1d1d" : "#0f172a",
                  color: "#f8fafc",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                🚫 REJECT (Block)
              </button>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              Reason Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid #475569",
                backgroundColor: "#0f172a",
                color: "#f8fafc",
                fontSize: "13px",
              }}
            >
              {action === "APPROVE" ? (
                <>
                  <option value="False Positive - Authentic">False Positive - Authentic Context</option>
                  <option value="Educational / News Exception">Educational / News Exception</option>
                  <option value="Artistic / Satire Context">Artistic / Satire / Parody</option>
                  <option value="Low-Risk Mild Sensitivity">Low-Risk Mild Sensitivity Permitted</option>
                </>
              ) : (
                <>
                  <option value="Deepfake Manipulation">Confirmed Deepfake / Face Morph</option>
                  <option value="Graphic Violence / Blood">Graphic Violence / Blood Violation</option>
                  <option value="Adult Nudity / Explicit">Adult Nudity / Explicit Material</option>
                  <option value="Coordinated Disinformation">Coordinated Synthetic Disinformation</option>
                </>
              )}
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              Auditable Justification Notes *
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Explain rationale for this moderation action (required for audit ledger)..."
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid #475569",
                backgroundColor: "#0f172a",
                color: "#f8fafc",
                fontSize: "13px",
                resize: "vertical",
              }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: "1px solid #475569",
                backgroundColor: "transparent",
                color: "#cbd5e1",
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: "8px 20px",
                borderRadius: "6px",
                border: "none",
                backgroundColor: action === "APPROVE" ? "#059669" : "#dc2626",
                color: "#ffffff",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {isSubmitting ? "Signing & Recording..." : `Confirm ${action}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
