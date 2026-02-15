// /static/festures/edit_offer/offer_model.js

import { showToast } from "../../toast.js";
import { loadOffers } from "../../admin_backend.js";
import { renderState, appState} from "../../admin_state.js";
import { api } from "../../admin_backend.js";

function numOrNull(v) {
    if (v === "" || v == null) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}


export async function addOffer() {
    const name   = document.getElementById("edit_name")?.value.trim();
    const bottle = document.getElementById("edit_price_bottle")?.value;
    console.log("bottle raw =", bottle);
    console.log("bottle parsed =", numOrNull(bottle));

    const pack   = document.getElementById("edit_price_case")?.value;
    const curr   = document.getElementById("edit_currency")?.value;
    const bpcVal = document.getElementById("edit_bottles_per_case")?.value;
    const cl     = document.getElementById("edit_cl")?.value;
    const location = document.getElementById("edit_location")?.value;
    const access   = document.getElementById("edit_access")?.value;

    const payload = {
        supplier: appState.activeSupplier,
        name: name || null,
        price_bottle: numOrNull(bottle),
        price_case:   numOrNull(pack),
        currency: curr || null,
        bpc: bpcVal ? parseInt(bpcVal, 10) : null,
        cl: cl || null,
        location: location || null,
        access: access || null,
    };

    if (!payload.name) {
        showToast("Name required");
        return;
    }


    console.log("[addOffer] supplier =", appState.activeSupplier);
    console.log("[addOffer] payload =", payload);

    const res = await api("/offer/add", "POST", payload, false);

    console.log("[addOffer] response =", res);

    if (res?.error) {
        console.error("[addOffer] create failed:", res.error);
        showToast("Create failed");
        return;
    }

    showToast("Offer created");

    await loadOffers();

    appState.state = 1;
    appState.viewMode = "offers";
    renderState();
}



export async function updateOffer() {
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
        name: name || null,
        price_bottle: numOrNull(bottle),
        price_case:   numOrNull(pack),
        currency: curr || null,
        bpc: bpcVal ? parseInt(bpcVal, 10) : null,
        cl: cl || null,
        location: location || null,
        access: access || null,
    };

    const res = await api("/offer/update", "POST", payload, false);

    if (res?.error) {
        showToast("Save failed");
        return;
    }

    showToast("Offer updated");

    // reload offers → pivot stays consistent
    await loadOffers();
    renderState();
}



let lastEditedField = null;   // shared module state, used by calculator, etc

export function setLastEditedField(v) {
    lastEditedField = v;
}

//calculator
export function maybeRecalc() {
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
