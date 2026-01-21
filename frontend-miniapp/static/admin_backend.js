//admin_backend.js

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

            state = 1;
            renderState();
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
async function api(path, method="GET", body=null, updateOutput=true) {
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






// =========================
// TEST MODE 
// =========================

async function runGraphTest() {
    const text = document.getElementById("test_input").value;

    if (!text.trim()) {
        showToast("No input text");
        return;
    }

    const out = document.getElementById("output");
    out.innerHTML = `<div class="event-item">▶ running graph test…</div>`;

    const res = await api(
        "/test/graph",
        "POST",
        { text },
        false
    );

    if (!res.ok) {
        out.innerText = res.error || "Test failed";
        return;
    }

    out.innerHTML = res.data.map(r => {
        if (!r.changed) {
            return `
                <div class="diff-row unchanged">
                    <div class="raw">${r.raw}</div>
                    <div class="unchanged">→ (no change)</div>
                </div>
            `;
        }

        return `
            <div class="diff-row changed">
                <div class="raw">${r.raw}</div>
                <div class="norm">→ ${r.norm}</div>
            </div>
        `;

    }).join("");
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
