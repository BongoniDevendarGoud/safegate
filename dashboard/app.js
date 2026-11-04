/**
 * SafeGate Sentinel — 24 FPS Video Integrity & Deepfake Controller
 * ================================================================
 * Pure Vanilla JavaScript:
 * - 24 FPS Frame Extraction & Frame-by-Frame Legitimate / Modified Marking
 * - Prominent RED COLOR MARK for Legitimate Frames
 * - 1-Click Test Buttons (Authentic vs Deepfake 24 FPS Samples)
 * - Lightbox Frame Modal
 * - Review Queue & Cryptographic Audit Verification
 */

// Application State
let selectedFile = null;
let currentFramesData = [];
let activeFilter = "all";

// Enterprise API Key defaults
const DEFAULT_CLIENT_KEY = "dev-client-key-change-in-production-98765";
const DEFAULT_ADMIN_KEY = "dev-admin-key-change-in-production-12345";
const STORAGE_ADMIN_KEY = "safegate_admin_key";
const STORAGE_CLIENT_KEY = "safegate_client_key";

function getAdminKey() {
  const el = document.getElementById("adminKeyInput");
  return (el && el.value.trim()) || localStorage.getItem(STORAGE_ADMIN_KEY) || DEFAULT_ADMIN_KEY;
}

function getClientKey() {
  const el = document.getElementById("clientKeyInput");
  return (el && el.value.trim()) || localStorage.getItem(STORAGE_CLIENT_KEY) || DEFAULT_CLIENT_KEY;
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initApiKeys();
  setupTabNavigation();
  setupDropZone();
  setupUploadActions();
  setupQuickDemoButtons();
  setupFilterControls();
  setupFrameModal();
  setupReviewQueue();
  setupDecisions();
  setupAuditVerification();

  // Load telemetry stats
  loadStats();
});

// 1. API Keys & Drawer Setup
function initApiKeys() {
  const savedAdmin = localStorage.getItem(STORAGE_ADMIN_KEY) || DEFAULT_ADMIN_KEY;
  const savedClient = localStorage.getItem(STORAGE_CLIENT_KEY) || DEFAULT_CLIENT_KEY;

  const adminInput = document.getElementById("adminKeyInput");
  const clientInput = document.getElementById("clientKeyInput");
  if (adminInput) adminInput.value = savedAdmin;
  if (clientInput) clientInput.value = savedClient;

  const drawer = document.getElementById("authDrawer");
  const openBtn = document.getElementById("authConfigBtn");
  const closeBtn = document.getElementById("closeAuthDrawer");
  const saveBtn = document.getElementById("saveKeysBtn");

  if (openBtn && drawer) {
    openBtn.addEventListener("click", () => drawer.classList.toggle("hidden"));
  }
  if (closeBtn && drawer) {
    closeBtn.addEventListener("click", () => drawer.classList.add("hidden"));
  }
  if (saveBtn) {
    saveBtn.addEventListener("click", () => {
      localStorage.setItem(STORAGE_ADMIN_KEY, getAdminKey());
      localStorage.setItem(STORAGE_CLIENT_KEY, getClientKey());
      drawer.classList.add("hidden");
    });
  }
}

// 2. Tab Navigation
function setupTabNavigation() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");

      if (targetId === "tab-review") loadReviewQueue();
      if (targetId === "tab-decisions") loadDecisions();
      if (targetId === "tab-audit") loadAuditLogs();
    });
  });
}

// 3. Drop Zone & File Selection
function setupDropZone() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const fileInfo = document.getElementById("fileSelectedInfo");
  const uploadBtn = document.getElementById("uploadBtn");
  const clearBtn = document.getElementById("clearBtn");

  ["dragenter", "dragover"].forEach(ev => {
    dropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(ev => {
    dropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  clearBtn.addEventListener("click", resetUploadState);

  function handleFileSelected(file) {
    selectedFile = file;
    fileInfo.innerHTML = `<span>Selected: <strong>${file.name}</strong> (${(file.size / (1024 * 1024)).toFixed(2)} MB)</span>`;
    fileInfo.classList.remove("hidden");
    uploadBtn.disabled = false;
  }
}

function resetUploadState() {
  selectedFile = null;
  document.getElementById("fileInput").value = "";
  document.getElementById("fileSelectedInfo").classList.add("hidden");
  document.getElementById("uploadBtn").disabled = true;
  document.getElementById("uploadProgress").classList.add("hidden");
  document.getElementById("framesResultsSection").classList.add("hidden");
}

// 4. Quick Demo 1-Click Buttons
function setupQuickDemoButtons() {
  const cleanBtn = document.getElementById("quickTestCleanBtn");
  const dfBtn = document.getElementById("quickTestDeepfakeBtn");

  if (cleanBtn) {
    cleanBtn.addEventListener("click", () => runQuickSampleTest("clean"));
  }
  if (dfBtn) {
    dfBtn.addEventListener("click", () => runQuickSampleTest("deepfake"));
  }
}

async function runQuickSampleTest(sampleType) {
  const progress = document.getElementById("uploadProgress");
  const progressFill = document.getElementById("progressBarFill");
  const progressText = document.getElementById("progressText");

  progress.classList.remove("hidden");
  progressFill.style.width = "40%";
  progressText.textContent = `Extracting 24 frames/sec from ${sampleType} video sample...`;

  try {
    const res = await fetch(`/api/sample-inspect/${sampleType}`);
    progressFill.style.width = "90%";

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to inspect sample video");
    }

    const data = await res.json();
    progressFill.style.width = "100%";
    setTimeout(() => {
      progress.classList.add("hidden");
      render24FramesResult(data);
    }, 300);
  } catch (err) {
    progress.classList.add("hidden");
    alert("Test Error: " + err.message);
  }
}

// 5. Upload & Live 24 FPS Screening
function setupUploadActions() {
  const uploadBtn = document.getElementById("uploadBtn");
  const progress = document.getElementById("uploadProgress");
  const progressFill = document.getElementById("progressBarFill");
  const progressText = document.getElementById("progressText");

  uploadBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    uploadBtn.disabled = true;
    progress.classList.remove("hidden");
    progressFill.style.width = "30%";
    progressText.textContent = "Uploading bitstream & extracting 24 frames per second...";

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      progressFill.style.width = "60%";
      progressText.textContent = "Screening frames & marking legitimate content in red...";

      const res = await fetch("/api/upload", {
        method: "POST",
        headers: {
          "X-API-Key": getClientKey(),
        },
        body: formData,
      });

      progressFill.style.width = "90%";

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || `Upload failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      progressFill.style.width = "100%";
      progressText.textContent = "Verification complete!";

      setTimeout(() => {
        progress.classList.add("hidden");
        uploadBtn.disabled = false;
        render24FramesResult(data);
        loadStats();
      }, 350);

    } catch (err) {
      progress.classList.add("hidden");
      uploadBtn.disabled = false;
      alert("Verification Failed: " + err.message);
    }
  });
}

// 6. RENDER 24 FRAMES RESULT WITH RED MARK FOR LEGITIMATE FRAMES
function render24FramesResult(data) {
  const section = document.getElementById("framesResultsSection");
  const banner = document.getElementById("verdictBannerBox");
  const badgeText = document.getElementById("verdictBadgeText");
  const tagline = document.getElementById("verdictTagline");
  const totalCountEl = document.getElementById("totalFramesCount");
  const legitCountEl = document.getElementById("legitFramesCount");
  const modCountEl = document.getElementById("modFramesCount");
  const grid = document.getElementById("framesGrid");

  section.classList.remove("hidden");

  // Verdict Banner
  const v = data.verdict || "ALLOW";
  badgeText.textContent = v;
  banner.className = "verdict-banner-box";

  if (v === "ALLOW") {
    badgeText.className = "verdict-indicator verdict-allow";
    tagline.textContent = `Pristine Video: ${data.explanation}`;
  } else if (v === "REVIEW") {
    badgeText.className = "verdict-indicator verdict-review";
    tagline.textContent = `Quarantine Flagged: ${data.explanation}`;
  } else {
    badgeText.className = "verdict-indicator verdict-block";
    tagline.textContent = `Prohibited Content: ${data.explanation}`;
  }

  // Counts
  const frames = data.frames || [];
  currentFramesData = frames;

  const total = frames.length || data.total_frames_extracted || 24;
  const legitCount = frames.filter(f => f.status === "LEGITIMATE").length;
  const modCount = total - legitCount;

  totalCountEl.textContent = total;
  legitCountEl.textContent = legitCount;
  modCountEl.textContent = modCount;

  document.getElementById("filterAllCount").textContent = total;
  document.getElementById("filterLegitCount").textContent = legitCount;
  document.getElementById("filterModCount").textContent = modCount;

  // Render Grid
  renderFramesGrid(frames);

  // Scroll to results
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderFramesGrid(frames) {
  const grid = document.getElementById("framesGrid");
  grid.innerHTML = "";

  if (!frames || frames.length === 0) {
    grid.innerHTML = "<div class='empty-state'>No frames extracted.</div>";
    return;
  }

  const filtered = frames.filter(f => {
    if (activeFilter === "legit") return f.status === "LEGITIMATE";
    if (activeFilter === "mod") return f.status === "MODIFIED";
    return true;
  });

  filtered.forEach(frame => {
    const isLegit = frame.status === "LEGITIMATE";
    const card = document.createElement("div");
    
    // >>> APPLY PROMINENT RED COLOR MARK TO LEGITIMATE FRAMES <<<
    card.className = `frame-card ${isLegit ? "is-legitimate" : "is-modified"}`;

    const badgeHtml = isLegit
      ? `<span class="badge-legitimate-red">🔴 LEGITIMATE</span>`
      : `<span class="badge-modified-dark">⚠️ MODIFIED</span>`;

    card.innerHTML = `
      <div class="frame-thumb-box">
        <img src="${frame.thumbnail_data}" alt="Frame ${frame.frame_index}" loading="lazy">
        ${badgeHtml}
        <span class="frame-time-pill">${frame.timestamp_str}</span>
      </div>
      <div class="frame-info-bar">
        <span class="frame-num-label">Frame #${String(frame.frame_index).padStart(2, '0')}</span>
        <span class="frame-sec-label">Sec ${frame.second_idx + 1} (${frame.sub_second_frame}/24)</span>
      </div>
    `;

    card.addEventListener("click", () => openFrameModal(frame));
    grid.appendChild(card);
  });
}

// 7. Filter Controls
function setupFilterControls() {
  const btnAll = document.getElementById("filterAllBtn");
  const btnLegit = document.getElementById("filterLegitBtn");
  const btnMod = document.getElementById("filterModBtn");

  [btnAll, btnLegit, btnMod].forEach(btn => {
    btn.addEventListener("click", () => {
      [btnAll, btnLegit, btnMod].forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.getAttribute("data-filter");
      renderFramesGrid(currentFramesData);
    });
  });
}

// 8. Lightbox Modal
function setupFrameModal() {
  const modal = document.getElementById("frameModal");
  const closeBtn = document.getElementById("closeModalBtn");

  closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
}

function openFrameModal(frame) {
  const modal = document.getElementById("frameModal");
  const badge = document.getElementById("modalFrameBadge");
  const num = document.getElementById("modalFrameNumber");
  const ts = document.getElementById("modalTimestamp");
  const img = document.getElementById("modalFrameImg");
  const stamp = document.getElementById("modalRedStamp");

  const isLegit = frame.status === "LEGITIMATE";
  badge.textContent = isLegit ? "🔴 LEGITIMATE FRAME" : "⚠️ MODIFIED / SYNTHETIC";
  badge.style.background = isLegit ? "#ff2a2a" : "#f59e0b";

  num.textContent = `Frame #${String(frame.frame_index).padStart(2, '0')} (Sub-frame ${frame.sub_second_frame}/24)`;
  ts.textContent = `${frame.timestamp_str} (${frame.timestamp_sec}s)`;
  img.src = frame.thumbnail_data;

  // Red stamp indicator
  if (isLegit) {
    stamp.classList.remove("hidden");
    stamp.innerHTML = "<span>🔴 LEGITIMATE AUTHENTIC FRAME</span>";
    stamp.style.background = "rgba(255, 42, 42, 0.95)";
  } else {
    stamp.classList.remove("hidden");
    stamp.innerHTML = "<span>⚠️ MODIFIED SYNTHETIC FRAME DETECTED</span>";
    stamp.style.background = "rgba(245, 158, 11, 0.95)";
  }

  modal.classList.remove("hidden");
}

// 9. Telemetry Stats
async function loadStats() {
  try {
    const res = await fetch("/api/stats", {
      headers: { "X-API-Key": getAdminKey() }
    });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("statTotal").textContent = data.total_scanned || 0;
    document.getElementById("statAllowed").textContent = data.total_allowed || 0;
    document.getElementById("statReview").textContent = data.total_reviewed || 0;
    document.getElementById("statBlocked").textContent = data.total_blocked || 0;
    document.getElementById("reviewQueueCount").textContent = data.total_reviewed || 0;
  } catch (e) {
    console.debug("Telemetry refresh skipped:", e);
  }
}

// 10. Quarantine Review Queue
function setupReviewQueue() {
  const btn = document.getElementById("refreshReviewBtn");
  if (btn) btn.addEventListener("click", loadReviewQueue);
}

async function loadReviewQueue() {
  const list = document.getElementById("reviewQueueList");
  try {
    const res = await fetch("/api/review-queue", {
      headers: { "X-API-Key": getAdminKey() }
    });
    if (!res.ok) return;
    const items = await res.json();

    if (!items || items.length === 0) {
      list.innerHTML = "<div class='empty-state'>✓ Quarantine queue is clean. Zero pending videos.</div>";
      return;
    }

    list.innerHTML = "";
    items.forEach(item => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.marginBottom = "14px";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong>${item.original_filename}</strong> (${(item.file_size / 1024).toFixed(1)} KB)
            <div style="font-size:0.8rem; color:#94a3b8; margin-top:4px;">${item.explanation || "Deepfake heuristic advisory"}</div>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-demo-clean" onclick="handleApprove('${item.id}')">Approve</button>
            <button class="btn btn-demo-deepfake" onclick="handleReject('${item.id}')">Reject &amp; Destroy</button>
          </div>
        </div>
      `;
      list.appendChild(card);
    });
  } catch (e) {
    console.debug("Queue error:", e);
  }
}

window.handleApprove = async function(id) {
  try {
    await fetch(`/api/review/${id}/approve`, {
      method: "POST",
      headers: { "X-API-Key": getAdminKey() }
    });
    loadReviewQueue();
    loadStats();
  } catch (e) { alert(e.message); }
};

window.handleReject = async function(id) {
  try {
    await fetch(`/api/review/${id}/reject`, {
      method: "POST",
      headers: { "X-API-Key": getAdminKey() }
    });
    loadReviewQueue();
    loadStats();
  } catch (e) { alert(e.message); }
};

// 11. Decisions History
function setupDecisions() {
  const btn = document.getElementById("refreshDecisionsBtn");
  if (btn) btn.addEventListener("click", loadDecisions);
}

async function loadDecisions() {
  const tbody = document.getElementById("decisionsTableBody");
  try {
    const res = await fetch("/api/decisions?limit=10", {
      headers: { "X-API-Key": getAdminKey() }
    });
    if (!res.ok) return;
    const items = await res.json();

    if (!items || items.length === 0) {
      tbody.innerHTML = "<tr><td colspan='6' class='text-center'>No records found.</td></tr>";
      return;
    }

    tbody.innerHTML = items.map(d => `
      <tr>
        <td style="font-family:monospace;">${d.id.substring(0, 8)}...</td>
        <td>${d.original_filename}</td>
        <td style="font-family:monospace;">${d.sha256_hash ? d.sha256_hash.substring(0, 16) + '...' : '-'}</td>
        <td>${d.deepfake_risk_score !== null ? d.deepfake_risk_score + '/100' : '0/100'}</td>
        <td><strong style="color:${d.verdict === 'ALLOW' ? '#10b981' : (d.verdict === 'REVIEW' ? '#f59e0b' : '#ef4444')}">${d.verdict}</strong></td>
        <td>${new Date(d.created_at).toLocaleString()}</td>
      </tr>
    `).join("");
  } catch (e) { console.debug("Decisions load error:", e); }
}

// 12. Audit Verification
function setupAuditVerification() {
  const btn = document.getElementById("verifyAuditBtn");
  if (btn) btn.addEventListener("click", verifyAuditChain);
}

async function verifyAuditChain() {
  const banner = document.getElementById("auditStatusBanner");
  const icon = document.getElementById("auditBannerIcon");
  const text = document.getElementById("auditBannerText");

  try {
    const res = await fetch("/api/audit/verify", {
      headers: { "X-API-Key": getAdminKey() }
    });
    if (!res.ok) throw new Error("Audit verification failed");
    const data = await res.json();

    if (data.valid) {
      banner.style.borderColor = "#10b981";
      banner.style.color = "#10b981";
      icon.textContent = "✓";
      text.textContent = `AUDIT INTEGRITY: VALID — All ${data.total_entries} records cryptographically intact (0 broken links).`;
    } else {
      banner.style.borderColor = "#ef4444";
      banner.style.color = "#ef4444";
      icon.textContent = "⚠";
      text.textContent = `AUDIT COMPROMISED at row ${data.broken_at || 'unknown'}!`;
    }
  } catch (e) {
    alert("Audit error: " + e.message);
  }
}

async function loadAuditLogs() {
  const tbody = document.getElementById("auditTableBody");
  try {
    const res = await fetch("/api/audit/log?limit=10", {
      headers: { "X-API-Key": getAdminKey() }
    });
    if (!res.ok) return;
    const items = await res.json();

    tbody.innerHTML = items.map(l => `
      <tr>
        <td>#${l.id}</td>
        <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
        <td><code>${l.action}</code></td>
        <td style="font-family:monospace;">${l.current_hash ? l.current_hash.substring(0, 16) + '...' : '-'}</td>
        <td style="font-family:monospace;">${l.previous_hash ? l.previous_hash.substring(0, 16) + '...' : 'GENESIS'}</td>
      </tr>
    `).join("");
  } catch (e) { console.debug("Audit load error:", e); }
}
