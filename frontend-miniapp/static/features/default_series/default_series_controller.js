// default_series_controller.js

import { getLogger } from "../../logger.js";
import { showToastAt } from "../../toast.js";

import { renderDefaultSeriesHTML } from "./default_series_view.js";
import { removeDefaultSeries, addDefaultSeries } from "./default_series_model.js";

const log = getLogger("default_series");

export function wireDefaultCanonicals(containerEl) {
    log.info("wireDefaultCanonicals", {
        childCount: containerEl.children.length
    });

    containerEl.querySelectorAll(".default-canon-item").forEach(el => {
        el.addEventListener("click", async () => {
            const brand = el.dataset.brand;
            const series = el.dataset.series;

            log.info("remove click", { brand, series });

            const ok = confirm(`Remove default canonical?\n\n${brand} — ${series}`);
            if (!ok) return;

            await removeDefaultSeries(brand, series);

            containerEl.innerHTML = await renderDefaultSeriesHTML();
            wireDefaultCanonicals(containerEl);
        });
    });
}


// Render default series as its own panel inside brand_panel
export async function mountDefaultSeriesPanel() {
    log.info("mountDefaultSeriesPanel");

    const anchor = document.getElementById("default_series_anchor");
    if (!anchor) {
        log.warn("default_series_anchor not found");
        return;
    }

    let panel = document.getElementById("default_series_panel");
    if (!panel) {
        panel = document.createElement("div");
        panel.id = "default_series_panel";
        anchor.appendChild(panel);
    }

    panel.innerHTML = `
        <h4> Default series</h4>

        <div style="margin-top:6px;">
           <input
                id="default_series_brand"
                placeholder="Brand"
                style="width:100%; margin-bottom:4px;"
            />
           <input
                id="default_series_series"
                placeholder="Series"
                style="width:100%; margin-bottom:6px;"
            />
            <button id="btn_add_default_series">
                ➕ Add default series
            </button>
        </div>
    `;

    const btn = panel.querySelector("#btn_add_default_series");
    btn.addEventListener("click", async () => {
        const brand = panel.querySelector("#default_series_brand").value.trim();
        const series = panel.querySelector("#default_series_series").value.trim();
        const r = btn.getBoundingClientRect();

        if (!brand || !series) {
            showToastAt(r.right, r.top, "Brand and Series are required");
            return;
        }

        await addDefaultSeries(brand, series);
        showToastAt(r.right, r.top, `(mock) ${brand} — ${series}`);

        // optional: clear inputs
        panel.querySelector("#default_series_brand").value = "";
        panel.querySelector("#default_series_series").value = "";
    });

    wireDefaultCanonicals(panel);
}
