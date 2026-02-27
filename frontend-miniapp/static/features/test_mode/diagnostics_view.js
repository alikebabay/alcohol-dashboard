//diagnostics_view.js
export function getTestInputText() {
  return document.getElementById("test_input")?.value ?? "";
}

export function renderRunning() {
  const out = document.getElementById("output");
  if (!out) return;
  out.innerHTML = `<div class="event-item">▶ running graph test…</div>`;
}

export function renderError(msg) {
  const out = document.getElementById("output");
  if (!out) return;
  out.innerText = msg || "Test failed";
}

function groupLogsByRow(logs) {
  const map = {};
  let currentRow = null;

  logs.forEach(line => {
    const match = line.match(/\[ROW\]\s+i=(\d+)/);
    if (match) {
      currentRow = parseInt(match[1], 10);
      if (!map[currentRow]) map[currentRow] = [];
    }

    if (currentRow !== null) {
      if (!map[currentRow]) map[currentRow] = [];
      map[currentRow].push(line);
    }
  });

  return map;
}

export function renderGraphDiff(rows, logs = []) {
  const out = document.getElementById("output");
  if (!out) return;

  // Group logs per row index
  const logsByRow = groupLogsByRow(logs);

  const html = rows.map((r, i) => {
    const rowLogs = logsByRow[i] || [];
    const hasLogs = rowLogs.length > 0;

    const base = r.changed
      ? `
        <div class="raw">${escapeHtml(r.raw)}</div>
        <div class="norm">→ ${escapeHtml(r.norm)}</div>
      `
      : `
        <div class="raw">${escapeHtml(r.raw)}</div>
        <div class="unchanged">→ (no change)</div>
      `;

    const logsBlock = hasLogs
      ? `
        <div class="row-logs-toggle" data-row="${i}">
          ▶ logs (${rowLogs.length})
        </div>
        <pre class="row-logs" id="row_logs_${i}" style="display:none;">
${escapeHtml(rowLogs.join("\n"))}
        </pre>
      `
      : "";

    return `
      <div class="diff-row ${r.changed ? "changed" : "unchanged"}">
        ${base}
        ${logsBlock}
      </div>
    `;
  }).join("");

  out.innerHTML = html;

  // toggle wiring
  document.querySelectorAll(".row-logs-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = btn.dataset.row;
      const el = document.getElementById(`row_logs_${idx}`);
      const hidden = el.style.display === "none";
      el.style.display = hidden ? "block" : "none";
      btn.innerText = hidden ? "▼ hide logs" : `▶ logs (${logsByRow[idx].length})`;
    });
  });
}


// tiny safety: prevent HTML injection from backend strings
function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}