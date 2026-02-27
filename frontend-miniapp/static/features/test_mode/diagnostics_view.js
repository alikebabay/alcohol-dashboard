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

export function renderGraphDiff(rows) {
  const out = document.getElementById("output");
  if (!out) return;

  out.innerHTML = rows.map(r => {
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