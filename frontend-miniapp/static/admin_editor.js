//admin_editor.js

import { getLogger } from "./logger.js";
const log = getLogger("editor");


import { api} from "./admin_backend.js";
import { renderState, appState } from "./admin_state.js";
import { loadOffers } from "./admin_backend.js";
import { renderDefaultSeriesHTML } from "./features/default_series/default_series_view.js";
import { wireDefaultCanonicals } from "./features/default_series/default_series_controller.js";



export function enterEditor(offerId) {
    appState.activeOfferId = offerId;
    appState.editorOriginals = null;
    appState.state = 4;
    renderState();
}


//global state for calculator
let lastEditedField = null; // "case" | "bottle" | null
//calculator
function maybeRecalc() {
    const caseEl = document.getElementById("edit_price_case");
    const bottleEl = document.getElementById("edit_price_bottle");
    const bpcEl = document.getElementById("edit_bottles_per_case");

    if (!caseEl || !bottleEl || !bpcEl) return;

    const casePrice = parseFloat(caseEl.value);
    const bottlePrice = parseFloat(bottleEl.value);
    const bpc = parseInt(bpcEl.value, 10);

    if (!bpc || bpc <= 0) return;

    // ─────────────────────────────
    // CASE 1: пользователь правит CASE
    // ─────────────────────────────
    if (lastEditedField === "case" && casePrice) {
        bottleEl.value = (casePrice / bpc).toFixed(4);
        return;
    }

    // ─────────────────────────────
    // CASE 2: пользователь правит BOTTLE
    // ─────────────────────────────
    if (lastEditedField === "bottle" && bottlePrice) {
        caseEl.value = (bottlePrice * bpc).toFixed(2);
        return;
    }

    // ─────────────────────────────
    // CASE 3: BPC изменился, но пользователь ничего не правил
    // ─────────────────────────────
    // 👉 НИЧЕГО НЕ ДЕЛАЕМ
}

function onEditCase() {
    lastEditedField = "case";
    maybeRecalc();
}

function onEditBottle() {
    lastEditedField = "bottle";
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
export async function loadEditorOriginals() {
    if (appState.editorOriginals !== null) return; // already loaded

    appState.editorOriginals = [];
    const res = await api(
        `/editor/original_rows?offer_id=${appState.activeOfferId}`,
        "GET",
        null,
        false
    );

    if (res?.rows) {
        appState.editorOriginals = res.rows.slice(0, 10);
    }

    renderOfferEditor();
}

async function findBrand() {
    const q = document.getElementById("brand_search").value.trim();
    if (!q) return;

    const res = await api(
        "/find_brand?name=" + encodeURIComponent(q),
        "GET",
        null,
        false
    );

    // overwrite previous search (so old one disappears)
    appState.foundBrands = res?.found ? res.brands : null;
    log.info("findBrand result", appState.foundBrands?.map(b => b.name));

    // re-render output panel
    renderState();
}



//renders offer editing space
function renderOfferEditor() {
    const offer = getActiveOffer();
    const out = document.getElementById("editor_offer_editor");

    if (!offer) {
        out.innerHTML = "<em>Offer not found</em>";
        return;
    }

    const priceBottle = offer.price_bottle ?? "";
    const priceCase   = offer.price_case ?? "";
    const cl   = offer.cl ?? "";
    const currency    = offer.currency ?? "";
    const location    = offer.location ?? "";
    const access    = offer.access ?? "";
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
                <h3>✏️ Edit price</h3>

            <div class="editor-section">
                <div style="opacity:0.6; font-size:12px">
                    Offer ID:
                    <code>${appState.activeOfferId}</code>
                </div>
                <button
                    data-copy="${appState.activeOfferId}"
                    style="font-size:11px; padding:2px 6px"
                >📋 Copy</button>
                <div style="opacity:0.6; font-size:12px; margin-top:2px">
                    Supplier: <b>${appState.activeSupplier}</b>
                </div>
                <div style="margin-top:6px">
                    <b>${offer.name || ""}</b>
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
                           value="${offer.name ?? ""}">
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
                           value="${offer.bottles_per_case ?? ""}">
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
    // --- wire editor action buttons ---
    const btnSave = document.getElementById("btn_editor_save");
    if (btnSave) {
        btnSave.addEventListener("click", saveOffer);
    }

    const btnCancel = document.getElementById("btn_editor_cancel");
    if (btnCancel) {
        btnCancel.addEventListener("click", exitEditor);
    }
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

function renderFoundBrandsHTML(brands) {
    return brands.map(b => `
        <div style="padding:6px 0; border-bottom:1px dashed #444">
            <b style="font-size:32px;">${b.name}</b>

            ${b.canonicals?.length
                ? `<div style="margin-top:4px; padding-left:10px; font-size:22px;">
                    ${b.canonicals.map(c => `• ${c.name}`).join("<br>")}
                   </div>`
                : `<div style="opacity:0.5; font-size:14px; padding-left:10px;">
                    no canonicals
                   </div>`
            }
        </div>
    `).join("");
}


export function renderSearchResult() {
    log.trace("renderSearchResult", {
        mode: appState.mode,
        found: appState.foundBrands?.map(b => b.name)
    });
    // рендер поиска ТОЛЬКО в default mode
    if (appState.mode !== "default") {
        log.debug("renderSearchResult skipped (not default mode)");
        return;
    }
    const out = document.getElementById("brand_result");
    if (!out) {
            log.warn("brand_result not found")
            return;
    }

     if (!appState.foundBrands) {
        log.debug("no foundBrands → clear brand_result");
         out.innerHTML = "";
         return;
     }
     log.info("render brand_result", appState.foundBrands.map(b => b.name));
     out.innerHTML = renderFoundBrandsHTML(appState.foundBrands);
}

export async function renderOutput() {
    const out = document.getElementById("output");
    let html = "";

    if (appState.foundBrands) {
        html += renderFoundBrandsHTML(appState.foundBrands);
        html += "<hr>";
    }

    html += `<h3 class="default-title">Default canonicals</h3>`;
    out.innerHTML = html;

    // mount point for this feature
    const container = out;
    container.innerHTML += await renderDefaultSeriesHTML();
    wireDefaultCanonicals(container);
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

export function wireEditorOriginals() {
    document.addEventListener("click", (e) => {
        const btn = e.target.closest("#btn_editor_originals");
        if (!btn) return;

        loadEditorOriginals();
    });
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


function selectEditorOffer(offerId) {
    appState.activeOfferId = offerId;
    appState.editorOriginals = null;
    renderOfferList();     // подсветка
    renderOfferEditor();   // обновляем правую панель
}

//функции редактирования
async function saveOffer() {
    const name   = document.getElementById("edit_name")?.value.trim();
    const bottle = document.getElementById("edit_price_bottle").value;
    const pack   = document.getElementById("edit_price_case").value;
    const curr   = document.getElementById("edit_currency").value;
    const bpcVal = document.getElementById("edit_bottles_per_case")?.value;
    const cl = document.getElementById("edit_cl").value;
    const location = document.getElementById("edit_location").value;
    const access = document.getElementById("edit_access").value;

    const payload = {
        id: appState.activeOfferId,
        name: name === "" ? null : name,
        price_bottle: bottle === "" ? null : Number(bottle),
        price_case:   pack   === "" ? null : Number(pack),
        currency:     curr   === "" ? null : curr,
        bpc: bpcVal === "" || bpcVal == null ? null : parseInt(bpcVal, 10),
        cl: cl === "" ? null : cl,
        location: location === "" ? null : location,
        access: access === "" ? null : access,
    };

    const res = await api("/offer", "POST", payload, false);

    if (res?.error) {
        showToast("Save failed");
        return;
    }

    showToast("Offer updated");

    // reload offers → pivot stays consistent
    await loadOffers();

    appState.state = 2;
    renderState();
}

function exitEditor() {
    appState.activeOfferId = null;
    appState.editorOriginals = null;
    appState.state = 2;
    renderState();
}



async function addCanonicalFromUI() {
    const brand = document.getElementById("canon_brand")?.value.trim();
    const canonical = document.getElementById("canon_name")?.value.trim();
    const series = document.getElementById("canon_series")?.value.trim();
    const category = document.getElementById("canon_category")?.value.trim();
    const brandAliasRaw = document.getElementById("brand_alias")?.value.trim();
    const seriesAliasRaw = document.getElementById("series_alias")?.value.trim();


    if (!brand || !canonical) {
        showToast("Brand and Canonical name are required");
        return;
    }

    const brand_alias = brandAliasRaw
        ? brandAliasRaw.split(",").map(s => s.trim()).filter(Boolean)
        : null;

    const series_alias = seriesAliasRaw
        ? seriesAliasRaw.split(",").map(s => s.trim()).filter(Boolean)
        : null;

    const payload = {
        brand,
        canonical_name: canonical,
        series: series || null,
        category: category || null,
        brand_alias: brand_alias,
        series_alias: series_alias,
    };

    const res = await api(
        "/editor/addcanonical",
        "POST",
        payload,
        false
    );

    if (res?.error) {
        showToast("Failed to create canonical");
        return;
    }

    showToast("Canonical created");
}

//download node

//event handler for download button
export function initDownloadHandler() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".node-download");
    if (!btn) return;

    const node = btn.closest(".node-item");
    const id = node?.dataset?.id;
    if (!id) return;

    window.location.href = `/admin/download/${id}`;
  });
}


//wiring buttons from admin.html

export function wireCanonical() {
    document.getElementById("btn_find_brand")
        ?.addEventListener("click", findBrand);
    document.getElementById("btn_add_canonical")
        ?.addEventListener("click", addCanonicalFromUI);
}
