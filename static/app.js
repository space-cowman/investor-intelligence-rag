const $ = (id) => document.getElementById(id);
const state = { metrics: [], selectedKey: null };

const KPI_COLUMNS = ["revenue", "net_income", "operating_income", "cash_flow", "total_assets", "total_liabilities"];
const keyOf = (r) => `${r.company}|${r.year ?? ""}`;
const lines = (text) => (text || "").split("\n").map((s) => s.trim()).filter(Boolean);
const NULL_STRINGS = new Set(["null", "none", "n/a", "na", "not available", "unavailable", "not found", ""]);
const display = (value) => (value == null || NULL_STRINGS.has(String(value).trim().toLowerCase()) ? "—" : value);

/* ---------- API helper ---------- */
async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

/* ---------- Toasts ---------- */
function toast(title, message, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  const strong = document.createElement("strong");
  strong.textContent = title;
  const body = document.createElement("span");
  body.textContent = message;
  el.append(strong, body);
  $("toasts").appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

/* ---------- Health ---------- */
async function loadHealth() {
  try {
    await api("/health");
    $("health").className = "health ok";
    $("healthText").textContent = "API online";
  } catch {
    $("health").className = "health down";
    $("healthText").textContent = "API offline";
  }
}

/* ---------- Metrics ---------- */
async function loadMetrics() {
  try {
    state.metrics = await api("/api/metrics");
  } catch (e) {
    toast("Could not load metrics", e.message, "error");
    state.metrics = [];
  }
  state.metrics.sort((a, b) => a.company.localeCompare(b.company) || (b.year ?? 0) - (a.year ?? 0));
  renderStats();
  renderTable();
  renderScope();
  if (!state.metrics.some((r) => keyOf(r) === state.selectedKey)) {
    state.selectedKey = state.metrics.length ? keyOf(state.metrics[0]) : null;
  }
  renderDetail();
}

function renderStats() {
  const companies = new Set(state.metrics.map((r) => r.company));
  $("statCompanies").textContent = companies.size;
  $("statReports").textContent = state.metrics.length;
  const latest = state.metrics.map((r) => r.updated_at || r.created_at).filter(Boolean).sort().pop();
  $("statUpdated").textContent = latest ? new Date(latest).toLocaleDateString() : "–";
}

function renderTable() {
  const filter = $("tableFilter").value.trim().toLowerCase();
  const rows = state.metrics.filter((r) => r.company.toLowerCase().includes(filter));
  const body = $("kpiBody");
  body.replaceChildren();

  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.tabIndex = 0;
    if (keyOf(r) === state.selectedKey) tr.classList.add("selected");

    const company = document.createElement("td");
    company.className = "company-cell";
    company.textContent = r.company;
    const year = document.createElement("td");
    year.textContent = r.year ?? "–";
    tr.append(company, year);

    KPI_COLUMNS.forEach((col) => {
      const td = document.createElement("td");
      td.className = "num";
      td.textContent = display(r[col]);
      tr.appendChild(td);
    });

    const select = () => selectReport(keyOf(r));
    tr.addEventListener("click", select);
    tr.addEventListener("keydown", (e) => { if (e.key === "Enter") select(); });
    body.appendChild(tr);
  });

  $("emptyState").hidden = state.metrics.length > 0;
}

function selectReport(key) {
  state.selectedKey = key;
  renderTable();
  renderDetail();
  $("chatScope").value = key;
}

function renderDetail() {
  const r = state.metrics.find((m) => keyOf(m) === state.selectedKey);
  $("detailCard").hidden = !r;
  if (!r) return;

  $("detailTitle").textContent = `${r.company} · FY ${r.year ?? "–"}`;
  const updated = r.updated_at || r.created_at;
  $("detailUpdated").textContent = updated ? `Updated ${new Date(updated).toLocaleString()}` : "";

  fillList($("driversList"), lines(r.growth_drivers), "No growth drivers extracted.");
  fillList($("risksList"), lines(r.risk_factors), "No risk factors extracted.");
}

function fillList(listEl, items, emptyText) {
  listEl.replaceChildren();
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "none";
    li.textContent = emptyText;
    listEl.appendChild(li);
    return;
  }
  items.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    listEl.appendChild(li);
  });
}

function renderScope() {
  const scope = $("chatScope");
  const current = scope.value;
  scope.replaceChildren(new Option("All reports", ""));
  state.metrics.forEach((r) => scope.appendChild(new Option(`${r.company} (${r.year ?? "–"})`, keyOf(r))));
  if ([...scope.options].some((o) => o.value === current)) scope.value = current;
}

/* ---------- Chat ---------- */
// function addMessage(role, text) {
//   const wrap = document.createElement("div");
//   wrap.className = `msg ${role}`;
//   const bubble = document.createElement("div");
//   bubble.className = "bubble";
//   bubble.textContent = text;
//   wrap.appendChild(bubble);
//   $("chatLog").appendChild(wrap);
//   $("chatLog").scrollTop = $("chatLog").scrollHeight;
//   return wrap;
// }

function addMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const isBot = role === "bot";
  if (isBot && window.marked && window.DOMPurify) {
    bubble.classList.add("md");
    bubble.innerHTML = DOMPurify.sanitize(marked.parse(text));   // rendered + sanitized
  } else {
    bubble.textContent = text;                                    // user text stays plain
  }

  wrap.appendChild(bubble);
  $("chatLog").appendChild(wrap);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
  return wrap;
}

async function sendQuestion(question) {
  question = question.trim();
  if (!question) return;

  const payload = { question };
  const scoped = state.metrics.find((r) => keyOf(r) === $("chatScope").value);
  if (scoped) {
    payload.company = scoped.company;
    if (scoped.year) payload.year = Number(scoped.year);
  }

  addMessage("user", question);
  $("chatInput").value = "";
  $("sendBtn").disabled = true;
  const typing = addMessage("bot typing", "Thinking…");

  try {
    const data = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    typing.remove();
    addMessage("bot", data.answer || "No answer returned.");
  } catch (e) {
    typing.remove();
    addMessage("error", `Error: ${e.message}`);
  } finally {
    $("sendBtn").disabled = false;
    $("chatInput").focus();
  }
}

$("chatForm").addEventListener("submit", (e) => {
  e.preventDefault();
  sendQuestion($("chatInput").value);
});
$("chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendQuestion($("chatInput").value);
  }
});
document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => sendQuestion(chip.textContent))
);

/* ---------- Upload ---------- */
function setProgress(text, pct = null) {
  $("progress").hidden = false;
  $("progressText").textContent = text;
  const fill = $("progressFill");
  if (pct === null) {
    fill.classList.add("indeterminate");
    $("progressPct").textContent = "";
  } else {
    fill.classList.remove("indeterminate");
    fill.style.width = `${pct}%`;
    $("progressPct").textContent = `${pct}%`;
  }
}

function uploadFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    toast("Invalid file", "Please upload a PDF report.", "error");
    return;
  }
  if (!/^\d{4}_.+\.pdf$/i.test(file.name)) {
    toast("Check the file name", "Use YEAR_Company.pdf (e.g. 2024_Apple.pdf) so company and year are detected.", "info");
  }

  const form = new FormData();
  form.append("file", file);
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/upload");

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) setProgress("Uploading…", Math.round((e.loaded / e.total) * 100));
  };
  xhr.upload.onload = () => setProgress("Processing: chunking, embedding and extracting KPIs (may take a few minutes)…");

  xhr.onload = async () => {
    $("progress").hidden = true;
    if (xhr.status >= 200 && xhr.status < 300) {
      toast("Ingestion complete", `${file.name} was processed.`, "success");
      await loadMetrics();
      const match = file.name.match(/^(\d{4})_.*?([^_]+)\.pdf$/i);
      if (match) {
        const key = `${match[2]}|${match[1]}`;
        if (state.metrics.some((r) => keyOf(r) === key)) selectReport(key);
      }
    } else {
      let detail = "Server error.";
      try { detail = JSON.parse(xhr.responseText).detail || detail; } catch {}
      toast("Ingestion failed", detail, "error");
    }
  };
  xhr.onerror = () => {
    $("progress").hidden = true;
    toast("Connection error", "Could not reach the server.", "error");
  };

  setProgress("Uploading…", 0);
  xhr.send(form);
}

const dropzone = $("dropzone");
$("browseBtn").addEventListener("click", () => $("fileInput").click());
$("fileInput").addEventListener("change", (e) => {
  if (e.target.files.length) uploadFile(e.target.files[0]);
  e.target.value = "";
});
["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
});

/* ---------- Init ---------- */
$("tableFilter").addEventListener("input", renderTable);
loadHealth();
loadMetrics();
