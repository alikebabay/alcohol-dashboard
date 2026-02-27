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

export function renderGraphDiff(rows, logs = []) {
  const out = document.getElementById("output");
  if (!out) return;

  const rowsHtml = rows.map((r, i) => {
    if (!r.changed) {
      return `
        <div class="diff-row unchanged">
          <div class="raw">${escapeHtml(r.raw)}</div>
          <div class="unchanged">→ (no change)</div>
        </div>`;
    }

    return `
      <div class="diff-row changed">
        <div class="raw">${escapeHtml(r.raw)}</div>
        <div class="norm">→ ${escapeHtml(r.norm)}</div>
      </div>`;
  }).join("");

  const logsHtml = logs.length
    ? `
      <div class="logs-block">
        <div class="logs-toggle" id="toggle_logs">
          ▶ Show debug logs (${logs.length} lines)
        </div>
        <pre class="logs-content" id="logs_content" style="display:none;">
${escapeHtml(logs.join("\n"))}
        </pre>
      </div>`
    : "";

  out.innerHTML = rowsHtml + logsHtml;

  // toggle logic
  const toggle = document.getElementById("toggle_logs");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const content = document.getElementById("logs_content");
      const isHidden = content.style.display === "none";

      content.style.display = isHidden ? "block" : "none";
      toggle.innerText = isHidden
        ? "▼ Hide debug logs"
        : `▶ Show debug logs (${logs.length} lines)`;
    });
  }
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