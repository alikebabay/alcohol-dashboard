// admin_state.js
import { renderEditorLayout } from "./admin_editor.js";
import { runGraphTest} from "./admin_diagnostics.js";
import { testGBX} from "./admin_diagnostics.js";
import { testPrice} from "./admin_diagnostics.js";
import { renderEvents } from "./events.js";
import { renderOfferCard } from "./render_offer.js";


// =========================
// MODULE STATE
// =========================
export const appState = {
    mode: "default",       // default | advanced
    state: 0,              // 0 = idle, 1 = supplier selected, 2 = nodes/offers view, 3 = test mode, 4 = offer editor
    viewMode: "nodes",     // nodes | offers
    activeSupplier: null,
    lastNodes: [],
    lastOffers: [],
    canonicalIds: new Set(),
    supplierExcluded: false,
    activeOfferId: null,
    editorOriginals: null,
};

// ==========
// STATE DISPATCHER
// ==========
export function renderState() {
    if (appState.mode === "advanced") {
        renderAdvancedState();
    } else {
        renderDefaultState();
    }
}

// panel mover
function moveBrandPanel(target) {
    const panel = document.getElementById("brand_panel");
    if (!panel) return;

    // HTML anchors:
    // - advanced (LEFT):  #brand_panel_container
    // - default/editor (RIGHT): #brand_anchor_default
    const left  = document.getElementById("brand_panel_container");
    const right = document.getElementById("brand_anchor_default");

    if (!panel) {
        console.warn("brand_panel not found");
        return;
    }

    if (target === "left" && left && panel.parentElement !== left) {
        left.appendChild(panel);
    }
    if (target === "right" && right && panel.parentElement !== right) {
        right.appendChild(panel);
    }
}


// =========================
// STATE TRANSITIONS
// =========================
export function resetState() {
    if (appState.state === 2) {
        appState.state = 1;
        renderState();
        return;
    }
    appState.activeSupplier = null;
    appState.state = 0;
    renderState();
    renderEvents();
}

function enterTestMode() {
    appState.state = 3;
    renderState();
    wireTestModeButtons();
}

function exitTestMode() {
    appState.mode = "default";
    appState.state = 0;    
    renderState();
}

// =========================
// ADVANCED STATE USERS
// =========================


function enterAdvancedMode() {
    appState.mode = "advanced";
    renderState();
}

function exitAdvancedMode() {
    appState.mode = "default";
    renderState();
}

function renderAdvancedState() {
    const lbl = document.getElementById("active_supplier");
    const out = document.getElementById("output");
    const adminPanel = document.getElementById("admin_panel");
    const brandPanel = document.getElementById("brand_panel");
    const dfoutBlock = document.getElementById("dfout_block");
    const testPanel  = document.getElementById("test_panel");
    const modeBox = document.getElementById("mode_controls");

    lbl.innerText = "ADVANCED MODE";
    // hide suppliers / test / dfout
    if (adminPanel) adminPanel.style.display = "none";
    if (dfoutBlock) dfoutBlock.style.display = "none";
    if (testPanel)  testPanel.style.display = "none";

    // show brand panel (left side logic already handled by HTML)
    moveBrandPanel("left");
    if (brandPanel) brandPanel.style.display = "block";

    // output = defaults view
    out.style.display = "block";
    out.innerHTML = "<em>Default brands / series will be shown here</em>";

    modeBox.innerHTML = `
        <button id="btn_back_default">← Back</button>
    `;
    document.getElementById("btn_back_default")
        ?.addEventListener("click", exitAdvancedMode);
}


// =========================
// DEFAULT STATE FOR USERS
// =========================


function renderDefaultState() {
    const s = appState.state;
    // ВСЕГДА возвращаем бренд-панель вправо в default режиме
    moveBrandPanel("right");
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
        const show =
            appState.state !== 0 ||
            appState.mode === "advanced";
        btnMain.style.display = show ? "inline-block" : "none";
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

    // hide BRAND / CANONICAL in idle
    const brandPanel = document.getElementById("brand_panel");
    if (brandPanel) brandPanel.style.display = "none";

    // show event log
    const out = document.getElementById("output");
    out.style.display = "block";
    renderEvents();
    const modeBox = document.getElementById("mode_controls");
    modeBox.innerHTML = `
        <button id="btn_advanced">⚙ Advanced</button>
    `;
    document.getElementById("btn_advanced")
        ?.addEventListener("click", enterAdvancedMode);
    return;
    }

    //show test button
    const btnTest = document.getElementById("btn_test");
    if (btnTest) btnTest.style.display = "block";

    const modeBox = document.getElementById("mode_controls");
    if (modeBox) modeBox.innerHTML = "";

    if (s === 1) { // supplier selected state
        lbl.innerText = "Active supplier: " + appState.activeSupplier;
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
        ex.innerText = appState.supplierExcluded
            ? "✅ Include in pivot"
            : "🚫 Exclude from pivot";

        moveBrandPanel("right");
        const brandPanel = document.getElementById("brand_panel");
        if (brandPanel) brandPanel.style.display = "none";

        renderEvents();
        return;
    }

    if (s === 2) {   // NODES VIEW
        lbl.innerText = "Nodes for: " + appState.activeSupplier;
        btnC.style.display = "block";
        rm.style.display   = "block";
        nd.style.display   = "block";
        df.style.display   = "block";

        dfoutBlock.style.display = "block";

        const out = document.getElementById("output");
        out.style.display = "block";

        // 🆕 BRAND PANEL — только в offers
        moveBrandPanel("right");
        const brandPanel = document.getElementById("brand_panel");
        if (brandPanel) {
            brandPanel.style.display =
                appState.viewMode === "offers" ? "block" : "none";
        }

        //manage suppliers
        const ex = document.getElementById("btn_toggle_excluded");
        ex.style.display = "block";
        ex.innerText = appState.supplierExcluded
            ? "✅ Include in pivot"
            : "🚫 Exclude from pivot";

        // OFFERS VIEW
        if (appState.viewMode === "offers") {
            out.innerHTML = appState.lastOffers
                .filter(o => o.type === "Offer")
                .map(o => renderOfferCard(o))
                .join("");
            return;
        }

    // Render NODES (separate pipeline)
    out.innerHTML = appState.lastNodes.map(n => {
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
            t === "dfout" && appState.canonicalIds.has(id);

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

        // === HIDE DFOUT OTHER TOOLS ===
        dfoutBlock.style.display = "none";

        // BRAND PANEL must be visible in editor (state 4)
        moveBrandPanel("right");
        const brandPanel = document.getElementById("brand_panel");
        if (brandPanel) brandPanel.style.display = "block";
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
