// default_series_view.js

import { loadDefaultSeries } from "./default_series_model.js";

export async function renderDefaultSeriesHTML() {
    const brands = await loadDefaultSeries();

    if (!brands?.length) {
        return "<em>No default canonicals</em>";
    }

    return `
        <div class="canon-grid">
            ${brands.map(b => `
                <div class="canon-col">
                    <div class="canon-brand">${b.name}</div>
                    <div class="canon-series">
                        ${b.series.map(s => `
                            <button
                                type="button"
                                class="default-canon-item"
                                data-brand="${b.name}"
                                data-series="${s}"
                            >
                                • ${s}
                            </button>
                        `).join("")}
                    </div>
                </div>
            `).join("")}
        </div>
    `;
}
