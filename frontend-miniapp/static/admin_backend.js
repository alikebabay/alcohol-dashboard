//admin_backend.js

import { resetState, renderState, appState } from "./admin_state.js";
import { logEvent } from "./events.js";
import {showToastAt } from "./toast.js";
import { enterEditor } from "./admin_editor.js";


//connection to api (backend handles mode)
const API_BASE = "/admin";

export async function api(path, method="GET", body=null, updateOutput=true) {
     let opts = { method, headers: {"Content-Type": "application/json"} };
     if (body) opts.body = JSON.stringify(body);

     const res = await fetch(API_BASE + path, opts);
     const data = await res.json().catch(()=>({error:"Invalid JSON"}));
     if (updateOutput)
         document.getElementById("output").innerText = JSON.stringify(data, null, 2);
     return data;
 }


//populates supplier dropdown
export async function loadSuppliers() {
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
        div.onclick = async () => {
            const prevSupplier = appState.activeSupplier;
            appState.activeSupplier = row.name;
            appState.supplierExcluded = !!row.admin_excluded;
            // 🧹 clear brand search when switching supplier
            appState.foundBrands = null;
            const box = document.getElementById("brand_result");
            if (box) box.innerHTML = "";

            // 🟢 SPECIAL CASE: editor state
            if (appState === 4 && prevSupplier !== row.name) {
                appState.lastNodes = [];
                appState.lastOffers = [];
                loadOffers();              // state = 2 внутри
                highlightActiveSupplier();
                return;
            }

            // 🟡 default behaviour → LOAD OFFERS
            if (prevSupplier !== row.name) {
                appState.lastNodes = [];
                appState.lastOffers = [];
                appState.viewMode = "offers";
                await loadOffers();   // sets state = 2 internally
                highlightActiveSupplier();
                return;
            }
            // fallback (same supplier clicked)
            renderState();
        };


        grid.appendChild(div);
    });

    highlightActiveSupplier();
}

function highlightActiveSupplier() {
    document.querySelectorAll(".supplier-item").forEach(el => {
        el.classList.toggle("active", el.innerText === appState.activeSupplier);
    });
}
//search for suppliers
export function wireSupplierSearch() {
    const input = document.getElementById("supplier_search");
    if (!input) return;

    input.addEventListener("input", () => {
        const q = input.value.toLowerCase();

        document.querySelectorAll(".supplier-item").forEach(el => {
            const name = el.innerText.toLowerCase();
            el.style.display = name.includes(q) ? "" : "none";
        });
    });
}

//manages suppliers
async function toggleExcluded() {
    if (!appState.activeSupplier) return;

    const newState = !appState.supplierExcluded;

    const res = await api(
        "/set_supplier_excluded",
        "POST",
        { supplier: appState.activeSupplier, excluded: newState },
        false
    );

    if (res?.error) {
        showToast("Failed to update supplier");
        logEvent("Supplier exclude toggle failed", "error");
        return;
    }

    appState.supplierExcluded = newState;

    showToast(
        newState
            ? "Supplier excluded from pivot"
            : "Supplier included in pivot"
    );

    logEvent(
       newState
           ? `Supplier excluded from pivot: ${appState.activeSupplier}`
           : `Supplier included in pivot: ${appState.activeSupplier}`,
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


function listSuppliers(){
    api("/list_suppliers", "GET");
}

async function removeSupplier(){
    if (!confirm("Remove supplier: " + appState.activeSupplier + " ?")) return;
    const res = await api("/remove_supplier", "POST", { name: appState.activeSupplier }, false);
    if (res?.error) {
        showToast("Remove failed");
        logEvent(`Remove supplier failed: ${appState.activeSupplier}`, "error");
        return;
    }
    showToast("Supplier removed");
    logEvent(`Supplier removed: ${appState.activeSupplier}`, "ok");
}

function findNodes() {
    loadNodes();
}

async function loadNodes() {
    appState.viewMode = "nodes";
    await loadCanonicals();
    const data = await api(
        "/find_nodes?supplier=" + encodeURIComponent(appState.activeSupplier),
        "GET",
        null,
        false
    );
    appState.lastNodes = data;
    appState.state = 2;
    renderState();
}

// loads supplier offers
export async function loadOffers() {
    const data = await api(
        "/list_offers?supplier=" + encodeURIComponent(appState.activeSupplier),
        "GET",
        null,
        false
    );
    appState.lastOffers = data;
    appState.viewMode = "offers";
    appState.state = 2;
    renderState();
}

//removes DFOUt, returns user to state 2
async function deleteDfOut() {
    const res = await api(
        "/delete_dfout",
        "POST",
        { supplier: appState.activeSupplier },
        false
    );

    if (res?.error) {
        showToast("DfOut delete failed");
        logEvent("DfOut delete failed", "error");
        return;
    }

    showToast("DfOut deleted");
    logEvent(`DfOut deleted for ${appState.activeSupplier}`, "ok");
    appState.state = 1;
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
    appState.state = 0;
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
        if (appState.viewMode === "offers") {
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
    appState.canonicalIds = new Set(Array.isArray(data) ? data : []);
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
