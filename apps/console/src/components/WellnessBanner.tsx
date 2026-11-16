import React, { useEffect, useState } from "react";

interface WellnessBannerProps {
  reviewerId: string;
}

export const WellnessBanner: React.FC<WellnessBannerProps> = ({ reviewerId }) => {
  const [secondsActive, setSecondsActive] = useState<number>(0);
  const [breakNeeded, setBreakNeeded] = useState<boolean>(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsActive((prev) => {
        const next = prev + 1;
        if (next >= 45 * 60) {
          setBreakNeeded(true);
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins}m ${s < 10 ? "0" : ""}${s}s`;
  };

  return (
    <div
      style={{
        backgroundColor: breakNeeded ? "#7f1d1d" : "#1e293b",
        borderBottom: "1px solid #334155",
        padding: "8px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: "13px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span
          style={{
            display: "inline-block",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            backgroundColor: breakNeeded ? "#ef4444" : "#10b981",
          }}
        />
        <span>
          Reviewer: <strong>{reviewerId}</strong>
        </span>
        <span style={{ color: "#94a3b8" }}>|</span>
        <span>Active Session: {formatTime(secondsActive)}</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <span style={{ color: breakNeeded ? "#fca5a5" : "#94a3b8" }}>
          {breakNeeded
            ? "⚠️ Session limit reached (45m). Please step away for a wellness break."
            : "🛡️ Wellness Mode: Sensitive thumbnails visually blurred by default."}
        </span>
        {breakNeeded && (
          <button
            onClick={() => {
              setSecondsActive(0);
              setBreakNeeded(false);
            }}
            style={{
              padding: "4px 10px",
              backgroundColor: "#ef4444",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Reset Timer
          </button>
        )}
      </div>
    </div>
  );
};
