// main.js

import { showToast } from "./toast.js";
window.showToast = showToast;

// core logic
import "./admin_backend.js";
import "./admin_state.js";
import "./admin_editor.js";
import "./render_offer.js";
import "./events.js";

// wiring
import { wireMainMenu, wireTestButton } from "./admin_state.js";
import { wireOfferButtons } from "./admin_backend.js";
import { wireSupplierMenu } from "./admin_backend.js";
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