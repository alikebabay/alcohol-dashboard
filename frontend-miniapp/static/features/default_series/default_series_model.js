// frontend-miniapp/static/features/default_series/default_series_model.js

import { api } from "../../admin_backend.js";

let defaultSeriesCache = null;

export async function loadDefaultSeries() {
    if (defaultSeriesCache) return defaultSeriesCache;
    const res = await api("/default_series");
    defaultSeriesCache = res.brands;
    return defaultSeriesCache;
}

export function clearDefaultSeriesCache() {
    defaultSeriesCache = null;
}

// MOCK remove (keeps API knowledge in the model)
export async function removeDefaultSeries(brand, series) {
    console.log("[MOCK] remove default series", { brand, series });
    await api("/default_series/remove", "POST", { brand, series }, false);
    clearDefaultSeriesCache();
}

// MOCK add
export async function addDefaultSeries(brand, series) {
    console.log("[MOCK] add default series", { brand, series });
    await api("/default_series/add", "POST", { brand, series }, false);
    clearDefaultSeriesCache();
}
