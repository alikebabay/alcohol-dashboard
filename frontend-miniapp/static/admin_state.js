// admin_state.js
import { renderEditorLayout } from "./admin_editor.js";
import { runGraphTest} from "./admin_diagnostics.js";
import { testGBX} from "./admin_diagnostics.js";
import { testPrice} from "./admin_diagnostics.js";
import { renderEvents } from "./events.js";
import { renderOfferCard } from "./render_offer.js";


// =========================
// GLOBAL STATE
// =========================
window.state = 0;              // 0 = idle, 1 = supplier selected, 2 = nodes/offers view, 3 = test mode, 4 = offer editor
window.viewMode = "nodes";     // nodes | offers
window.activeSupplier = null; // stored selected supplier
window.lastNodes = []; // cached nodes for state 2
window.lastOffers = []; // cached offers
window.canonicalIds = new Set(); //cached canonicals for state 2
window.supplierExcluded = false; //managing states for suppliers
window.activeOfferId = null;   // 👈 editor context
window.editorOriginals = null;   // show originals for supplier offers null = not loaded yet

// =========================
// STATE TRANSITIONS
// =========================
export function resetState() {
    if (state === 2) {
        state = 1;
        renderState();
        return;
    }
    activeSupplier = null;
    state = 0;
    renderState();
    renderEvents();
}

function enterTestMode() {
    state = 3;
    renderState();
    wireTestModeButtons();
}

function exitTestMode() {
    state = 0;
    renderState();
}


// =========================
// RENDER STATE
// =========================


function renderState() {
    const s = state;
    // reset editor mode by default
    document.body.classList.remove("editor-mode");
    const lbl  = document.getElementById("active_supplier");
    const btnC = document.getElementById("btn_change_supplier");
    const rm   = document.getElementById("btn_remove");
    const nd   = document.getElementById("btn_nodes");
    const df   = document.getElementById("btn_dfout");
    const dfoutBlock = document.getElementById("dfout_block");
    const adminPanel = document.getElementById("admin_panel");
    const testPanel  = document.getElementById("test_panel");

    //default visibility
    adminPanel.style.display = "block";
    testPanel.style.display  = "none";

    //main menu button
    const btnMain = document.getElementById("btn_main_menu");
    if (btnMain) {
        btnMain.style.display = state === 0 ? "none" : "inline-block";
    }
    
    // =====================
    // STATE 0: EVENT LOG
    // =====================

    if (s === 0) {
    lbl.innerText = "Event Log";
    // RESTORE MENU ITEMS (editor hides them globally)
    document.querySelectorAll(".menu .menu-item").forEach(el => {
        el.style.display = "block";
    });
    
    btnC.style.display = "none";
    rm.style.display   = "none";
    nd.style.display   = "none";
    df.style.display   = "none";
    document.getElementById("btn_offers").style.display = "none";

    // hide DFOUT tools in idle
    dfoutBlock.style.display = "none";
    
    //manage suppliers
    document.getElementById("btn_toggle_excluded").style.display = "none";

    // show event log
    const out = document.getElementById("output");
    out.style.display = "block";
    renderEvents();
    return;
    }

    //show test button
    const btnTest = document.getElementById("btn_test");
    if (btnTest) btnTest.style.display = "block";

    if (s === 1) { // supplier selected state
        lbl.innerText = "Active supplier: " + activeSupplier;
        btnC.style.display = "block"; //change supplier
        rm.style.display   = "block"; //remove supplier
        nd.style.display   = "block"; //find all nodes for supplier
        df.style.display   = "block"; //turns deletedf out button display

        dfoutBlock.style.display = "block";
        document.getElementById("btn_offers").style.display = "block";
        document.getElementById("output").style.display = "block";
        //manage suppliers
        const ex = document.getElementById("btn_toggle_excluded");
        ex.style.display = "block";
        ex.innerText = supplierExcluded
            ? "✅ Include in pivot"
            : "🚫 Exclude from pivot";
        renderEvents();
        return;
    }

    if (s === 2) {   // NODES VIEW
        lbl.innerText = "Nodes for: " + activeSupplier;
        btnC.style.display = "block";
        rm.style.display   = "block";
        nd.style.display   = "block";
        df.style.display   = "block";

        dfoutBlock.style.display = "block";

        const out = document.getElementById("output");
        out.style.display = "block";
        // 🆕 BRAND PANEL — только в offers
        const brandPanel = document.getElementById("brand_panel");
        if (brandPanel) {
            brandPanel.style.display =
                viewMode === "offers" ? "block" : "none";
        }

        //manage suppliers
        const ex = document.getElementById("btn_toggle_excluded");
        ex.style.display = "block";
        ex.innerText = supplierExcluded
            ? "✅ Include in pivot"
            : "🚫 Exclude from pivot";

        // OFFERS VIEW
        if (viewMode === "offers") {
            out.innerHTML = lastOffers
                .filter(o => o.type === "Offer")
                .map(o => renderOfferCard(o))
                .join("");
            return;
        }

    // Render NODES (separate pipeline)
    out.innerHTML = lastNodes.map(n => {
        const id = n.id || "?";
        const name = n.name || "";

        let cls = "node-other";
        const t = (n.type || "").toLowerCase();

        if (t === "offer") cls = "node-offer";
        else if (t === "dfout") cls = "node-dfout";
        else if (t === "dfraw") cls = "node-dfraw";
        else if (t === "rawblob") cls = "node-rawblob";
        else if (t === "brand") cls = "node-brand";

        const isCanonical =
            t === "dfout" && canonicalIds.has(id);

        const badge = isCanonical
            ? `<div class="badge-canonical">⭐ canonical</div>`
            : "";

        return `
            <div class="node-item ${cls}" data-id="${id}">
                <div>
                    <b>${n.type}</b>${badge}
                </div>

                <div>
                    ID: <span class="copy-id" data-copy="${id}">${id}</span>
                </div>

                <div>
                    <b>${name}</b>
                </div>
                <button class="node-download" title="Download">⬇</button>
                <button class="node-delete" title="Delete">🗑</button>
            </div>

        `;
    }).join("");
    
        return;
    }
    // =====================
    // STATE 3: TEST MODE
    // =====================
    if (s === 3) {
        lbl.innerText = "TEST MODE";

        // hide ALL admin UI
        adminPanel.style.display = "none";

        // 🔧 RESTORE test menu buttons (editor hid them globally)
        testPanel.querySelectorAll(".menu-item").forEach(el => {
            el.style.display = "block";
        });

        btnC.style.display = "none";
        rm.style.display   = "none";
        nd.style.display   = "none";
        df.style.display   = "none";
        document.getElementById("btn_offers").style.display = "none";
        document.getElementById("btn_toggle_excluded").style.display = "none";

        // show test UI
        testPanel.style.display = "block";

        // output stays visible and generic
        const out = document.getElementById("output");
        out.style.display = "block";
        out.innerHTML = "<em>Paste text on the left and run a test.</em>";

        return;
    }

    // =====================
    // STATE 4: OFFER EDITOR
    // =====================
    if (s === 4) {
        
        // enable editor layout mode
        document.body.classList.add("editor-mode");
        // === LEFT PANEL ===
        // suppliers остаются
        adminPanel.style.display = "block";

        // === HIDE ALL MENU BUTTONS ===
        btnC.style.display = "none";
        rm.style.display   = "none";
        nd.style.display   = "none";
        df.style.display   = "none";
        document.getElementById("btn_offers").style.display = "none";
        document.getElementById("btn_toggle_excluded").style.display = "none";
        // hide bottom action buttons
        document.querySelectorAll(".menu .menu-item").forEach(el => {
            el.style.display = "none";
        });

        // 🔄 Rebuild Sheets must stay visible in editor
        const rebuildBtn = document.getElementById("btn_rebuild_sheets");
        if (rebuildBtn) rebuildBtn.style.display = "block";

        // === HIDE DFOUT / BRAND / OTHER TOOLS ===
        dfoutBlock.style.display = "none";
        const brandBlock = document.getElementById("brand")?.closest(".section-block");
        if (brandBlock) brandBlock.style.display = "none";

        // === HIDE TEST PANEL ===
        testPanel.style.display = "none";

        // === OUTPUT = EDITOR ===
        const out = document.getElementById("output");
        out.style.display = "block";

        // ⬇️ ВАЖНО: editor layout живёт в admin_editor.js
        renderEditorLayout();
        return;
    }    
}


//wiring buttons from admin.html
export function wireMainMenu() {
    const btn = document.getElementById("btn_main_menu");
    if (!btn) return;

    btn.addEventListener("click", () => {
        resetState();
    });
}

export function wireTestButton() {
    const btn = document.getElementById("btn_test");
    if (!btn) return;

    btn.addEventListener("click", enterTestMode);
}

function wireTestModeButtons() {
    document.getElementById("btn_test_graph")
        ?.addEventListener("click", runGraphTest);

    document.getElementById("btn_test_gbx")
        ?.addEventListener("click", testGBX);

    document.getElementById("btn_test_price")
        ?.addEventListener("click", testPrice);

    document.getElementById("btn_test_exit")
        ?.addEventListener("click", exitTestMode);
}

// expose to window for legacy code
window.renderState = renderState;
