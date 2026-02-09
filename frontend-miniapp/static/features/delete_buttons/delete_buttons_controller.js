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

    // -------- series (scoped) --------
    const s = e.target.closest("[data-del-series]");
    if (s) {
      const brand = s.dataset.brand || "";
      const series = s.dataset.series || "";
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
