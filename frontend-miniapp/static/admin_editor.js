//admin_editor.js

import { api } from "./admin_backend.js";

function enterEditor(offerId) {
    activeOfferId = offerId;
    editorOriginals = null;
    state = 4;
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
    return lastOffers.find(o => o.id === activeOfferId) || null;
}

//loads originals for supplier offers
export async function loadEditorOriginals() {
    if (editorOriginals !== null) return; // already loaded

    editorOriginals = [];
    const res = await api(
        `/editor/original_rows?offer_id=${activeOfferId}`,
        "GET",
        null,
        false
    );

    if (res?.rows) {
        editorOriginals = res.rows.slice(0, 10);
    }

    renderOfferEditor();
}

async function findBrand() {
    const q = document.getElementById("brand_search").value.trim();
    const out = document.getElementById("brand_result");

    if (!q) {
        out.innerHTML = "<em>Enter brand name</em>";
        return;
    }

    out.innerHTML = "Searching…";

    const res = await api(
        "/find_brand?name=" + encodeURIComponent(q),
        "GET",
        null,
        false
    );
    if (!res || !res.found) {
        out.innerHTML = "<em>Brand not found</em>";
        return;
    }
     out.innerHTML = res.brands.map(b => `
        <div style="padding:6px 0; border-bottom:1px dashed #444">
            <b>${b.name}</b>

            ${b.brand_alias && b.brand_alias.length
                ? `<div style="opacity:0.7">
                    aliases: ${b.brand_alias.join(", ")}
                   </div>`
                : ""}

            ${b.canonicals && b.canonicals.length
                ? `<div style="margin-top:4px; padding-left:10px; font-size:12px;">
                    ${b.canonicals
                        .map(c => `• ${c.name}`)
                        .join("<br>")}
                   </div>`
                : `<div style="opacity:0.5; font-size:12px; padding-left:10px;">
                    no canonicals
                   </div>`
            }
        </div>
    `).join("");
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
    const currency    = offer.currency ?? "";
    let originalsBlock = `
        <button id="btn_editor_originals">
            📄 Show original rows
        </button>
    `;

    if (editorOriginals !== null) {
        originalsBlock = `
            <div class="editor-originals">
                    ${editorOriginals.map(r => {
                        const parts = r.raw.split("|").map(s => s.trim());
                        const head = parts[0] || r.raw;
                        const tail = parts.slice(1).join(" | ");
                        return `
                            <div class="editor-original-row"
                                 data-raw=${JSON.stringify(r.raw)}>
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
                <code id="editor_offer_id">${activeOfferId}</code>
                <button
                    id="btn_copy_offer_id"
                    style="font-size:11px; padding:2px 6px"
                >📋 Copy</button>
                </div>
                <div style="opacity:0.6; font-size:12px; margin-top:2px">
                    Supplier: <b>${activeSupplier}</b>
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
                    Supplier: ${activeSupplier}
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
                    Currency<br/>
                    <input id="edit_currency"
                           type="text"
                           value="${currency}">
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
    // --- wire copy Offer ID ---
    const btnCopy = document.getElementById("btn_copy_offer_id");
    if (btnCopy) {
        btnCopy.onclick = () => {
            navigator.clipboard.writeText(activeOfferId);
            showToast("Offer ID copied");
        };
    }

    // --- wire original rows copy ---
    document.querySelectorAll(".editor-original-row").forEach(el => {
        el.onclick = () => {
            navigator.clipboard.writeText(el.dataset.raw);
            showToast("Original row copied");
        };
    });
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

    box.innerHTML = lastOffers.map(o => `
        <div
            class="editor-offer-item ${o.id === activeOfferId ? "active" : ""}"
            data-offer-id="${o.id}"
        >
            <div class="name">${o.name}</div>
            <div class="price">
                ${o.price_case ?? "—"} ${o.currency ?? ""}
            </div>
        </div>
    `).join("");
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
            <button class="menu-item danger"
                    onclick="state=0; activeOfferId=null; renderState()">
                ← Return to main menu
            </button>
        </div>
    `;

    renderOfferList();
    renderOfferEditor();
}


function selectEditorOffer(offerId) {
    activeOfferId = offerId;
    editorOriginals = null;
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

    const payload = {
        id: activeOfferId,
        name: name === "" ? null : name,
        price_bottle: bottle === "" ? null : Number(bottle),
        price_case:   pack   === "" ? null : Number(pack),
        currency:     curr   === "" ? null : curr,
        bpc: bpcVal === "" || bpcVal == null ? null : parseInt(bpcVal, 10)
    };

    const res = await api("/offer", "POST", payload, false);

    if (res?.error) {
        showToast("Save failed");
        return;
    }

    showToast("Offer updated");

    // reload offers → pivot stays consistent
    await loadOffers();

    state = 2;
    renderState();
}

function exitEditor() {
    activeOfferId = null;
    editorOriginals = null;
    state = 2;
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

//wiring buttons from admin.html

export function wireCanonical() {
    document.getElementById("btn_find_brand")
        ?.addEventListener("click", findBrand);
    document.getElementById("btn_add_canonical")
        ?.addEventListener("click", addCanonicalFromUI);
}

// expose to window for legacy code
window.enterEditor = enterEditor