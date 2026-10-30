/**
 * SafeGate — Single-Page Dashboard Controller
 * ============================================
 * Pure Vanilla JavaScript (no framework overhead).
 * Connects directly to SafeGate's RESTful API:
 * - Real-time media intake screening
 * - Human-in-the-loop review queue moderation
 * - Historical decision records and user appeals
 * - Cryptographic audit hash chain verification
 * - Telemetry analytics and Chart.js timeline
 */

// Application State
let selectedFile = null;
let currentChart = null;
let pendingResolveAppealId = null;
let pendingResolveStatus = null;

// API Key configuration
const STORAGE_ADMIN_KEY = "safegate_admin_key";
const STORAGE_CLIENT_KEY = "safegate_client_key";

function getAdminKey() {
  return document.getElementById("adminKeyInput").value.trim();
}

function getClientKey() {
  return document.getElementById("clientKeyInput").value.trim();
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initApiKeys();
  setupTabNavigation();
  setupDropZone();
  setupUploadActions();
  setupReviewQueue();
  setupDecisions();
  setupAppeals();
  setupAuditVerification();

  // Initial data load
  loadStats();
  loadReviewQueue();
  loadDecisions();
  loadAppeals();
});

// 1. API Key Persistence
function initApiKeys() {
  const savedAdmin = localStorage.getItem(STORAGE_ADMIN_KEY);
  const savedClient = localStorage.getItem(STORAGE_CLIENT_KEY);

  if (savedAdmin) document.getElementById("adminKeyInput").value = savedAdmin;
  if (savedClient) document.getElementById("clientKeyInput").value = savedClient;

  document.getElementById("saveKeysBtn").addEventListener("click", () => {
    localStorage.setItem(STORAGE_ADMIN_KEY, getAdminKey());
    localStorage.setItem(STORAGE_CLIENT_KEY, getClientKey());
    alert("API keys saved in browser local storage.");
    loadStats();
    loadReviewQueue();
    loadDecisions();
  });
}

// 2. Tab Navigation
function setupTabNavigation() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");

      // Auto-refresh data when switching tabs
      if (targetId === "tab-review") loadReviewQueue();
      if (targetId === "tab-decisions") loadDecisions();
      if (targetId === "tab-appeals") loadAppeals();
      if (targetId === "tab-audit") loadStats();
    });
  });
}

// 3. Drag-and-Drop Intake Box
function setupDropZone() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const fileInfo = document.getElementById("fileSelectedInfo");
  const uploadBtn = document.getElementById("uploadBtn");
  const clearBtn = document.getElementById("clearBtn");

  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
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

  clearBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    fileInfo.classList.add("hidden");
    fileInfo.textContent = "";
    uploadBtn.disabled = true;
    document.getElementById("verdictResult").classList.add("hidden");
    document.getElementById("verdictPlaceholder").classList.remove("hidden");
  });

  function handleFileSelected(file) {
    selectedFile = file;
    const mb = (file.size / (1024 * 1024)).toFixed(2);
    fileInfo.textContent = `Selected: ${file.name} (${mb} MB)`;
    fileInfo.classList.remove("hidden");
    uploadBtn.disabled = false;
  }
}

// 4. Video Upload & Live Screening Action
function setupUploadActions() {
  const uploadBtn = document.getElementById("uploadBtn");
  const progressBar = document.getElementById("uploadProgress");
  const verdictResult = document.getElementById("verdictResult");
  const verdictPlaceholder = document.getElementById("verdictPlaceholder");

  uploadBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    uploadBtn.disabled = true;
    progressBar.classList.remove("hidden");
    verdictPlaceholder.classList.add("hidden");
    verdictResult.classList.add("hidden");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        headers: {
          "X-API-Key": getClientKey(),
        },
        body: formData,
      });

      const data = await response.json();
      progressBar.classList.add("hidden");
      uploadBtn.disabled = false;

      if (!response.ok) {
        alert(`Screening error: ${data.detail || "Request failed"}`);
        verdictPlaceholder.classList.remove("hidden");
        return;
      }

      displayVerdict(data);
      loadStats();
      loadReviewQueue();
      loadDecisions();
    } catch (err) {
      progressBar.classList.add("hidden");
      uploadBtn.disabled = false;
      alert(`Network or server error: ${err.message}`);
      verdictPlaceholder.classList.remove("hidden");
    }
  });

  document.getElementById("appealFromVerdictBtn").addEventListener("click", () => {
    const uploadId = document.getElementById("verdictUploadId").textContent;
    openAppealModal(uploadId);
  });
}

function displayVerdict(data) {
  const verdictResult = document.getElementById("verdictResult");
  const verdictBadge = document.getElementById("verdictBadge");
  const verdictDuration = document.getElementById("verdictDuration");
  const verdictUploadId = document.getElementById("verdictUploadId");
  const verdictExplanation = document.getElementById("verdictExplanation");
  const verdictNsfw = document.getElementById("verdictNsfw");
  const verdictDeepfake = document.getElementById("verdictDeepfake");

  const v = (data.verdict || "REVIEW").toUpperCase();
  verdictBadge.textContent = v;
  verdictBadge.className = `verdict-badge ${v.toLowerCase()}`;

  verdictDuration.textContent = `${(data.scan_duration_sec || 0).toFixed(2)}s`;
  verdictUploadId.textContent = data.upload_id;
  verdictExplanation.textContent = data.explanation || "No explanation recorded.";

  verdictNsfw.textContent = data.nsfw_worst_score !== null && data.nsfw_worst_score !== undefined
    ? `${(data.nsfw_worst_score * 100).toFixed(1)}%`
    : "N/A";

  verdictDeepfake.textContent = data.deepfake_risk_score !== null && data.deepfake_risk_score !== undefined
    ? `${data.deepfake_risk_score}/100`
    : "N/A";

  verdictResult.classList.remove("hidden");
}

// 5. Statistics & Verdict Timeline Chart
async function loadStats() {
  try {
    const response = await fetch("/api/stats", {
      headers: { "X-API-Key": getAdminKey() },
    });
    if (!response.ok) return;

    const stats = await response.json();
    document.getElementById("statTotal").textContent = stats.total_scanned;
    document.getElementById("statAllowed").textContent = stats.total_allowed;
    document.getElementById("statReview").textContent = stats.total_reviewed;
    document.getElementById("statBlocked").textContent = stats.total_blocked;
    document.getElementById("statAvgTime").textContent = `${stats.avg_scan_time_sec}s`;

    renderTimelineChart(stats.verdicts_over_time || []);
  } catch (err) {
    console.warn("Failed to load statistics:", err);
  }
}

function renderTimelineChart(timeline) {
  const canvas = document.getElementById("verdictTimelineChart");
  if (!canvas || typeof Chart === "undefined") return;

  const labels = timeline.map(t => t.date);
  const allowData = timeline.map(t => t.ALLOW || 0);
  const reviewData = timeline.map(t => t.REVIEW || 0);
  const blockData = timeline.map(t => t.BLOCK || 0);

  if (currentChart) {
    currentChart.destroy();
  }

  currentChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels.length > 0 ? labels : ["Today"],
      datasets: [
        {
          label: "Allowed",
          data: labels.length > 0 ? allowData : [0],
          backgroundColor: "rgba(16, 185, 129, 0.7)",
          borderColor: "#10b981",
          borderWidth: 1,
        },
        {
          label: "In Review",
          data: labels.length > 0 ? reviewData : [0],
          backgroundColor: "rgba(245, 158, 11, 0.7)",
          borderColor: "#f59e0b",
          borderWidth: 1,
        },
        {
          label: "Blocked",
          data: labels.length > 0 ? blockData : [0],
          backgroundColor: "rgba(239, 68, 68, 0.7)",
          borderColor: "#ef4444",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          stacked: true,
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8" },
        },
        y: {
          stacked: true,
          beginAtZero: true,
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", precision: 0 },
        },
      },
      plugins: {
        legend: { labels: { color: "#e2e8f0" } },
      },
    },
  });
}

// 6. Review Queue Management
function setupReviewQueue() {
  document.getElementById("refreshReviewBtn").addEventListener("click", loadReviewQueue);
}

async function loadReviewQueue() {
  const tbody = document.getElementById("reviewTableBody");
  const countBadge = document.getElementById("reviewQueueCount");

  try {
    const response = await fetch("/api/review-queue", {
      headers: { "X-API-Key": getAdminKey() },
    });
    if (!response.ok) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center">Auth required or error loading queue.</td></tr>`;
      return;
    }

    const items = await response.json();
    countBadge.textContent = items.length;

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center">Review queue is empty. No uploads pending moderation.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map(item => `
      <tr>
        <td class="mono">${item.id.slice(0, 8)}...</td>
        <td><strong>${escapeHtml(item.original_filename)}</strong></td>
        <td>${(item.file_size / (1024 * 1024)).toFixed(2)} MB</td>
        <td>${item.nsfw_worst_score !== null ? (item.nsfw_worst_score * 100).toFixed(1) + "%" : "-"}</td>
        <td>${item.deepfake_risk_score !== null ? item.deepfake_risk_score + "/100" : "-"}</td>
        <td><small>${escapeHtml(item.explanation || "")}</small></td>
        <td><small>${formatDate(item.created_at)}</small></td>
        <td>
          <button class="btn btn-sm btn-success" onclick="approveReview('${item.id}')">Approve</button>
          <button class="btn btn-sm btn-danger" onclick="rejectReview('${item.id}')">Reject</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center">Failed to load review queue: ${err.message}</td></tr>`;
  }
}

async function approveReview(uploadId) {
  const note = prompt("Moderator rationale for approval (optional):", "Approved after review");
  if (note === null) return;

  try {
    const response = await fetch(`/api/review/${uploadId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": getAdminKey(),
      },
      body: JSON.stringify({ note: note }),
    });

    if (response.ok) {
      alert("Upload approved and moved to published/.");
      loadReviewQueue();
      loadStats();
      loadDecisions();
    } else {
      const err = await response.json();
      alert(`Approval error: ${err.detail || "Action failed"}`);
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

async function rejectReview(uploadId) {
  const note = prompt("Moderator rationale for rejection (file will be deleted & fingerprints blocklisted):", "Violates content policy");
  if (note === null) return;

  try {
    const response = await fetch(`/api/review/${uploadId}/reject`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": getAdminKey(),
      },
      body: JSON.stringify({ note: note }),
    });

    if (response.ok) {
      alert("Upload rejected, deleted from storage, and hashes added to blocklist.");
      loadReviewQueue();
      loadStats();
      loadDecisions();
    } else {
      const err = await response.json();
      alert(`Rejection error: ${err.detail || "Action failed"}`);
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// 7. Decision Records
function setupDecisions() {
  document.getElementById("refreshDecisionsBtn").addEventListener("click", loadDecisions);
  document.getElementById("verdictFilter").addEventListener("change", loadDecisions);
}

async function loadDecisions() {
  const tbody = document.getElementById("decisionsTableBody");
  const verdictFilter = document.getElementById("verdictFilter").value;
  const url = verdictFilter ? `/api/decisions?verdict=${verdictFilter}` : "/api/decisions";

  try {
    const response = await fetch(url, {
      headers: { "X-API-Key": getAdminKey() },
    });
    if (!response.ok) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center">Auth required or error loading decisions.</td></tr>`;
      return;
    }

    const records = await response.json();
    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center">No decision records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(r => `
      <tr>
        <td class="mono" title="${r.id}">${r.id.slice(0, 8)}...</td>
        <td>${escapeHtml(r.original_filename)}</td>
        <td>${(r.file_size / (1024 * 1024)).toFixed(2)} MB</td>
        <td><span class="pill pill-${(r.verdict || 'review').toLowerCase()}">${r.verdict}</span></td>
        <td><small>${escapeHtml(r.explanation || "")}</small></td>
        <td>${r.nsfw_worst_score !== null ? (r.nsfw_worst_score * 100).toFixed(1) + "%" : "-"}</td>
        <td>${r.deepfake_risk_score !== null ? r.deepfake_risk_score + "/100" : "-"}</td>
        <td>${r.scan_duration_sec ? r.scan_duration_sec.toFixed(2) + "s" : "-"}</td>
        <td><small>${formatDate(r.created_at)}</small></td>
        <td>
          <button class="btn btn-sm btn-outline" onclick="openAppealModal('${r.id}')">Appeal</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center">Failed to load decisions: ${err.message}</td></tr>`;
  }
}

// 8. Appeals & Dispute Resolution
function setupAppeals() {
  document.getElementById("refreshAppealsBtn").addEventListener("click", loadAppeals);
  document.getElementById("appealFilter").addEventListener("change", loadAppeals);

  // Appeal Modal bindings
  document.getElementById("closeAppealModalBtn").addEventListener("click", closeAppealModal);
  document.getElementById("cancelAppealBtn").addEventListener("click", closeAppealModal);
  document.getElementById("submitAppealBtn").addEventListener("click", submitAppeal);

  // Resolve Modal bindings
  document.getElementById("closeResolveModalBtn").addEventListener("click", closeResolveModal);
  document.getElementById("cancelResolveBtn").addEventListener("click", closeResolveModal);
  document.getElementById("confirmResolveBtn").addEventListener("click", confirmResolveAppeal);
}

async function loadAppeals() {
  const tbody = document.getElementById("appealsTableBody");
  const filter = document.getElementById("appealFilter").value;
  const countBadge = document.getElementById("appealsCount");
  const url = filter ? `/api/appeals?status=${filter}` : "/api/appeals";

  try {
    const response = await fetch(url, {
      headers: { "X-API-Key": getAdminKey() },
    });
    if (!response.ok) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">Auth required or error loading appeals.</td></tr>`;
      return;
    }

    const appeals = await response.json();
    countBadge.textContent = appeals.length;

    if (appeals.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">No appeals found for current filter.</td></tr>`;
      return;
    }

    tbody.innerHTML = appeals.map(a => `
      <tr>
        <td class="mono">#${a.id}</td>
        <td class="mono" title="${a.upload_id}">${a.upload_id.slice(0, 8)}...</td>
        <td>${escapeHtml(a.reason)}</td>
        <td><span class="pill pill-${a.status === 'approved' ? 'allow' : a.status === 'rejected' ? 'block' : 'review'}">${a.status}</span></td>
        <td><small>${escapeHtml(a.moderator_note || "-")}</small></td>
        <td><small>${formatDate(a.created_at)}</small></td>
        <td>
          ${a.status === 'pending' ? `
            <button class="btn btn-sm btn-success" onclick="openResolveModal(${a.id}, 'approved')">Approve</button>
            <button class="btn btn-sm btn-danger" onclick="openResolveModal(${a.id}, 'rejected')">Reject</button>
          ` : `<small class="text-dim">Resolved</small>`}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center">Failed to load appeals: ${err.message}</td></tr>`;
  }
}

function openAppealModal(uploadId) {
  document.getElementById("appealUploadIdInput").value = uploadId;
  document.getElementById("appealReasonInput").value = "";
  document.getElementById("appealModal").classList.remove("hidden");
}

function closeAppealModal() {
  document.getElementById("appealModal").classList.add("hidden");
}

async function submitAppeal() {
  const uploadId = document.getElementById("appealUploadIdInput").value;
  const reason = document.getElementById("appealReasonInput").value.trim();

  if (reason.length < 10) {
    alert("Please provide at least 10 characters explaining your appeal reason.");
    return;
  }

  try {
    const response = await fetch("/api/appeal", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": getClientKey(),
      },
      body: JSON.stringify({ upload_id: uploadId, reason: reason }),
    });

    if (response.ok) {
      alert("Appeal successfully submitted for moderator review.");
      closeAppealModal();
      loadAppeals();
    } else {
      const err = await response.json();
      alert(`Appeal submission error: ${err.detail || "Action failed"}`);
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

function openResolveModal(appealId, status) {
  pendingResolveAppealId = appealId;
  pendingResolveStatus = status;

  document.getElementById("resolveModalTitle").textContent = `${status.toUpperCase()} Appeal #${appealId}`;
  document.getElementById("resolveAppealPrompt").textContent = `Confirm resolution to ${status.toUpperCase()} this appeal?`;
  document.getElementById("resolveNoteInput").value = status === "approved" ? "Appeal upheld upon moderator inspection" : "Appeal rejected: violation confirmed";
  document.getElementById("resolveModal").classList.remove("hidden");
}

function closeResolveModal() {
  pendingResolveAppealId = null;
  pendingResolveStatus = null;
  document.getElementById("resolveModal").classList.add("hidden");
}

async function confirmResolveAppeal() {
  if (!pendingResolveAppealId || !pendingResolveStatus) return;

  const note = document.getElementById("resolveNoteInput").value.trim();

  try {
    const response = await fetch(`/api/appeal/${pendingResolveAppealId}/resolve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": getAdminKey(),
      },
      body: JSON.stringify({
        status: pendingResolveStatus,
        moderator_note: note,
      }),
    });

    if (response.ok) {
      alert(`Appeal #${pendingResolveAppealId} marked as ${pendingResolveStatus}.`);
      closeResolveModal();
      loadAppeals();
    } else {
      const err = await response.json();
      alert(`Resolution error: ${err.detail || "Action failed"}`);
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// 9. Cryptographic Audit Chain Verification
function setupAuditVerification() {
  const verifyBtn = document.getElementById("verifyAuditBtn");
  const statusBadge = document.getElementById("auditVerifyStatus");
  const detailsBox = document.getElementById("auditDetails");

  verifyBtn.addEventListener("click", async () => {
    verifyBtn.disabled = true;
    statusBadge.classList.remove("hidden");
    statusBadge.textContent = "Verifying SHA-256 chain...";
    statusBadge.className = "audit-status-badge";

    try {
      const response = await fetch("/api/audit/verify", {
        headers: { "X-API-Key": getAdminKey() },
      });

      const res = await response.json();
      verifyBtn.disabled = false;

      if (!response.ok) {
        statusBadge.textContent = "Verification Error";
        statusBadge.className = "audit-status-badge invalid";
        alert(`Verification failed: ${res.detail || "Authentication required"}`);
        return;
      }

      if (res.valid) {
        statusBadge.textContent = "✓ Chain Intact & Valid";
        statusBadge.className = "audit-status-badge valid";
      } else {
        statusBadge.textContent = "⚠ Hash Chain Compromised";
        statusBadge.className = "audit-status-badge invalid";
      }

      document.getElementById("auditResultText").textContent = res.valid ? "VALID (No tampering detected)" : "TAMPERED / CORRUPTED";
      document.getElementById("auditTotalEntries").textContent = res.total_entries;
      document.getElementById("auditBrokenAt").textContent = res.broken_at !== null ? `Row #${res.broken_at}` : "None";
      document.getElementById("auditMessage").textContent = res.message;
      detailsBox.classList.remove("hidden");
    } catch (err) {
      verifyBtn.disabled = false;
      statusBadge.textContent = "Network Error";
      statusBadge.className = "audit-status-badge invalid";
      alert(`Audit verification request failed: ${err.message}`);
    }
  });
}

// Helper Utilities
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(isoString) {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    return d.toLocaleString();
  } catch {
    return isoString;
  }
}
