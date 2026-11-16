import React, { useState } from "react";

interface PostItem {
  id: string;
  username: string;
  userAvatar: string;
  location?: string;
  mediaUrl: string;
  isVideo: boolean;
  caption: string;
  likes: number;
  isLiked?: boolean;
  timestamp: string;
  safegateCleared?: boolean;
  framesAnalyzed?: number;
}

export const App: React.FC = () => {
  // Feed state with initial authentic Instagram posts
  const [feed, setFeed] = useState<PostItem[]>([
    {
      id: "post-1",
      username: "nature_lens",
      userAvatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
      location: "Yosemite National Park",
      mediaUrl: "https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=800&auto=format&fit=crop&q=80",
      isVideo: false,
      caption: "Golden hour over the valley peaks. Nothing beats crisp mountain air. 🏔️✨ #nature #mountains #wanderlust",
      likes: 3842,
      timestamp: "2 HOURS AGO",
      safegateCleared: true,
      framesAnalyzed: 1,
    },
    {
      id: "post-2",
      username: "cyber_sentinel",
      userAvatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
      location: "San Francisco, CA",
      mediaUrl: "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&auto=format&fit=crop&q=80",
      isVideo: false,
      caption: "SafeGate media firewall integrated across all upload pipelines. Pre-publication screening ensures synthetic morphing & graphic content never reach your followers. 🛡️🔐 #cybersecurity #deepfake #safegate",
      likes: 1249,
      timestamp: "5 HOURS AGO",
      safegateCleared: true,
      framesAnalyzed: 1,
    },
  ]);

  // Modal & Upload states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isVideo, setIsVideo] = useState<boolean>(false);
  const [caption, setCaption] = useState<string>("");

  // Screening pipeline states
  const [screeningStatus, setScreeningStatus] = useState<
    "IDLE" | "SCREENING" | "ALLOW" | "HUMAN_REVIEW" | "BLOCK"
  >("IDLE");
  const [screeningDetails, setScreeningDetails] = useState<{
    verdict?: string;
    totalFrames?: number;
    redFrames?: number;
    yellowFrames?: number;
    greenFrames?: number;
    message?: string;
  } | null>(null);

  const stories = [
    { username: "your_story", avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80", isUser: true },
    { username: "alexa_tech", avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80" },
    { username: "street_shots", avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80" },
    { username: "art_curator", avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&auto=format&fit=crop&q=80" },
    { username: "daily_motion", avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80" },
  ];

  const handleFileChange = (file: File) => {
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setIsVideo(file.type.startsWith("video/"));
    setScreeningStatus("IDLE");
    setScreeningDetails(null);
  };

  const createSyntheticTestBlob = (type: "clean" | "blood" | "morphed"): File => {
    // Generates a mock canvas blob for instant developer testing
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 400;
    const ctx = canvas.getContext("2d")!;

    if (type === "clean") {
      const grad = ctx.createLinearGradient(0, 0, 400, 400);
      grad.addColorStop(0, "#4f46e5");
      grad.addColorStop(1, "#06b6d4");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 400, 400);
      ctx.fillStyle = "#ffffff";
      ctx.font = "24px sans-serif";
      ctx.fillText("Authentic Camera Capture", 60, 200);
    } else if (type === "blood") {
      ctx.fillStyle = "#1a0505";
      ctx.fillRect(0, 0, 400, 400);
      ctx.fillStyle = "#b91c1c";
      ctx.beginPath();
      ctx.arc(200, 200, 140, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.font = "20px sans-serif";
      ctx.fillText("Sensitive Cues (Arterial Blood)", 60, 200);
    } else {
      // Morphed / checkerboard grid
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, 400, 400);
      for (let y = 0; y < 400; y += 4) {
        for (let x = 0; x < 400; x += 4) {
          if ((x + y) % 8 === 0) {
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(x, y, 4, 4);
          }
        }
      }
      ctx.fillStyle = "#ef4444";
      ctx.fillRect(40, 160, 320, 80);
      ctx.fillStyle = "#ffffff";
      ctx.font = "22px sans-serif";
      ctx.fillText("Synthetic Deepfake Morph", 60, 210);
    }

    // Convert to data URI / file
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    const byteString = atob(dataUrl.split(",")[1]);
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
      ia[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([ab], { type: "image/jpeg" });
    return new File([blob], `${type}_test_media.jpg`, { type: "image/jpeg" });
  };

  const handleShareToInstagram = async () => {
    if (!selectedFile) return;

    setScreeningStatus("SCREENING");
    setScreeningDetails(null);

    try {
      // 1. Instagram backend passes upload to SafeGate Firewall middleware
      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadResp = await fetch("/v1/media/upload", {
        method: "POST",
        headers: {
          "X-Tenant-ID": "instagram-production-firewall",
        },
        body: formData,
      });

      if (!uploadResp.ok) {
        throw new Error(`Upload rejected with HTTP ${uploadResp.status}`);
      }

      const uploadData = await uploadResp.json();
      const uploadId = uploadData.upload_id;

      // 2. Poll SafeGate status until final verdict reached
      pollStatus(uploadId);
    } catch (err: unknown) {
      setScreeningStatus("BLOCK");
      setScreeningDetails({
        message: err instanceof Error ? err.message : "Failed to verify media integrity.",
      });
    }
  };

  const pollStatus = async (uploadId: string) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts += 1;
      try {
        const resp = await fetch(`/v1/media/${uploadId}`, {
          headers: { "X-Tenant-ID": "instagram-production-firewall" },
        });

        if (resp.ok) {
          const data = await resp.json();

          if (data.status === "COMPLETED" || data.verdict !== "PENDING" || attempts > 15) {
            clearInterval(interval);
            const verdict = data.verdict || "ALLOW";
            setScreeningStatus(verdict as "ALLOW" | "HUMAN_REVIEW" | "BLOCK");
            setScreeningDetails({
              verdict,
              totalFrames: data.total_frames || 1,
              redFrames: data.red_frames || 0,
              yellowFrames: data.yellow_frames || 0,
              greenFrames: data.green_frames || 1,
            });

            // If ALLOW, publish directly to Instagram feed
            if (verdict === "ALLOW") {
              const newPost: PostItem = {
                id: `post-${Date.now()}`,
                username: "your_story",
                userAvatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80",
                location: "Live Feed",
                mediaUrl: previewUrl || "",
                isVideo,
                caption: caption.trim() || "Shared via Instagram with SafeGate media firewall clearance. ✨",
                likes: 0,
                timestamp: "JUST NOW",
                safegateCleared: true,
                framesAnalyzed: data.total_frames || 1,
              };
              setFeed((prev) => [newPost, ...prev]);
            }
          }
        }
      } catch (err) {
        console.error("Status polling failed:", err);
      }
    }, 1200);
  };

  const toggleLike = (postId: string) => {
    setFeed((prev) =>
      prev.map((p) => {
        if (p.id === postId) {
          const isLiked = !p.isLiked;
          return {
            ...p,
            isLiked,
            likes: isLiked ? p.likes + 1 : p.likes - 1,
          };
        }
        return p;
      })
    );
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", backgroundColor: "#000000", color: "#f5f5f5" }}>
      {/* 1. Left Instagram Navigation Sidebar */}
      <aside
        style={{
          width: "244px",
          borderRight: "1px solid #262626",
          padding: "24px 12px 20px 12px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          height: "100vh",
          flexShrink: 0,
        }}
      >
        <div>
          {/* Instagram Logo Wordmark */}
          <div style={{ padding: "0 12px", marginBottom: "36px" }}>
            <h1
              style={{
                fontFamily: "sans-serif",
                fontSize: "24px",
                fontWeight: 800,
                letterSpacing: "-0.5px",
                background: "linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                display: "inline-block",
              }}
            >
              Instagram
            </h1>
          </div>

          {/* Navigation Items */}
          <nav style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "12px 14px",
                borderRadius: "8px",
                backgroundColor: "#121212",
                fontWeight: 700,
                fontSize: "15px",
                cursor: "pointer",
              }}
            >
              <span style={{ fontSize: "20px" }}>🏠</span>
              <span>Home</span>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "12px 14px",
                borderRadius: "8px",
                fontSize: "15px",
                color: "#a8a8a8",
                cursor: "pointer",
              }}
            >
              <span style={{ fontSize: "20px" }}>🔍</span>
              <span>Search</span>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "12px 14px",
                borderRadius: "8px",
                fontSize: "15px",
                color: "#a8a8a8",
                cursor: "pointer",
              }}
            >
              <span style={{ fontSize: "20px" }}>🧭</span>
              <span>Explore</span>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "12px 14px",
                borderRadius: "8px",
                fontSize: "15px",
                color: "#a8a8a8",
                cursor: "pointer",
              }}
            >
              <span style={{ fontSize: "20px" }}>🎬</span>
              <span>Reels</span>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "12px 14px",
                borderRadius: "8px",
                fontSize: "15px",
                color: "#a8a8a8",
                cursor: "pointer",
              }}
            >
              <span style={{ fontSize: "20px" }}>💬</span>
              <span>Messages</span>
            </div>

            {/* Create Post Action Trigger */}
            <div
              onClick={() => {
                setIsCreateModalOpen(true);
                setScreeningStatus("IDLE");
                setScreeningDetails(null);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "12px 14px",
                borderRadius: "8px",
                fontSize: "15px",
                fontWeight: 600,
                color: "#ffffff",
                backgroundColor: "#1f1f1f",
                cursor: "pointer",
                border: "1px solid #363636",
                marginTop: "4px",
              }}
            >
              <span style={{ fontSize: "20px" }}>➕</span>
              <span>Create Post</span>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "12px 14px",
                borderRadius: "8px",
                fontSize: "15px",
                color: "#a8a8a8",
                cursor: "pointer",
              }}
            >
              <img
                src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80"
                alt="profile"
                style={{ width: "24px", height: "24px", borderRadius: "50%" }}
              />
              <span>Profile</span>
            </div>
          </nav>
        </div>

        {/* SafeGate Security Integration Badge */}
        <div
          style={{
            padding: "12px",
            backgroundColor: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: "10px",
            fontSize: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, color: "#38bdf8", marginBottom: "4px" }}>
            <span>🛡️</span>
            <span>SafeGate Shield</span>
          </div>
          <p style={{ color: "#8b949e", fontSize: "11px", lineHeight: "1.4" }}>
            Active upload firewall: all media screened before publishing.
          </p>
        </div>
      </aside>

      {/* 2. Main Content Stream */}
      <main style={{ flex: 1, display: "flex", justifyContent: "center", padding: "28px 20px" }}>
        <div style={{ width: "100%", maxWidth: "630px" }}>
          {/* Stories Bar */}
          <div
            style={{
              display: "flex",
              gap: "18px",
              padding: "14px 16px",
              border: "1px solid #262626",
              borderRadius: "12px",
              backgroundColor: "#000000",
              overflowX: "auto",
              marginBottom: "24px",
            }}
          >
            {stories.map((s, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  cursor: "pointer",
                  minWidth: "66px",
                }}
              >
                <div
                  style={{
                    padding: "2px",
                    borderRadius: "50%",
                    background: s.isUser
                      ? "#363636"
                      : "linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)",
                  }}
                >
                  <img
                    src={s.avatar}
                    alt={s.username}
                    style={{
                      width: "58px",
                      height: "58px",
                      borderRadius: "50%",
                      border: "2px solid #000000",
                      display: "block",
                    }}
                  />
                </div>
                <span
                  style={{
                    fontSize: "11px",
                    color: "#f5f5f5",
                    marginTop: "4px",
                    maxWidth: "68px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {s.username}
                </span>
              </div>
            ))}
          </div>

          {/* Feed Posts */}
          <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
            {feed.map((post) => (
              <article
                key={post.id}
                style={{
                  border: "1px solid #262626",
                  borderRadius: "12px",
                  backgroundColor: "#000000",
                  overflow: "hidden",
                }}
              >
                {/* Post Header */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div
                      style={{
                        padding: "2px",
                        borderRadius: "50%",
                        background: "linear-gradient(45deg, #f09433, #dc2743, #bc1888)",
                      }}
                    >
                      <img
                        src={post.userAvatar}
                        alt={post.username}
                        style={{ width: "34px", height: "34px", borderRadius: "50%", display: "block" }}
                      />
                    </div>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontWeight: 700, fontSize: "14px" }}>{post.username}</span>
                        <span style={{ color: "#8e8e8e", fontSize: "12px" }}>• {post.timestamp}</span>
                      </div>
                      {post.location && (
                        <div style={{ fontSize: "12px", color: "#a8a8a8" }}>{post.location}</div>
                      )}
                    </div>
                  </div>

                  {post.safegateCleared && (
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "10px",
                        backgroundColor: "#064e3b",
                        color: "#34d399",
                        border: "1px solid #059669",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <span>✓</span> SafeGate Cleared ({post.framesAnalyzed || 1} frames)
                    </span>
                  )}
                </div>

                {/* Media */}
                <div style={{ width: "100%", backgroundColor: "#0a0a0a" }}>
                  {post.isVideo ? (
                    <video
                      src={post.mediaUrl}
                      controls
                      style={{ width: "100%", maxHeight: "560px", display: "block", objectFit: "contain" }}
                    />
                  ) : (
                    <img
                      src={post.mediaUrl}
                      alt={post.caption}
                      style={{ width: "100%", maxHeight: "560px", display: "block", objectFit: "cover" }}
                    />
                  )}
                </div>

                {/* Post Action Buttons */}
                <div style={{ padding: "12px 16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
                    <div style={{ display: "flex", gap: "16px", fontSize: "22px" }}>
                      <span
                        onClick={() => toggleLike(post.id)}
                        style={{ cursor: "pointer", color: post.isLiked ? "#ef4444" : "#f5f5f5" }}
                      >
                        {post.isLiked ? "❤️" : "🤍"}
                      </span>
                      <span style={{ cursor: "pointer" }}>💬</span>
                      <span style={{ cursor: "pointer" }}>✈️</span>
                    </div>
                    <span style={{ fontSize: "22px", cursor: "pointer" }}>🔖</span>
                  </div>

                  {/* Likes Count */}
                  <div style={{ fontWeight: 700, fontSize: "14px", marginBottom: "6px" }}>
                    {post.likes.toLocaleString()} likes
                  </div>

                  {/* Caption */}
                  <div style={{ fontSize: "14px", lineHeight: "1.4" }}>
                    <span style={{ fontWeight: 700, marginRight: "6px" }}>{post.username}</span>
                    <span>{post.caption}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </main>

      {/* 3. Instagram "Create New Post" Modal with SafeGate Screening */}
      {isCreateModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.78)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              backgroundColor: "#262626",
              borderRadius: "14px",
              width: "720px",
              maxWidth: "92vw",
              overflow: "hidden",
              border: "1px solid #363636",
              boxShadow: "0 12px 40px rgba(0,0,0,0.8)",
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "12px 18px",
                borderBottom: "1px solid #363636",
              }}
            >
              <button
                onClick={() => setIsCreateModalOpen(false)}
                style={{ background: "none", border: "none", color: "#a8a8a8", fontSize: "18px", cursor: "pointer" }}
              >
                ✕
              </button>
              <h2 style={{ fontSize: "15px", fontWeight: 700 }}>Create new post</h2>
              {selectedFile && screeningStatus !== "SCREENING" ? (
                <button
                  onClick={handleShareToInstagram}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#0095f6",
                    fontWeight: 700,
                    fontSize: "14px",
                    cursor: "pointer",
                  }}
                >
                  Share
                </button>
              ) : (
                <div style={{ width: "40px" }} />
              )}
            </div>

            {/* Modal Body */}
            {screeningStatus === "SCREENING" ? (
              <div
                style={{
                  padding: "60px 24px",
                  textAlign: "center",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                <div style={{ fontSize: "42px", animation: "spin 2s linear infinite" }}>🛡️</div>
                <h3 style={{ fontSize: "17px", fontWeight: 700, color: "#38bdf8" }}>
                  SafeGate Media Firewall Screening
                </h3>
                <p style={{ fontSize: "13px", color: "#a8a8a8", maxWidth: "420px", lineHeight: "1.5" }}>
                  Instagram upload middleware is screening every frame for facial morphing, deepfakes,
                  graphic violence, and sensitive cues before publishing to your feed...
                </p>
                <div
                  style={{
                    width: "240px",
                    height: "4px",
                    backgroundColor: "#171717",
                    borderRadius: "2px",
                    overflow: "hidden",
                    marginTop: "8px",
                  }}
                >
                  <div
                    style={{
                      width: "100%",
                      height: "100%",
                      background: "linear-gradient(90deg, #38bdf8, #818cf8)",
                      animation: "pulse 1.5s infinite",
                    }}
                  />
                </div>
              </div>
            ) : screeningStatus === "BLOCK" ? (
              <div
                style={{
                  padding: "48px 24px",
                  textAlign: "center",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                <div style={{ fontSize: "48px" }}>🚫</div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#f87171" }}>
                  Post Blocked by SafeGate Media Firewall
                </h3>
                <p style={{ fontSize: "14px", color: "#fca5a5", maxWidth: "480px", lineHeight: "1.5" }}>
                  Content violates Instagram Integrity Standards: Confirmed deepfake or manipulated media detected
                  ({screeningDetails?.redFrames ?? 1} RED frame(s)).
                </p>
                <div
                  style={{
                    padding: "12px 18px",
                    backgroundColor: "#450a0a",
                    border: "1px solid #991b1b",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#fecaca",
                  }}
                >
                  In accordance with zero-false-allow policies, this post will NEVER be published to your feed or public CDN.
                </div>
                <button
                  onClick={() => {
                    setSelectedFile(null);
                    setPreviewUrl(null);
                    setScreeningStatus("IDLE");
                  }}
                  style={{
                    marginTop: "12px",
                    padding: "10px 24px",
                    backgroundColor: "#363636",
                    color: "#ffffff",
                    borderRadius: "8px",
                    border: "none",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Try Another Photo
                </button>
              </div>
            ) : screeningStatus === "HUMAN_REVIEW" ? (
              <div
                style={{
                  padding: "48px 24px",
                  textAlign: "center",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                <div style={{ fontSize: "48px" }}>🟡</div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#fbbf24" }}>
                  Post Held for Safety Review
                </h3>
                <p style={{ fontSize: "14px", color: "#fde68a", maxWidth: "480px", lineHeight: "1.5" }}>
                  SafeGate detected sensitive content or blood ({screeningDetails?.yellowFrames ?? 1} YELLOW frame(s)).
                  Your post has been routed to the moderation console and remains hidden until approved.
                </p>
                <button
                  onClick={() => setIsCreateModalOpen(false)}
                  style={{
                    marginTop: "12px",
                    padding: "10px 24px",
                    backgroundColor: "#0095f6",
                    color: "#ffffff",
                    borderRadius: "8px",
                    border: "none",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Understood
                </button>
              </div>
            ) : screeningStatus === "ALLOW" ? (
              <div
                style={{
                  padding: "48px 24px",
                  textAlign: "center",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                <div style={{ fontSize: "48px" }}>🟢</div>
                <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#34d399" }}>
                  Verified & Published!
                </h3>
                <p style={{ fontSize: "14px", color: "#a7f3d0" }}>
                  SafeGate verified 100% of frames ({screeningDetails?.greenFrames ?? 1} green, 0 red, 0 yellow).
                  Your post is now live on Instagram!
                </p>
                <button
                  onClick={() => setIsCreateModalOpen(false)}
                  style={{
                    marginTop: "12px",
                    padding: "10px 24px",
                    backgroundColor: "#0095f6",
                    color: "#ffffff",
                    borderRadius: "8px",
                    border: "none",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  View Feed
                </button>
              </div>
            ) : !selectedFile ? (
              /* Drag & Drop or Select Initial State */
              <div
                style={{
                  padding: "48px 24px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div style={{ fontSize: "64px", marginBottom: "16px" }}>📷</div>
                <h3 style={{ fontSize: "20px", fontWeight: 400, marginBottom: "20px" }}>
                  Drag photos and videos here
                </h3>

                <label
                  style={{
                    padding: "8px 18px",
                    backgroundColor: "#0095f6",
                    color: "#ffffff",
                    fontWeight: 600,
                    borderRadius: "8px",
                    cursor: "pointer",
                    fontSize: "14px",
                  }}
                >
                  Select from computer
                  <input
                    type="file"
                    accept="image/*,video/*"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleFileChange(f);
                    }}
                    style={{ display: "none" }}
                  />
                </label>

                {/* Quick Test Benchmarks */}
                <div
                  style={{
                    marginTop: "36px",
                    padding: "16px",
                    backgroundColor: "#1a1a1a",
                    borderRadius: "10px",
                    border: "1px solid #363636",
                    width: "100%",
                    maxWidth: "500px",
                  }}
                >
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", marginBottom: "10px" }}>
                    QUICK TEST FIREWALL DETECTION SCENARIOS:
                  </div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <button
                      onClick={() => handleFileChange(createSyntheticTestBlob("clean"))}
                      style={{
                        flex: 1,
                        padding: "8px",
                        fontSize: "12px",
                        fontWeight: 600,
                        backgroundColor: "#064e3b",
                        color: "#a7f3d0",
                        border: "1px solid #059669",
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      🟢 Authentic (Pass)
                    </button>
                    <button
                      onClick={() => handleFileChange(createSyntheticTestBlob("blood"))}
                      style={{
                        flex: 1,
                        padding: "8px",
                        fontSize: "12px",
                        fontWeight: 600,
                        backgroundColor: "#451a03",
                        color: "#fde68a",
                        border: "1px solid #d97706",
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      🟡 Blood/Sensitive (Hold)
                    </button>
                    <button
                      onClick={() => handleFileChange(createSyntheticTestBlob("morphed"))}
                      style={{
                        flex: 1,
                        padding: "8px",
                        fontSize: "12px",
                        fontWeight: 600,
                        backgroundColor: "#7f1d1d",
                        color: "#fecaca",
                        border: "1px solid #ef4444",
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      🔴 Deepfake Morph (Block)
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              /* Preview and Caption State */
              <div style={{ display: "flex", height: "460px" }}>
                <div
                  style={{
                    flex: 1.2,
                    backgroundColor: "#000000",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden",
                  }}
                >
                  {isVideo ? (
                    <video src={previewUrl!} controls style={{ width: "100%", maxHeight: "100%", objectFit: "contain" }} />
                  ) : (
                    <img src={previewUrl!} alt="preview" style={{ width: "100%", maxHeight: "100%", objectFit: "contain" }} />
                  )}
                </div>

                <div
                  style={{
                    flex: 0.8,
                    borderLeft: "1px solid #363636",
                    display: "flex",
                    flexDirection: "column",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                    <img
                      src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80"
                      alt="user"
                      style={{ width: "32px", height: "32px", borderRadius: "50%" }}
                    />
                    <span style={{ fontWeight: 700, fontSize: "14px" }}>your_story</span>
                  </div>

                  <textarea
                    rows={4}
                    value={caption}
                    onChange={(e) => setCaption(e.target.value)}
                    placeholder="Write a caption..."
                    style={{
                      width: "100%",
                      backgroundColor: "transparent",
                      border: "none",
                      color: "#f5f5f5",
                      fontSize: "14px",
                      resize: "none",
                      outline: "none",
                    }}
                  />

                  <div style={{ marginTop: "auto", borderTop: "1px solid #363636", paddingTop: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#8b949e", marginBottom: "12px" }}>
                      <span>Pre-publication Shield</span>
                      <span style={{ color: "#38bdf8", fontWeight: 600 }}>SafeGate Active</span>
                    </div>

                    <button
                      onClick={handleShareToInstagram}
                      style={{
                        width: "100%",
                        padding: "10px",
                        backgroundColor: "#0095f6",
                        color: "#ffffff",
                        fontWeight: 700,
                        border: "none",
                        borderRadius: "8px",
                        cursor: "pointer",
                      }}
                    >
                      Share Post
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
