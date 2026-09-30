const searchesCount = document.querySelector("#searchesCount");
const usefulCount = document.querySelector("#usefulCount");
const notUsefulCount = document.querySelector("#notUsefulCount");
const standardsCount = document.querySelector("#standardsCount");
const needsVerification = document.querySelector("#needsVerification");
const genericSources = document.querySelector("#genericSources");
const historyRows = document.querySelector("#historyRows");
const feedbackRows = document.querySelector("#feedbackRows");
const categoryBars = document.querySelector("#categoryBars");
const refreshButton = document.querySelector("#refreshButton");
const acceptedCount = document.querySelector("#acceptedCount");
const rejectedCount = document.querySelector("#rejectedCount");
const pendingCount = document.querySelector("#pendingCount");
const reviewRows = document.querySelector("#reviewRows");
const currentUserLabel = document.querySelector("#currentUser");
const logoutButton = document.querySelector("#logoutButton");
const verificationWorkspace = document.querySelector("#verificationWorkspace");
const verificationHistoryPanel = document.querySelector("#verificationHistoryPanel");
const verificationRows = document.querySelector("#verificationRows");
const verificationHistoryRows = document.querySelector("#verificationHistoryRows");
const verificationQuery = document.querySelector("#verificationQuery");
const verificationStatus = document.querySelector("#verificationStatus");
const filterVerification = document.querySelector("#filterVerification");
const verificationDialog = document.querySelector("#verificationDialog");
const verificationForm = document.querySelector("#verificationForm");
const closeVerification = document.querySelector("#closeVerification");
const verificationSaveStatus = document.querySelector("#verificationSaveStatus");
const top1Accuracy = document.querySelector("#top1Accuracy");
const top5Accuracy = document.querySelector("#top5Accuracy");
const mrrScore = document.querySelector("#mrrScore");
const qualityContext = document.querySelector("#qualityContext");
let currentUser = null;

async function loadCurrentUser() {
  const response = await fetch("/auth/me");
  if (!response.ok) {
    window.location.assign("/login");
    return;
  }
  currentUser = await response.json();
  currentUserLabel.textContent = `${currentUser.username} · ${currentUser.role}`;
  return currentUser;
}

async function logout() {
  await fetch("/auth/logout", { method: "POST" });
  window.location.assign("/login");
}

function row(cells, reportId = null) {
  const tr = document.createElement("tr");
  cells.forEach((value) => {
    const td = document.createElement("td");
    td.textContent = value;
    tr.append(td);
  });
  if (reportId !== null) {
    const td = document.createElement("td");
    const link = document.createElement("a");
    link.className = "table-link";
    link.href = `/reports/search/${reportId}.csv`;
    link.download = "";
    link.textContent = "CSV";
    td.append(link);
    tr.append(td);
  }
  return tr;
}

function emptyRow(message, colspan) {
  const tr = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = colspan;
  td.textContent = message;
  td.className = "muted-cell";
  tr.append(td);
  return tr;
}

async function loadAdminData() {
  const [analyticsResponse, historyResponse, qualityResponse, reviewSummaryResponse, reviewsResponse, retrievalResponse] = await Promise.all([
    fetch("/analytics"),
    fetch("/search-history?limit=12"),
    fetch("/dataset-quality"),
    fetch("/review-summary"),
    fetch("/reviews?limit=12"),
    fetch("/retrieval-quality"),
  ]);

  const analytics = await analyticsResponse.json();
  const history = await historyResponse.json();
  const quality = await qualityResponse.json();
  const reviewSummary = await reviewSummaryResponse.json();
  const reviews = await reviewsResponse.json();
  const retrieval = await retrievalResponse.json();

  searchesCount.textContent = analytics.searches_count;
  usefulCount.textContent = analytics.feedback.useful || 0;
  notUsefulCount.textContent = analytics.feedback.not_useful || 0;

  standardsCount.textContent = quality.standards_count;
  needsVerification.textContent = quality.needs_verification_count;
  genericSources.textContent = quality.generic_source_url_count;
  acceptedCount.textContent = reviewSummary.accepted;
  rejectedCount.textContent = reviewSummary.rejected;
  pendingCount.textContent = reviewSummary.pending;
  top1Accuracy.textContent = `${(retrieval.top_1_accuracy * 100).toFixed(1)}%`;
  top5Accuracy.textContent = `${(retrieval.top_5_accuracy * 100).toFixed(1)}%`;
  mrrScore.textContent = retrieval.mean_reciprocal_rank.toFixed(3);
  qualityContext.textContent = `${retrieval.query_count} queries · ${retrieval.mode} mode · ${retrieval.evaluated_on}`;

  historyRows.replaceChildren();
  if (!history.length) {
    historyRows.append(emptyRow("No searches saved yet.", 6));
  } else {
    history.forEach((item) => {
      historyRows.append(
        row([
          item.id,
          item.source_type,
          item.mode,
          item.result_count,
          item.query.length > 90 ? `${item.query.slice(0, 90)}...` : item.query,
        ], item.id),
      );
    });
  }

  feedbackRows.replaceChildren();
  const feedback = analytics.top_feedback_standards || [];
  if (!feedback.length) {
    feedbackRows.append(emptyRow("No feedback submitted yet.", 4));
  } else {
    feedback.forEach((item) => {
      feedbackRows.append(row([item.standard_code, item.useful, item.not_useful, item.total]));
    });
  }

  categoryBars.replaceChildren();
  const maxCategoryCount = Math.max(...quality.top_categories.map((item) => item.count), 1);
  quality.top_categories.forEach((item) => {
    const wrapper = document.createElement("div");
    wrapper.className = "bar-item";
    wrapper.innerHTML = `
      <div class="bar-label"><span>${item.category}</span><strong>${item.count}</strong></div>
      <div class="bar-track"><span style="width: ${(item.count / maxCategoryCount) * 100}%"></span></div>
    `;
    categoryBars.append(wrapper);
  });

  reviewRows.replaceChildren();
  if (!reviews.length) {
    reviewRows.append(emptyRow("No review decisions saved yet.", 6));
  } else {
    reviews.forEach((item) => {
      reviewRows.append(
        row([
          item.search_id,
          item.standard_code,
          item.decision,
          item.reviewer_username || "Legacy",
          item.note || "-",
          item.source_name || item.source_type,
        ]),
      );
    });
  }
}

function verificationRow(item) {
  const tr = document.createElement("tr");
  [item.standard_code, item.title, item.verify_status.replaceAll("_", " "), item.last_reviewed].forEach((value) => {
    const td = document.createElement("td");
    td.textContent = value;
    tr.append(td);
  });

  const sourceCell = document.createElement("td");
  const sourceLink = document.createElement("a");
  sourceLink.className = "table-link";
  sourceLink.href = item.source_url;
  sourceLink.target = "_blank";
  sourceLink.rel = "noreferrer";
  sourceLink.textContent = "Open";
  sourceCell.append(sourceLink);
  tr.append(sourceCell);

  const actionCell = document.createElement("td");
  const editButton = document.createElement("button");
  editButton.className = "ghost-button compact";
  editButton.type = "button";
  editButton.textContent = "Review";
  editButton.addEventListener("click", () => openVerificationDialog(item));
  actionCell.append(editButton);
  tr.append(actionCell);
  return tr;
}

async function loadVerificationQueue() {
  const params = new URLSearchParams({ limit: "50" });
  if (verificationStatus.value) params.set("status", verificationStatus.value);
  if (verificationQuery.value.trim()) params.set("q", verificationQuery.value.trim());
  const response = await fetch(`/verification-queue?${params}`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "Could not load verification queue.");
  verificationRows.replaceChildren();
  if (!payload.length) {
    verificationRows.append(emptyRow("No standards match this filter.", 6));
    return;
  }
  payload.forEach((item) => verificationRows.append(verificationRow(item)));
}

async function loadVerificationHistory() {
  const response = await fetch("/verification-history?limit=20");
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "Could not load verification history.");
  verificationHistoryRows.replaceChildren();
  if (!payload.length) {
    verificationHistoryRows.append(emptyRow("No verification changes saved yet.", 5));
    return;
  }
  payload.forEach((item) => {
    verificationHistoryRows.append(
      row([
        new Date(item.created_at).toLocaleString(),
        item.standard_id,
        item.new_data.verify_status.replaceAll("_", " "),
        item.changed_by,
        item.note,
      ]),
    );
  });
}

function openVerificationDialog(item) {
  document.querySelector("#verificationId").value = item.id;
  document.querySelector("#verificationCode").textContent = item.standard_code;
  document.querySelector("#verificationTitle").value = item.title;
  document.querySelector("#verificationSource").value = item.source_url;
  document.querySelector("#verificationEditStatus").value = item.verify_status;
  document.querySelector("#verificationNote").value = item.verification_note || "";
  verificationSaveStatus.textContent = "";
  verificationDialog.showModal();
}

async function saveVerification(event) {
  event.preventDefault();
  const saveButton = document.querySelector("#saveVerification");
  saveButton.disabled = true;
  verificationSaveStatus.textContent = "Saving...";
  const standardId = document.querySelector("#verificationId").value;

  try {
    const response = await fetch(`/admin/standards/${encodeURIComponent(standardId)}/verification`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: document.querySelector("#verificationTitle").value.trim(),
        source_url: document.querySelector("#verificationSource").value.trim(),
        verify_status: document.querySelector("#verificationEditStatus").value,
        note: document.querySelector("#verificationNote").value.trim(),
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Could not save verification.");
    verificationDialog.close();
    await Promise.all([loadAdminData(), loadVerificationQueue(), loadVerificationHistory()]);
  } catch (error) {
    verificationSaveStatus.textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
}

async function initializeAdmin() {
  const user = await loadCurrentUser();
  await loadAdminData();
  if (user?.role === "admin") {
    verificationWorkspace.hidden = false;
    verificationHistoryPanel.hidden = false;
    await Promise.all([loadVerificationQueue(), loadVerificationHistory()]);
  }
}

refreshButton.addEventListener("click", async () => {
  await loadAdminData();
  if (currentUser?.role === "admin") {
    await Promise.all([loadVerificationQueue(), loadVerificationHistory()]);
  }
});
logoutButton.addEventListener("click", logout);
filterVerification.addEventListener("click", loadVerificationQueue);
verificationQuery.addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadVerificationQueue();
});
closeVerification.addEventListener("click", () => verificationDialog.close());
verificationForm.addEventListener("submit", saveVerification);
initializeAdmin().catch((error) => {
  historyRows.append(emptyRow(error.message, 6));
  reviewRows.append(emptyRow(error.message, 6));
});
