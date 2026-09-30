const queryInput = document.querySelector("#queryInput");
const limitSelect = document.querySelector("#limitSelect");
const modeSelect = document.querySelector("#modeSelect");
const recommendButton = document.querySelector("#recommendButton");
const clearButton = document.querySelector("#clearButton");
const documentInput = document.querySelector("#documentInput");
const extractButton = document.querySelector("#extractButton");
const recommendFileButton = document.querySelector("#recommendFileButton");
const uploadStatus = document.querySelector("#uploadStatus");
const resultsList = document.querySelector("#resultsList");
const resultSummary = document.querySelector("#resultSummary");
const emptyState = document.querySelector("#emptyState");
const resultTemplate = document.querySelector("#resultTemplate");
const apiStatus = document.querySelector("#apiStatus");
const downloadReport = document.querySelector("#downloadReport");
const downloadPdfReport = document.querySelector("#downloadPdfReport");
const reportActions = document.querySelector("#reportActions");
const resultFilters = document.querySelector("#resultFilters");
const resultFilter = document.querySelector("#resultFilter");
const confidenceFilter = document.querySelector("#confidenceFilter");
const currentUserLabel = document.querySelector("#currentUser");
const adminLink = document.querySelector("#adminLink");
const logoutButton = document.querySelector("#logoutButton");
const workspaceTabs = document.querySelectorAll(".workspace-tab");
const workspaceViews = document.querySelectorAll("[data-view-panel]");
const historyTab = document.querySelector("#historyTab");
const catalogQuery = document.querySelector("#catalogQuery");
const catalogCategory = document.querySelector("#catalogCategory");
const catalogGrid = document.querySelector("#catalogGrid");
const catalogCount = document.querySelector("#catalogCount");
const catalogEmpty = document.querySelector("#catalogEmpty");
const historyList = document.querySelector("#historyList");
const historyEmpty = document.querySelector("#historyEmpty");
const refreshHistory = document.querySelector("#refreshHistory");
const compareBar = document.querySelector("#compareBar");
const compareCount = document.querySelector("#compareCount");
const compareButton = document.querySelector("#compareButton");
const comparisonDialog = document.querySelector("#comparisonDialog");
const comparisonTable = document.querySelector("#comparisonTable");
const closeComparison = document.querySelector("#closeComparison");
let currentSearchId = null;
let currentUser = null;
let standardsCatalog = [];
let currentResultQuery = "";
const selectedStandards = new Set();

async function loadCurrentUser() {
  const response = await fetch("/auth/me");
  if (!response.ok) {
    window.location.assign("/login");
    return;
  }
  currentUser = await response.json();
  currentUserLabel.textContent = `${currentUser.username} · ${currentUser.role}`;
  adminLink.hidden = currentUser.role === "procurement";
  historyTab.hidden = currentUser.role === "procurement";
  return currentUser;
}

async function logout() {
  await fetch("/auth/logout", { method: "POST" });
  window.location.assign("/login");
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Health check failed");
    const payload = await response.json();
    apiStatus.classList.remove("offline");
    apiStatus.classList.add("online");
    apiStatus.lastChild.textContent = ` API online · ${payload.standards_count} standards`;
  } catch {
    apiStatus.classList.remove("online");
    apiStatus.classList.add("offline");
    apiStatus.lastChild.textContent = " API offline";
  }
}

function setLoading(isLoading) {
  recommendButton.disabled = isLoading;
  extractButton.disabled = isLoading;
  recommendFileButton.disabled = isLoading;
  recommendButton.lastChild.textContent = isLoading ? " Searching" : " Recommend Standards";
}

function clearResults(message = "No query submitted yet.") {
  resultsList.replaceChildren();
  resultSummary.textContent = message;
  emptyState.hidden = false;
  currentSearchId = null;
  currentResultQuery = "";
  reportActions.hidden = true;
  resultFilters.hidden = true;
  resultFilter.value = "";
  confidenceFilter.value = "";
  downloadReport.removeAttribute("href");
  downloadPdfReport.removeAttribute("href");
}

function makeTag(text) {
  const tag = document.createElement("span");
  tag.className = "tag";
  tag.textContent = text;
  return tag;
}

function showView(viewName) {
  workspaceTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === viewName);
    tab.setAttribute("aria-current", tab.dataset.view === viewName ? "page" : "false");
  });
  workspaceViews.forEach((view) => {
    const active = view.dataset.viewPanel === viewName;
    view.hidden = !active;
    view.classList.toggle("active", active);
  });
}

function verificationLabel(status) {
  return status.replaceAll("_", " ");
}

function renderCatalog() {
  const query = catalogQuery.value.trim().toLowerCase();
  const category = catalogCategory.value;
  const filtered = standardsCatalog.filter((standard) => {
    const matchesCategory = !category || standard.category === category;
    const searchable = `${standard.standard_code} ${standard.title} ${standard.keywords.join(" ")} ${standard.scope_summary}`.toLowerCase();
    return matchesCategory && (!query || searchable.includes(query));
  });

  catalogGrid.replaceChildren();
  catalogEmpty.hidden = filtered.length > 0;
  catalogCount.textContent = `${filtered.length} of ${standardsCatalog.length} standards`;

  filtered.forEach((standard) => {
    const card = document.createElement("article");
    card.className = "catalog-card";

    const heading = document.createElement("div");
    heading.className = "catalog-card-heading";
    const code = document.createElement("strong");
    code.textContent = standard.standard_code;
    const status = document.createElement("span");
    status.className = `verification-badge ${standard.verify_status}`;
    status.textContent = verificationLabel(standard.verify_status);
    heading.append(code, status);

    const title = document.createElement("h3");
    title.textContent = standard.title;
    const categoryLine = document.createElement("p");
    categoryLine.className = "catalog-category";
    categoryLine.textContent = `${standard.category} / ${standard.subcategory}`;
    const scope = document.createElement("p");
    scope.className = "catalog-scope";
    scope.textContent = standard.scope_summary;
    const source = document.createElement("a");
    source.className = "source-link";
    source.href = standard.source_url;
    source.target = "_blank";
    source.rel = "noreferrer";
    source.textContent = "Open source reference";
    const compare = document.createElement("button");
    compare.className = "ghost-button compact compare-toggle";
    compare.type = "button";
    compare.dataset.standardId = standard.id;
    compare.textContent = "Compare";
    compare.addEventListener("click", () => {
      if (selectedStandards.has(standard.id)) {
        selectedStandards.delete(standard.id);
      } else if (selectedStandards.size < 3) {
        selectedStandards.add(standard.id);
      }
      updateCompareBar();
    });
    const actions = document.createElement("div");
    actions.className = "catalog-actions";
    actions.append(source, compare);
    card.append(heading, title, categoryLine, scope, actions);
    catalogGrid.append(card);
  });
  updateCompareBar();
}

function updateCompareBar() {
  const count = selectedStandards.size;
  compareBar.hidden = count === 0;
  compareCount.textContent = `${count} standard${count === 1 ? "" : "s"} selected`;
  compareButton.disabled = count < 2;
  document.querySelectorAll(".compare-toggle").forEach((button) => {
    const selected = selectedStandards.has(button.dataset.standardId);
    button.classList.toggle("selected", selected);
    button.textContent = selected ? "Remove" : "Compare";
    button.disabled = !selected && count >= 3;
  });
}

function comparisonRow(label, standards, field, link = false) {
  const row = document.createElement("tr");
  const heading = document.createElement("th");
  heading.scope = "row";
  heading.textContent = label;
  row.append(heading);
  standards.forEach((standard) => {
    const cell = document.createElement("td");
    if (link) {
      const anchor = document.createElement("a");
      anchor.className = "source-link";
      anchor.href = standard[field];
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      anchor.textContent = "Open reference";
      cell.append(anchor);
    } else {
      cell.textContent = typeof field === "function" ? field(standard) : standard[field];
    }
    row.append(cell);
  });
  return row;
}

function showComparison() {
  const standards = [...selectedStandards]
    .map((id) => standardsCatalog.find((standard) => standard.id === id))
    .filter(Boolean);
  if (standards.length < 2) return;
  comparisonTable.replaceChildren();
  const body = document.createElement("tbody");
  body.append(
    comparisonRow("Standard", standards, "standard_code"),
    comparisonRow("Title", standards, "title"),
    comparisonRow("Category", standards, (standard) => `${standard.category} / ${standard.subcategory}`),
    comparisonRow("Scope", standards, "scope_summary"),
    comparisonRow("Applicability", standards, "mandatory_hint"),
    comparisonRow("Verification", standards, (standard) => verificationLabel(standard.verify_status)),
    comparisonRow("Source", standards, "source_url", true),
  );
  comparisonTable.append(body);
  comparisonDialog.showModal();
}

async function loadCatalog() {
  const response = await fetch("/standards?limit=250");
  if (!response.ok) throw new Error("Could not load the standards library.");
  standardsCatalog = await response.json();
  const categories = [...new Set(standardsCatalog.map((standard) => standard.category))].sort();
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    catalogCategory.append(option);
  });
  renderCatalog();
}

async function openSavedRun(searchId) {
  const response = await fetch(`/search-history/${searchId}`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "Could not open the saved run.");
  queryInput.value = payload.source_type === "text" ? payload.query : "";
  modeSelect.value = payload.mode;
  renderResults(payload.source_name || payload.query, payload.results, payload.id);
  showView("search");
  document.querySelector("#resultsTitle").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadHistory() {
  const response = await fetch("/search-history?limit=20");
  if (!response.ok) throw new Error("Could not load recent runs.");
  const searches = await response.json();
  historyList.replaceChildren();
  historyEmpty.hidden = searches.length > 0;

  searches.forEach((search) => {
    const row = document.createElement("article");
    row.className = "history-item";
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = search.query.length > 120 ? `${search.query.slice(0, 120)}...` : search.query;
    const meta = document.createElement("span");
    meta.textContent = `${search.source_type} · ${search.mode} · ${search.result_count} results · ${new Date(search.created_at).toLocaleString()}`;
    content.append(title, meta);
    const button = document.createElement("button");
    button.className = "ghost-button compact";
    button.type = "button";
    button.textContent = "Open run";
    button.addEventListener("click", async () => {
      button.disabled = true;
      const originalLabel = button.textContent;
      button.textContent = "Opening...";
      try {
        await openSavedRun(search.id);
      } catch (error) {
        button.textContent = "Could not open";
        button.title = error.message;
        return;
      } finally {
        button.disabled = false;
      }
      button.textContent = originalLabel;
    });
    row.append(content, button);
    historyList.append(row);
  });
}

function renderResults(query, results, searchId = null) {
  resultsList.replaceChildren();
  currentSearchId = searchId;
  currentResultQuery = query;
  reportActions.hidden = !searchId;
  resultFilters.hidden = results.length === 0;
  resultFilter.value = "";
  confidenceFilter.value = "";
  if (searchId) {
    downloadReport.href = `/reports/search/${searchId}.csv`;
    downloadPdfReport.href = `/reports/search/${searchId}.pdf`;
  }
  emptyState.hidden = results.length > 0;
  resultSummary.textContent = `${results.length} result${results.length === 1 ? "" : "s"} for "${query}"`;

  if (!results.length) {
    emptyState.querySelector("strong").textContent = "No Match";
    emptyState.querySelector("span").textContent = "Try adding product type, material, voltage, grade, or application.";
    return;
  }

  results.forEach((result, index) => {
    const node = resultTemplate.content.cloneNode(true);
    const card = node.querySelector(".result-card");
    card.dataset.searchText = `${result.standard_code} ${result.title} ${result.category} ${result.subcategory}`.toLowerCase();
    card.dataset.confidence = result.confidence_label;
    node.querySelector(".rank").textContent = index + 1;
    node.querySelector("h3").textContent = result.title;
    node.querySelector(".standard-code").textContent = result.standard_code;
    node.querySelector(".reason").textContent = result.reason;
    node.querySelector(".score").textContent = result.score.toFixed(1);
    node.querySelector(".category").textContent = `${result.category} / ${result.subcategory}`;
    node.querySelector(".verify-status").textContent = result.verify_status.replaceAll("_", " ");
    node.querySelector(".confidence").textContent = `${result.confidence_label} (${Math.round(result.confidence_score * 100)}%)`;
    node.querySelector(".mandatory-hint").textContent = result.mandatory_hint;
    const sourceLink = node.querySelector(".source-link");
    sourceLink.href = result.source_url;

    if (result.evidence_clauses?.length) {
      const evidenceBlock = node.querySelector(".evidence-block");
      evidenceBlock.hidden = false;
      const evidenceList = node.querySelector(".evidence-list");
      result.evidence_clauses.forEach((clause) => {
        const quote = document.createElement("blockquote");
        quote.textContent = clause;
        evidenceList.append(quote);
      });
    }

    const terms = node.querySelector(".matched-terms");
    result.matched_terms.slice(0, 8).forEach((term) => terms.append(makeTag(term)));

    node.querySelectorAll(".feedback-button").forEach((button) => {
      button.addEventListener("click", () => submitFeedback(result, button.dataset.rating, button));
    });
    node.querySelectorAll(".review-button").forEach((button) => {
      button.addEventListener("click", () => submitReview(result, button.dataset.decision, button));
    });
    node.querySelector(".review-row").hidden = !currentUser || currentUser.role === "procurement";

    resultsList.append(node);
  });
}

function applyResultFilters() {
  const needle = resultFilter.value.trim().toLowerCase();
  const confidence = confidenceFilter.value;
  const cards = [...resultsList.querySelectorAll(".result-card")];
  let visible = 0;
  cards.forEach((card) => {
    const matchesText = !needle || card.dataset.searchText.includes(needle);
    const matchesConfidence = !confidence || card.dataset.confidence === confidence;
    card.hidden = !(matchesText && matchesConfidence);
    if (!card.hidden) visible += 1;
  });
  const filtered = Boolean(needle || confidence);
  resultSummary.textContent = filtered
    ? `${visible} of ${cards.length} results for "${currentResultQuery}"`
    : `${cards.length} result${cards.length === 1 ? "" : "s"} for "${currentResultQuery}"`;
}

async function submitReview(result, decision, button) {
  const card = button.closest(".result-card");
  const status = card.querySelector(".review-status");
  const note = card.querySelector(".review-note").value.trim();
  const buttons = card.querySelectorAll(".review-button");
  buttons.forEach((item) => {
    item.disabled = true;
  });
  status.textContent = "Saving...";

  try {
    const response = await fetch("/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        search_id: currentSearchId,
        standard_id: result.id,
        standard_code: result.standard_code,
        decision,
        note: note || null,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed with ${response.status}`);
    }
    buttons.forEach((item) => item.classList.toggle("selected", item.dataset.decision === decision));
    status.textContent = decision === "accepted" ? "Accepted for this search." : "Rejected for this search.";
  } catch (error) {
    status.textContent = error.message;
  } finally {
    buttons.forEach((item) => {
      item.disabled = false;
    });
  }
}

async function submitFeedback(result, rating, button) {
  const card = button.closest(".result-card");
  const status = card.querySelector(".feedback-status");
  const buttons = card.querySelectorAll(".feedback-button");
  buttons.forEach((item) => {
    item.disabled = true;
  });
  status.textContent = "Saving...";

  try {
    const response = await fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        search_id: currentSearchId,
        standard_id: result.id,
        standard_code: result.standard_code,
        rating,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed with ${response.status}`);
    }
    status.textContent = rating === "useful" ? "Marked useful." : "Marked not useful.";
  } catch (error) {
    status.textContent = error.message;
    buttons.forEach((item) => {
      item.disabled = false;
    });
  }
}

async function recommend() {
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    clearResults("Enter a procurement specification first.");
    return;
  }

  setLoading(true);
  try {
    const response = await fetch("/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        limit: Number(limitSelect.value),
        mode: modeSelect.value,
      }),
    });

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const payload = await response.json();
    renderResults(payload.query, payload.results, payload.search_id);
  } catch (error) {
    resultsList.replaceChildren();
    emptyState.hidden = false;
    emptyState.querySelector("strong").textContent = "Request Failed";
    emptyState.querySelector("span").textContent = error.message;
    resultSummary.textContent = "Could not fetch recommendations.";
  } finally {
    setLoading(false);
  }
}

function selectedDocument() {
  const file = documentInput.files[0];
  if (!file) {
    uploadStatus.textContent = "Select a TXT, PDF, or DOCX file first.";
    documentInput.focus();
    return null;
  }
  return file;
}

async function extractDocument() {
  const file = selectedDocument();
  if (!file) return;

  setLoading(true);
  uploadStatus.textContent = `Extracting ${file.name}...`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/extract-document", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed with ${response.status}`);
    }

    queryInput.value = payload.text;
    uploadStatus.textContent = `Extracted ${payload.char_count} characters from ${payload.filename}.`;
    clearResults("Extracted text is ready. Click Recommend Standards to search.");
  } catch (error) {
    uploadStatus.textContent = error.message;
  } finally {
    setLoading(false);
  }
}

async function recommendFromDocument() {
  const file = selectedDocument();
  if (!file) return;

  setLoading(true);
  uploadStatus.textContent = `Extracting and searching ${file.name}...`;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("limit", limitSelect.value);
  formData.append("mode", modeSelect.value);

  try {
    const response = await fetch("/recommend-document", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed with ${response.status}`);
    }

    queryInput.value = payload.preview || "";
    uploadStatus.textContent = `Analyzed ${payload.clauses_analyzed} clauses and ${payload.char_count} characters from ${payload.filename}.`;
    renderResults(payload.filename, payload.results, payload.search_id);
  } catch (error) {
    uploadStatus.textContent = error.message;
    resultSummary.textContent = "Could not process the uploaded document.";
  } finally {
    setLoading(false);
  }
}

recommendButton.addEventListener("click", recommend);

queryInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    recommend();
  }
});

clearButton.addEventListener("click", () => {
  queryInput.value = "";
  documentInput.value = "";
  uploadStatus.textContent = "No document selected.";
  clearResults();
  queryInput.focus();
});

extractButton.addEventListener("click", extractDocument);
recommendFileButton.addEventListener("click", recommendFromDocument);

document.querySelectorAll(".sample-chip").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query;
    recommend();
  });
});

workspaceTabs.forEach((tab) => {
  tab.addEventListener("click", () => showView(tab.dataset.view));
});
catalogQuery.addEventListener("input", renderCatalog);
catalogCategory.addEventListener("change", renderCatalog);
refreshHistory.addEventListener("click", loadHistory);
resultFilter.addEventListener("input", applyResultFilters);
confidenceFilter.addEventListener("change", applyResultFilters);
compareButton.addEventListener("click", showComparison);
closeComparison.addEventListener("click", () => comparisonDialog.close());

async function initializeApp() {
  const user = await loadCurrentUser();
  await loadCatalog();
  if (user?.role !== "procurement") await loadHistory();
}

checkHealth();
initializeApp().catch((error) => {
  apiStatus.classList.add("offline");
  apiStatus.lastChild.textContent = ` ${error.message}`;
});
logoutButton.addEventListener("click", logout);
