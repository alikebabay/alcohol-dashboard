import { api } from "../../admin_backend.js";
import { showToast } from "../../toast.js";
import { appState } from "../../admin_state.js";

/**
 * Mount one global click delegate for delete buttons.
 *
 * Expects buttons in DOM:
 * - <button data-del-brand="Brand Name">🗑</button>
 * - <button data-del-series data-brand="B" data-series="S">🗑</button>
 * - <button data-del-canonical="Canonical Name">🗑</button>
 *
 * Options:
 * - refresh(): optional async callback to re-render / re-run search after delete
 */
export function mountDeleteButtons(options = {}) {
  if (mountDeleteButtons._mounted) return; // guard
  mountDeleteButtons._mounted = true;

  const refresh = options.refresh || (async () => {});

  document.addEventListener("click", async (e) => {
    // buttons should only work in advanced mode
    if (appState.mode !== "advanced") return;

    // -------- brand --------
    const b = e.target.closest("[data-del-brand]");
    if (b) {
      const name = b.dataset.delBrand || "";
      const ok = confirm(`Delete brand?\n\n${name}`);
      if (!ok) return;

      const res = await api("/delete/brand", "POST", { name }, false);
      if (res?.ok) {
        showToast("Deleted");
        await refresh();
      } else {
        showToast(res?.error || "brand not found");
      }
      return;
    }
    // -------- brand alias --------
    const ba = e.target.closest("[data-del-brand_alias]");
    if (ba) {
      const brand = ba.dataset.brand || "";
      const brand_alias = ba.dataset.delBrand_alias || "";
      if (!brand || !brand_alias) return;
      const ok = confirm(`Delete brand alias?\n\n${brand} — ${brand_alias}`);
      if (!ok) return;

      const res = await api("/delete/brand/alias", "POST", { brand, brand_alias }, false);
      if (res?.ok) {
        showToast("Deleted");
        await refresh();
      } else {
        showToast(res?.error || "Brand alias not found");
      }
      return;
    }
    // -------- series (scoped) --------
    const ser = e.target.closest("[data-del-series]");
    if (ser) {
      const brand = ser.dataset.brand || "";
      const series = ser.dataset.series || "";
      if (!brand || !series) return;
      const ok = confirm(`Delete series?\n\n${brand} — ${series}`);
      if (!ok) return;

      const res = await api("/delete/series", "POST", { brand, series }, false);
      if (res?.ok) {
        showToast("Deleted");
        await refresh();
      } else {
        showToast(res?.error || "series not found");
      }
      return;
    }

    // -------- canonical --------
    const c = e.target.closest("[data-del-canonical]");
    if (c) {
      const name = c.dataset.delCanonical || "";
      const ok = confirm(`Delete canonical?\n\n${name}`);
      if (!ok) return;

      const res = await api("/delete/canonical", "POST", { name }, false);
      if (res?.ok) {
        showToast("Deleted");
        await refresh();
      } else {
        showToast(res?.error || "canonical not found");
      }
    }
  });
}
