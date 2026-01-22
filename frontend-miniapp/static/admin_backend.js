//admin_backend.js

import { resetState } from "./admin_state.js";
import { logEvent } from "./events.js";
import {showToastAt } from "./toast.js"

//connection to api
let API_BASE = null;



async function loadConfig() {
    try {
        const res = await fetch("/admin/config");
        const cfg = await res.json();
        API_BASE = cfg.api_base;
    } catch (e) {
        // fallback for FILE:// usage
        API_BASE = "http://localhost:8001/admin";
    }
}




//populates supplier dropdown
async function loadSuppliers() {
    const data = await api("/list_suppliers", "GET", null, false);
    const grid = document.getElementById("supplier_grid");

    grid.innerHTML = "";

    if (!Array.isArray(data)) {
        grid.innerHTML = "<div>Error loading suppliers</div>";
        return;
    }

    data.forEach(row => {
        const div = document.createElement("div");
        div.className = "supplier-item";
        div.innerText = row.name + (row.admin_excluded ? " 🚫" : "");
        //reloads supplier data on active supplier switch
        div.onclick = () => {
            const prevSupplier = activeSupplier;
            activeSupplier = row.name;
            supplierExcluded = !!row.admin_excluded;

            // 🟢 SPECIAL CASE: editor state
            if (state === 4 && prevSupplier !== row.name) {
                lastNodes = [];
                lastOffers = [];
                loadOffers();              // state = 2 внутри
                highlightActiveSupplier();
                return;
            }

            // 🟡 default behaviour
            if (prevSupplier !== row.name) {
                lastNodes = [];
                lastOffers = [];
                viewMode = "nodes";
            }

            viewMode = "nodes";
            loadNodes();              // ⬅️ this sets state = 2 internally
            highlightActiveSupplier();
        };


        grid.appendChild(div);
    });

    highlightActiveSupplier();
}

function highlightActiveSupplier() {
    document.querySelectorAll(".supplier-item").forEach(el => {
        el.classList.toggle("active", el.innerText === activeSupplier);
    });
}

//manages suppliers
async function toggleExcluded() {
    if (!activeSupplier) return;

    const newState = !supplierExcluded;

    const res = await api(
        "/set_supplier_excluded",
        "POST",
        { supplier: activeSupplier, excluded: newState },
        false
    );

    if (res?.error) {
        showToast("Failed to update supplier");
        logEvent("Supplier exclude toggle failed", "error");
        return;
    }

    supplierExcluded = newState;

    showToast(
        newState
            ? "Supplier excluded from pivot"
            : "Supplier included in pivot"
    );

    logEvent(
       newState
           ? `Supplier excluded from pivot: ${activeSupplier}`
           : `Supplier included in pivot: ${activeSupplier}`,
       "ok"
   );

    await loadSuppliers();   // refresh 🚫 badge
    renderState();
}





async function rebuildSheets() {
    if (!confirm("Rebuild Google Sheets master?")) return;

    showToast("Rebuilding sheets…");
    logEvent("Rebuild sheets started");

    const res = await api("/rebuild_sheets", "POST", null, false);

    if (res?.error) {
        showToast("Rebuild failed");
        logEvent("Rebuild failed", "error");
        return;
    }

    showToast("Sheets rebuilt");
    logEvent(`Sheets rebuilt (${res.rows || "?"} rows)`, "ok");
}


// backend calls
export async function api(path, method="GET", body=null, updateOutput=true) {
    let opts = { method, headers: {"Content-Type": "application/json"} };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(API_BASE + path, opts);
    const data = await res.json().catch(()=>({error:"Invalid JSON"}));
    if (updateOutput)
        document.getElementById("output").innerText = JSON.stringify(data, null, 2);
    return data;
}

function listSuppliers(){
    api("/list_suppliers", "GET");
}

async function removeSupplier(){
    if (!confirm("Remove supplier: " + activeSupplier + " ?")) return;
    const res = await api("/remove_supplier", "POST", { name: activeSupplier }, false);
    if (res?.error) {
        showToast("Remove failed");
        logEvent(`Remove supplier failed: ${activeSupplier}`, "error");
        return;
    }
    showToast("Supplier removed");
    logEvent(`Supplier removed: ${activeSupplier}`, "ok");
}

function findNodes() {
    loadNodes();
}

async function loadNodes() {
    viewMode = "nodes";
    await loadCanonicals();
    const data = await api(
        "/find_nodes?supplier=" + encodeURIComponent(activeSupplier),
        "GET",
        null,
        false
    );
    lastNodes = data;
    state = 2;
    renderState();
}

// loads supplier offers
async function loadOffers() {
    const data = await api(
        "/list_offers?supplier=" + encodeURIComponent(activeSupplier),
        "GET",
        null,
        false
    );
    lastOffers = data;
    viewMode = "offers";
    state = 2;
    renderState();
}

//removes DFOUt, returns user to state 2
async function deleteDfOut() {
    const res = await api(
        "/delete_dfout",
        "POST",
        { supplier: activeSupplier },
        false
    );

    if (res?.error) {
        showToast("DfOut delete failed");
        logEvent("DfOut delete failed", "error");
        return;
    }

    showToast("DfOut deleted");
    logEvent(`DfOut deleted for ${activeSupplier}`, "ok");
    state = 1;
    renderState();

    // Load nodes immediately → switches state to 2 inside loadNodes()
    await loadNodes();
}

//removes nodes by provided id
async function deleteById() {
    console.log("DELETE: function entered");
    const id = document.getElementById("dfout_id").value.trim();
    console.log("DELETE: id =", id);
    if (!id) return;
    if (!confirm("Delete node?\n" + id)) return;

    const res = await api("/delete_node", "POST", { id }, false);

    if (res?.error) {
        showToast("Delete failed");
        logEvent(`Delete failed: ${id}`, "error");
        return;
    }

    showToast("Node deleted");
    logEvent(`Node deleted: ${id}`, "ok"); // сохранит в EventStore
    state = 0;
    renderState(); // state 0 -> renderEvents() покажет
}

//deletes nodes on click
export function wireNodeDeleteHandler() {
    document.addEventListener("click", async (e) => {
        const btn = e.target.closest(".node-delete");
        if (!btn) return;

        const card = btn.closest("[data-id]");
        if (!card) return;

        const id = card.dataset.id;
        if (!id) return;

        if (!confirm("Delete node?\n" + id)) return;

        const res = await api("/delete_node", "POST", { id }, false);

        if (res?.error) {
            showToastAt(lastMouse.x, lastMouse.y, "Delete failed");
            logEvent(`Delete failed: ${id}`, "error");
            return;
        }

        // ✅ always log
        logEvent(`Node deleted: ${id}`, "ok");

        // ✅ toast near mouse
        showToastAt(lastMouse.x, lastMouse.y, "Node deleted");

        // ✅ reload current view
        if (viewMode === "offers") {
            await loadOffers();
        } else {
            await loadNodes();
        }
    });
}


async function markCanonical(){
    const id = document.getElementById("dfout_id").value.trim();
    const res = await api("/mark_canonical", "POST", { id }, false);
    if (res?.error) {
        showToast("Mark canonical failed");
        logEvent(`Mark canonical failed: ${id}`, "error");
        return;
    }
    showToast("Marked as canonical");
    logEvent(`Marked canonical: ${id}`, "ok");
}

async function loadCanonicals() {
    const data = await api("/list_canonicals", "GET", null, false);
    canonicalIds = new Set(Array.isArray(data) ? data : []);
}



//opens pivot table
async function openPivot() {
    const res = await api("/pivot", "GET", null, false);
    if (!res?.url) {
        showToast("Pivot not available");
        return;
    }
    window.open(res.url, "_blank");
}


// expose to window for legacy code
window.loadConfig = loadConfig;
window.loadSuppliers = loadSuppliers;
window.loadOffers = loadOffers;

export function wireOfferButtons() {
    const offers = document.getElementById("btn_offers");
    const nodes  = document.getElementById("btn_nodes");

    if (offers) offers.addEventListener("click", loadOffers);
    if (nodes)  nodes.addEventListener("click", loadNodes);
}

export function wireSupplierMenu() {
    const pivot = document.getElementById("btn_pivot");
    if (pivot) pivot.addEventListener("click", openPivot);

    const change = document.getElementById("btn_change_supplier");
    if (change) change.addEventListener("click", resetState);

    const toggle = document.getElementById("btn_toggle_excluded");
    if (toggle) toggle.addEventListener("click", toggleExcluded);

    const rebuild = document.getElementById("btn_rebuild_sheets");
    if (rebuild) rebuild.addEventListener("click", rebuildSheets);

    const reload = document.getElementById("btn_reload_suppliers");
    if (reload) reload.addEventListener("click", loadSuppliers);

    const remove = document.getElementById("btn_remove");
    if (remove) remove.addEventListener("click", removeSupplier);

    const dfout = document.getElementById("btn_dfout");
    if (dfout) dfout.addEventListener("click", deleteDfOut);
}


export function wireAdminActions() {
    document.getElementById("btn_mark_canonical")
        ?.addEventListener("click", markCanonical);
}

export function wireOfferEditHandler() {
    document.addEventListener("click", e => {
        const btn = e.target.closest(".offer-edit");
        if (!btn) return;

        const card = btn.closest(".offer-card");
        if (!card) return;

        const id = card.dataset.id;
        if (!id) return;

        enterEditor(id);
    });
}
