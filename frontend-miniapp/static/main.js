// main.js
import { setLogLevel, enableModule, disableModule } from "./logger.js";

const isLocal =
    location.hostname === "localhost" ||
    location.hostname === "127.0.0.1";

if (isLocal) {
    setLogLevel("trace");
    enableModule("state");
    enableModule("editor");
} else {
    setLogLevel("error");
}


import { showToast } from "./toast.js";
window.showToast = showToast;
import { ClipboardHelper } from "./clipboard.js";

// core logic
import "./admin_backend.js";
import "./admin_state.js";
import "./admin_editor.js";
import "./render_offer.js";
import "./events.js";

// wiring
import { wireMainMenu, wireTestButton, renderState } from "./admin_state.js";
import { wireOfferButtons } from "./admin_backend.js";
import { wireSupplierMenu, loadSuppliers, wireSupplierSearch} from "./admin_backend.js";
import { wireEditorOfferList } from "./admin_editor.js";
import { wireEditorOriginals } from "./admin_editor.js";
import { wireAdminActions } from "./admin_backend.js";
import { wireCanonical } from "./admin_editor.js";
import { wireNodeDeleteHandler } from "./admin_backend.js";
import { wireOfferEditHandler } from "./admin_backend.js";
import { initDownloadHandler } from "./admin_editor.js";
import { mountDeleteButtons } from "./features/delete_buttons/delete_buttons_controller.js";
import { wireOfferSearch } from "./admin_backend.js";




document.addEventListener("DOMContentLoaded", async () => {
    await loadPartial("brand_panel_container", "/static/partials/brand_panel.html");
    await loadPartial("suppliers_panel_container", "/static/partials/suppliers_panel.html");
    await loadPartial("test_panel_container", "/static/partials/test_panel.html");
    wireMainMenu();
    wireTestButton();
    wireOfferButtons();
    wireSupplierMenu();
    wireSupplierSearch();
    wireEditorOfferList();
    wireEditorOriginals();
    await loadSuppliers();
    renderState();
    wireAdminActions();
    wireCanonical();
    mountDeleteButtons({
    refresh: async () => renderState(), // или если хочешь перезапуск поиска — скажи, сделаем
    });
    wireNodeDeleteHandler();
    wireOfferEditHandler();
    initDownloadHandler();
    wireOfferSearch();
});


// ------------------------------------------------------------
// Global copy handler via data-copy attribute
// ------------------------------------------------------------
document.addEventListener("click", async e => {
    const el = e.target.closest("[data-copy]");
    if (!el) return;

    const text = el.dataset.copy;
    if (!text) return;

    const ok = await ClipboardHelper.copy(text);
    showToast(ok ? "Copied" : "Copy failed");
});


//loader for partials in admin.html
async function loadPartial(id, url) {
  const res = await fetch(url);
  document.getElementById(id).innerHTML = await res.text();
}
