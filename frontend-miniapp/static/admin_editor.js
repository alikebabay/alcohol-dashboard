//admin_editor.js

function enterEditor(offerId) {
    activeOfferId = offerId;
    editorOriginals = null;
    state = 4;
    renderState();
}


function getActiveOffer() {
    return lastOffers.find(o => o.id === activeOfferId) || null;
}

//loads originals for supplier offers
async function loadEditorOriginals() {
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
        <button onclick="loadEditorOriginals()">
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
                                onclick="
                                    navigator.clipboard.writeText(${JSON.stringify(r.raw)});
                                    showToast('Original row copied');
                                ">
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
                    style="font-size:11px; padding:2px 6px"
                    onclick="
                        navigator.clipboard.writeText('${activeOfferId}');
                        showToast('Offer ID copied');
                    "
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
                <button onclick="saveOfferPrice()">💾 Save</button>
                <button onclick="exitEditor()">✖ Cancel</button>
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
}

//layout for offer editor
function renderOfferList() {
    const box = document.getElementById("editor_offer_list");

    box.innerHTML = lastOffers.map(o => `
        <div class="editor-offer-item
                    ${o.id === activeOfferId ? "active" : ""}"
             onclick="selectEditorOffer('${o.id}')">
            <div class="name">${o.name}</div>
            <div class="price">
                ${o.price_case ?? "—"} ${o.currency ?? ""}
            </div>
        </div>
    `).join("");
}


function renderEditorLayout() {
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


async function saveOfferPrice() {
    const bottle = document.getElementById("edit_price_bottle").value;
    const pack   = document.getElementById("edit_price_case").value;
    const curr   = document.getElementById("edit_currency").value;
    const bpcVal = document.getElementById("edit_bottles_per_case")?.value;

    const payload = {
        id: activeOfferId,
        price_bottle: bottle === "" ? null : Number(bottle),
        price_case:   pack   === "" ? null : Number(pack),
        currency:     curr   === "" ? null : curr,
        bpc: bpcVal === "" || bpcVal == null ? null : parseInt(bpcVal, 10)
    };

    const res = await api("/offer/price", "POST", payload, false);

    if (res?.error) {
        showToast("Save failed");
        return;
    }

    showToast("Price updated");

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
