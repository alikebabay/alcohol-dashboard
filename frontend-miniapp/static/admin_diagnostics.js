//admin_diagnostics.js

import { api } from "./admin_backend.js";

// =========================
// TEST MODE 
// =========================

export async function runGraphTest() {
    const text = document.getElementById("test_input").value;

    if (!text.trim()) {
        showToast("No input text");
        return;
    }

    const out = document.getElementById("output");
    out.innerHTML = `<div class="event-item">▶ running graph test…</div>`;

    const res = await api(
        "/test/graph",
        "POST",
        { text },
        false
    );

    if (!res.ok) {
        out.innerText = res.error || "Test failed";
        return;
    }

    out.innerHTML = res.data.map(r => {
        if (!r.changed) {
            return `
                <div class="diff-row unchanged">
                    <div class="raw">${r.raw}</div>
                    <div class="unchanged">→ (no change)</div>
                </div>
            `;
        }

        return `
            <div class="diff-row changed">
                <div class="raw">${r.raw}</div>
                <div class="norm">→ ${r.norm}</div>
            </div>
        `;

    }).join("");
}

export function testGBX() {
    showToast("GBX test not implemented yet");
}

export function testPrice() {
    showToast("Price test not implemented yet");
}