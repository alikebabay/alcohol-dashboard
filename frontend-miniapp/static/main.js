// main.js

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
import { wireSupplierMenu, loadSuppliers} from "./admin_backend.js";
import { wireEditorOfferList } from "./admin_editor.js";
import { wireEditorOriginals } from "./admin_editor.js";
import { wireAdminActions } from "./admin_backend.js";
import { wireCanonical } from "./admin_editor.js";
import { wireNodeDeleteHandler } from "./admin_backend.js";
import { wireOfferEditHandler } from "./admin_backend.js";
import { initDownloadHandler } from "./admin_editor.js";



document.addEventListener("DOMContentLoaded", async () => {
    wireMainMenu();
    wireTestButton();
    wireOfferButtons();
    wireSupplierMenu();
    wireEditorOfferList();
    wireEditorOriginals();
    await loadSuppliers();
    renderState();
    wireAdminActions();
    wireCanonical();
    wireNodeDeleteHandler();
    wireOfferEditHandler();
    initDownloadHandler();
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
