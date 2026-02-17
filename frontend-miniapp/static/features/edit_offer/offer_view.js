
//renders offer editing space
///static/festures/edit_offer/offer_view.js
import {updateOffer, maybeRecalc, setLastEditedField, addOffer} from "./offer_model.js"
import {exitEditor} from "./offer_controller.js"
import { appState, renderState } from "../../admin_state.js";
import { api } from "../../admin_backend.js";



function onEditCase() {
    setLastEditedField("case");
    maybeRecalc();
}

function onEditBottle() {
    setLastEditedField("bottle");
    maybeRecalc();
}

function onEditBPC() {
    maybeRecalc();
}


//search functions
function getActiveOffer() {
    return appState.lastOffers.find(o => o.id === appState.activeOfferId) || null;
}

//loads originals for supplier offers

export function wireEditorOriginals() {
    document.addEventListener("click", (e) => {
        const btn = e.target.closest("#btn_editor_originals");
        if (!btn) return;

        loadEditorOriginals();
    });
}



export async function loadEditorOriginals() {
    if (appState.editorOriginals !== null) return; // already loaded

    appState.editorOriginals = [];
    const res = appState.activeOfferId
    ? await api(`/editor/original_rows?offer_id=${appState.activeOfferId}`, "GET", null, false)
    : await api(`/editor/df_raw?supplier=${appState.activeSupplier}`, "GET", null, false);

    if (res?.rows) {
        appState.editorOriginals = res.rows.slice(0, 10);
    }

    renderOfferEditor();
}

export function renderOfferEditor() {
    const offer = getActiveOffer();
    const out = document.getElementById("editor_offer_editor");
    const isCreate = !appState.activeOfferId;

    const priceBottle = offer?.price_bottle ?? "";
    const priceCase   = offer?.price_case ?? "";
    const cl          = offer?.cl ?? "";
    const currency    = offer?.currency ?? "";
    const location    = offer?.location ?? "";
    const access      = offer?.access ?? "";

    let originalsBlock = `
        <button id="btn_editor_originals">
            📄 Show original rows
        </button>
    `;

    if (appState.editorOriginals !== null) {
        originalsBlock = `
            <div class="editor-originals">
                    ${appState.editorOriginals.map(r => {
                        const parts = r.raw.split("|").map(s => s.trim());
                        const head = parts[0] || r.raw;
                        const tail = parts.slice(1).join(" | ");
                        return `
                            <div class="editor-original-row"
                                 data-copy=${JSON.stringify(r.raw)}>
                                <strong>${head}</strong>
                                ${tail ? `<div class="muted">${tail}</div>` : ``}
                            </div>
                        `;
                    }).join("")}
                </div>
        `;
    }

    out.innerHTML = `
        <div class="editor-card editor-card-split">
            <div class="editor-left-pane">
                <h3>${isCreate ? "➕ Create offer" : "✏️ Edit price"}</h3>

            <div class="editor-section">
                ${!isCreate ? `
                <div style="opacity:0.6; font-size:12px">
                    Offer ID:
                    <code>${appState.activeOfferId}</code>
                </div>
                <button
                    data-copy="${appState.activeOfferId}"
                    style="font-size:11px; padding:2px 6px"
                >📋 Copy</button>
                ` : ""}
                <div style="opacity:0.6; font-size:12px; margin-top:2px">
                    Supplier: <b>${appState.activeSupplier}</b>
                </div>
                <div style="margin-top:6px">
                    <b>${offer?.name || ""}</b>
                </div>
            </div>

            <!-- CURRENT STATE -->
            <div class="editor-section editor-current">
               <div style="opacity:0.7; margin-bottom:6px">
                   <b>Current values</b>
               </div>
               <div style="opacity:0.6">
                    Supplier: ${appState.activeSupplier}
               </div>
               <div>
                   Bottle:
                   <b>${priceBottle ? priceBottle : "—"}</b>
                   ${currency || ""}
               </div>
               <div>
                   Case:
                   <b>${priceCase ? priceCase : "—"}</b>
                   ${currency || ""}
               </div>
               <div>
                   Currency:
                   <b>${currency || "—"}</b>
               </div>
            </div>
            <hr />
            <div class="editor-section">
                <label>
                    Name <br/>
                    <input id="edit_name"
                           type="text"
                           value="${offer?.name ?? ""}">
                </label>
            </div>

            <div class="editor-section">
                <label>
                    Bottle price<br/>
                    <input id="edit_price_bottle"
                           type="number"
                           step="0.0001"
                           value="${priceBottle}">
                </label>
            </div>

            <div class="editor-section">
                <label>
                    Case price<br/>
                    <input id="edit_price_case"
                           type="number"
                           step="0.0001"
                           value="${priceCase}">
                </label>
            </div>

            <div class="editor-section">
                <label>
                    Bottles per case<br/>
                    <input id="edit_bottles_per_case"
                           type="number"
                           step="1"
                           min="1"
                           value="${offer?.bottles_per_case ?? ""}">
                </label>
            </div>
            <div class="editor-section">
                <label>
                    CL<br/>
                    <input id="edit_cl"
                           type="text"
                           value="${cl}">
                </label>
            </div>

            <div class="editor-section">
                <label>
                    Currency<br/>
                    <input id="edit_currency"
                           type="text"
                           value="${currency}">
                </label>
            </div>

            <div class="editor-section">
                <label>
                    Location<br/>
                    <input id="edit_location"
                           type="text"
                           value="${location}">
                </label>
            </div>
            <div class="editor-section">
                <label>
                    Access<br/>
                    <input id="edit_access"
                           type="text"
                           value="${access}">
                </label>
            </div>

            <div class="editor-actions">
                <button id="btn_editor_save">💾 Save</button>
                <button id="btn_editor_cancel">✖ Cancel</button>
            </div>

        </div>
            <div class="editor-right-pane">
                <div style="opacity:0.7; margin-bottom:6px">
                    <b>Original rows</b>
                </div>
                ${originalsBlock}
            </div>

        </div>
    `;

    // --- wire editor inputs ---
    const bottleInput = document.getElementById("edit_price_bottle");
    if (bottleInput) {
        bottleInput.addEventListener("input", onEditBottle);
    }

    const caseInput = document.getElementById("edit_price_case");
    if (caseInput) {
        caseInput.addEventListener("input", onEditCase);
    }

    const bpcInput = document.getElementById("edit_bottles_per_case");
    if (bpcInput) {
        bpcInput.addEventListener("input", onEditBPC);
    }
    
    const btnCancel = document.getElementById("btn_editor_cancel");
    if (btnCancel) {
        btnCancel.addEventListener("click", exitEditor);
    }
}

export function wireOfferEditorGlobal() {
    document.addEventListener("click", (e) => {

        if (e.target.closest("#btn_add_offer")) {
            appState.activeOfferId = null;
            appState.editorOriginals = null;
            appState.state = 3;
            renderState();
        }

        if (e.target.closest("#btn_editor_save")) {
            if (appState.activeOfferId)
                updateOffer();
            else
                addOffer();
        }
    });
}


//layout for offer editor
function renderOfferList() {
    const box = document.getElementById("editor_offer_list");

    box.innerHTML = appState.lastOffers.map(o => `
        <div
            class="editor-offer-item ${o.id === appState.activeOfferId ? "active" : ""}"
            data-offer-id="${o.id}"
        >
            <div class="name">${o.name}</div>
            <div class="price">
                ${o.price_case ?? "—"} ${o.currency ?? ""}
            </div>
        </div>
    `).join("");
}


export function renderEditorLayout() {
    const out = document.getElementById("output");

    out.innerHTML = `
        <div class="editor-layout">
            <div class="editor-left" id="editor_offer_list"></div>
            <div class="editor-right" id="editor_offer_editor"></div>
        </div>

        <div class="editor-footer">
            <button class="menu-item danger" id="btn_editor_exit">
                ← Return to main menu
            </button>
        </div>
    `;

    renderOfferList();
    renderOfferEditor();
     document.getElementById("btn_editor_exit")
        ?.addEventListener("click", exitEditor);
}




//wiring
export function wireEditorOfferList() {
    document.addEventListener("click", (e) => {
        const item = e.target.closest(".editor-offer-item");
        if (!item) return;

        const id = item.dataset.offerId;
        if (!id) return;

        selectEditorOffer(id);
    });
}



function selectEditorOffer(offerId) {
    appState.activeOfferId = offerId;
    appState.editorOriginals = null;
    renderOfferList();     // подсветка
    renderOfferEditor();   // обновляем правую панель
}
