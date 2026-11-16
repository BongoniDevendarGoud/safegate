import React, { useState } from "react";

interface UploadedFeedItem {
  id: string;
  filename: string;
  status: "QUARANTINED" | "SCREENING" | "ALLOW" | "HUMAN_REVIEW" | "BLOCK";
  verdict: "ALLOW" | "HUMAN_REVIEW" | "BLOCK" | "PENDING";
  localPreviewUrl: string;
  totalFrames?: number;
  redFrames?: number;
  yellowFrames?: number;
  greenFrames?: number;
  publishedUrl?: string | null;
  message?: string;
}

export const App: React.FC = () => {
  const [feed, setFeed] = useState<UploadedFeedItem[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setErrorMsg(null);
    setIsUploading(true);

    const localUrl = URL.createObjectURL(file);
    const tempId = `temp-${Date.now()}`;

    // Add optimistic item in QUARANTINED state
    const newItem: UploadedFeedItem = {
      id: tempId,
      filename: file.name,
      status: "QUARANTINED",
      verdict: "PENDING",
      localPreviewUrl: localUrl,
    };
    setFeed((prev) => [newItem, ...prev]);

    try {
      // 1. Host app delegates media directly to SafeGate Firewall
      const formData = new FormData();
      formData.append("file", file);

      const uploadResp = await fetch("/v1/media/upload", {
        method: "POST",
        headers: {
          "X-Tenant-ID": "demo-host-platform",
        },
        body: formData,
      });

      if (!uploadResp.ok) {
        throw new Error(`Upload rejected with HTTP ${uploadResp.status}`);
      }

      const uploadData = await uploadResp.json();
      const realId = uploadData.upload_id;

      // Update feed item with real SafeGate upload_id
      setFeed((prev) =>
        prev.map((item) =>
          item.id === tempId
            ? { ...item, id: realId, status: uploadData.status, verdict: uploadData.verdict }
            : item
        )
      );

      // 2. Poll SafeGate status until final verdict reached
      pollStatus(realId);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to upload media to SafeGate.");
    } finally {
      setIsUploading(false);
    }
  };

  const pollStatus = async (uploadId: string) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts += 1;
      try {
        const resp = await fetch(`/v1/media/${uploadId}/status`);
        if (resp.ok) {
          const data = await resp.json();
          setFeed((prev) =>
            prev.map((item) =>
              item.id === uploadId
                ? {
                    ...item,
                    status: data.status,
                    verdict: data.verdict,
                    totalFrames: data.total_frames,
                    redFrames: data.red_frames,
                    yellowFrames: data.yellow_frames,
                    greenFrames: data.green_frames,
                    publishedUrl: data.published_url,
                  }
                : item
            )
          );

          if (data.status === "COMPLETED" || attempts > 20) {
            clearInterval(interval);
          }
        }
      } catch (err) {
        console.error("Status poll failed:", err);
      }
    }, 1500);
  };

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "32px 16px" }}>
      {/* Platform Header */}
      <header
        style={{
          borderBottom: "1px solid #1f2937",
          paddingBottom: "20px",
          marginBottom: "28px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#6366f1" }}>
            StreamVibe Platform
          </h1>
          <p style={{ fontSize: "13px", color: "#9ca3af" }}>
            Protected by SafeGate Pre-Publication Media-Integrity Firewall
          </p>
        </div>

        <label
          style={{
            padding: "10px 18px",
            backgroundColor: isUploading ? "#4b5563" : "#6366f1",
            color: "#ffffff",
            fontWeight: 600,
            borderRadius: "8px",
            cursor: isUploading ? "not-allowed" : "pointer",
            fontSize: "14px",
          }}
        >
          {isUploading ? "Screening Upload..." : "📤 Upload Media"}
          <input
            type="file"
            accept="image/*,video/*"
            onChange={handleFileUpload}
            disabled={isUploading}
            style={{ display: "none" }}
          />
        </label>
      </header>

      {errorMsg && (
        <div
          style={{
            padding: "12px 16px",
            backgroundColor: "#7f1d1d",
            color: "#fecaca",
            borderRadius: "6px",
            marginBottom: "20px",
            fontSize: "13px",
          }}
        >
          {errorMsg}
        </div>
      )}

      {/* Feed Stream */}
      <section>
        <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "16px" }}>Community Stream</h2>
        {feed.length === 0 ? (
          <div
            style={{
              padding: "48px",
              textAlign: "center",
              backgroundColor: "#111827",
              borderRadius: "8px",
              border: "1px dashed #374151",
              color: "#6b7280",
            }}
          >
            No posts published yet. Upload an image or video to see SafeGate firewall screening in action.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {feed.map((item) => (
              <div
                key={item.id}
                style={{
                  backgroundColor: "#111827",
                  border: "1px solid #1f2937",
                  borderRadius: "8px",
                  overflow: "hidden",
                }}
              >
                {/* Header status bar */}
                <div
                  style={{
                    padding: "12px 16px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    borderBottom: "1px solid #1f2937",
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: "14px" }}>{item.filename}</span>
                  <div>
                    {item.verdict === "ALLOW" && (
                      <span
                        style={{
                          backgroundColor: "#064e3b",
                          color: "#34d399",
                          fontSize: "12px",
                          fontWeight: 700,
                          padding: "3px 10px",
                          borderRadius: "12px",
                        }}
                      >
                        🟢 VERIFIED & PUBLISHED
                      </span>
                    )}
                    {item.verdict === "HUMAN_REVIEW" && (
                      <span
                        style={{
                          backgroundColor: "#451a03",
                          color: "#fbbf24",
                          fontSize: "12px",
                          fontWeight: 700,
                          padding: "3px 10px",
                          borderRadius: "12px",
                        }}
                      >
                        🟡 HELD IN MODERATION
                      </span>
                    )}
                    {item.verdict === "BLOCK" && (
                      <span
                        style={{
                          backgroundColor: "#7f1d1d",
                          color: "#f87171",
                          fontSize: "12px",
                          fontWeight: 700,
                          padding: "3px 10px",
                          borderRadius: "12px",
                        }}
                      >
                        🔴 BLOCKED (DEEPFAKE DETECTED)
                      </span>
                    )}
                    {item.verdict === "PENDING" && (
                      <span
                        style={{
                          backgroundColor: "#1e1b4b",
                          color: "#818cf8",
                          fontSize: "12px",
                          fontWeight: 700,
                          padding: "3px 10px",
                          borderRadius: "12px",
                        }}
                      >
                        ⏳ SCREENING IN PROGRESS
                      </span>
                    )}
                  </div>
                </div>

                {/* Media Presentation based on Firewall Decision */}
                <div style={{ padding: "16px" }}>
                  {item.verdict === "ALLOW" ? (
                    <div>
                      {item.filename.endsWith(".mp4") || item.filename.endsWith(".webm") ? (
                        <video
                          src={item.localPreviewUrl}
                          controls
                          style={{ width: "100%", maxHeight: "380px", borderRadius: "6px" }}
                        />
                      ) : (
                        <img
                          src={item.localPreviewUrl}
                          alt={item.filename}
                          style={{ width: "100%", maxHeight: "380px", objectFit: "contain", borderRadius: "6px" }}
                        />
                      )}
                      <p style={{ fontSize: "12px", color: "#10b981", marginTop: "8px" }}>
                        ✓ SafeGate cleared 100% of frames ({item.greenFrames ?? 0} green, 0 red, 0 yellow).
                      </p>
                    </div>
                  ) : item.verdict === "BLOCK" ? (
                    <div
                      style={{
                        padding: "32px 16px",
                        textAlign: "center",
                        backgroundColor: "#1f1315",
                        border: "1px solid #7f1d1d",
                        borderRadius: "6px",
                      }}
                    >
                      <div style={{ fontSize: "36px", marginBottom: "8px" }}>🚫</div>
                      <h3 style={{ fontSize: "15px", color: "#f87171", fontWeight: 700 }}>
                        Content Blocked by SafeGate Media Firewall
                      </h3>
                      <p style={{ fontSize: "12px", color: "#fca5a5", marginTop: "4px" }}>
                        Confirmed deepfake or morphed synthetic media detected ({item.redFrames ?? 1} RED frame(s)).
                        In accordance with platform safety policies, this content will never be published.
                      </p>
                    </div>
                  ) : item.verdict === "HUMAN_REVIEW" ? (
                    <div
                      style={{
                        padding: "32px 16px",
                        textAlign: "center",
                        backgroundColor: "#1c1917",
                        border: "1px solid #78350f",
                        borderRadius: "6px",
                      }}
                    >
                      <div style={{ fontSize: "36px", marginBottom: "8px" }}>🛡️</div>
                      <h3 style={{ fontSize: "15px", color: "#fbbf24", fontWeight: 700 }}>
                        Held in SafeGate Human Review Quarantine
                      </h3>
                      <p style={{ fontSize: "12px", color: "#fde68a", marginTop: "4px" }}>
                        Sensitive or uncertain cues detected ({item.yellowFrames ?? 1} YELLOW frame(s)).
                        Asset is locked in quarantine and will not appear publicly until a human moderator approves.
                      </p>
                    </div>
                  ) : (
                    <div
                      style={{
                        padding: "32px 16px",
                        textAlign: "center",
                        backgroundColor: "#1e1b4b",
                        borderRadius: "6px",
                      }}
                    >
                      <div style={{ fontSize: "28px", marginBottom: "8px" }}>⚡</div>
                      <div style={{ fontSize: "13px", color: "#a5b4fc" }}>
                        SafeGate multi-branch engine analyzing frames (Spatial, Frequency, Temporal, Sensitivity)...
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
