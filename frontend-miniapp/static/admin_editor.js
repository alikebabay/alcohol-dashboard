//admin_editor.js

import { getLogger } from "./logger.js";
const log = getLogger("editor");


import { api} from "./admin_backend.js";
import { renderState, appState } from "./admin_state.js";
import { renderDefaultSeriesHTML } from "./features/default_series/default_series_view.js";
import { wireDefaultCanonicals } from "./features/default_series/default_series_controller.js";
import { showToastAt } from "./toast.js";
import {
  renderDeleteBrandButton,
  renderDeleteSeriesButton,
  renderDeleteCanonicalButton,
  renderDeleteBrandAliasButton
} from "./features/delete_buttons/delete_buttons_view.js";




export function enterEditor(offerId) {
    appState.activeOfferId = offerId;
    appState.editorOriginals = null;
    appState.state = 3;
    renderState();
}



async function findBrand() {
    const input = document.getElementById("brand_search");
    const q = input?.value.trim();
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

    // ✅ toast when not found (near Find button)
    if (!res?.found) {
        const btn = document.getElementById("btn_find_brand");
        if (btn) {
            const r = btn.getBoundingClientRect();
            showToastAt(r.left, r.top, res?.message || "brand not found");
        } else {
            // fallback
            showToastAt(20, 20, res?.message || "brand not found");
        }
    }

    // re-render output panel
    renderState();
}


//renders found brands, series, alias, canonicals
function wrapAdaptive(listHtml, count) {
  if (count <= 4) return listHtml;

  const cols = count > 12 ? 3 : 2;

  return `
    <div style="
      display:grid;
      grid-template-columns: repeat(${cols}, 1fr);
      gap:4px 14px;
      margin-top:2px;
    ">
      ${listHtml}
    </div>
  `;
}


export function renderFoundBrandsHTML(brands) {
  const deletable = (appState?.mode === "advanced"); // delete only in advanced mode
  const esc = (s) => (s ?? "").toString()
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");

  const joinAliases = (a) => Array.isArray(a) ? a.filter(Boolean).join(", ") : "";

  if (!Array.isArray(brands) || brands.length === 0) {
    return `<div style="opacity:.7;">brand not found</div>`;
  }

  return brands.map(b => {
    const brandName = b?.name ?? "";
    const brandAliases = joinAliases(b?.brand_alias);

    const series = Array.isArray(b?.series) ? b.series : [];
    const canonicals = Array.isArray(b?.canonicals) ? b.canonicals : [];

    const seriesHtml = series.length
      ? series.map(s => { 
          const sName = s?.name ?? "";
          const sAlias = joinAliases(s?.alias);
          
          return `
            <div style="margin:2px 0;">
              • <span data-copy="${esc(sName)}"
                        style="cursor:pointer; font-size:15px; font-weight:600; line-height:1.25;">
                    ${esc(sName)}
                </span>

              ${sAlias ? `<span style="opacity:.75; font-size:12.5px;"> (${esc(sAlias)})</span>` : ""}
              ${deletable ? renderDeleteSeriesButton(brandName, sName, esc) : ""}

            </div>
          `;
        }).join("")
      : `<div style="opacity:.6; font-size:12px;">—</div>`; 
       

    const canonHtml = canonicals.length
      ? canonicals.map(c => {
          // backend now returns {name:"..."} objects
          const cName = (typeof c === "string") ? c : (c?.name ?? "");
          return `
            <div style="margin:2px 0;">
                ${deletable ? renderDeleteCanonicalButton(cName, esc) : ""}

              • <span data-copy="${esc(cName)}"
                    style="cursor:pointer; font-size:14px; line-height:1.25;">
                ${esc(cName)}
            </span>

            </div>
          `;
        }).join("")
      : `<div style="opacity:.6; font-size:12px;">—</div>`;

    return `
      <div style="border:1px solid rgba(255,255,255,.12); padding:8px; border-radius:8px; margin:8px 0;">
        <div style="display:flex; gap:8px; align-items:center;">
          <div style="font-weight:700; font-size:18px; letter-spacing:0.2px;">
            ${esc(brandName)}
            </div>
          <button data-copy="${esc(brandName)}" style="margin-left:auto; font-size:11px; padding:2px 6px;">copy</button>
             ${deletable ? renderDeleteBrandButton(brandName, esc) : ""}

        </div>

         ${
           Array.isArray(b?.brand_alias) && b.brand_alias.length
             ? `<div style="opacity:.85; font-size:13px; margin-top:4px;">
                 aliases:
                 ${b.brand_alias.map(a => `
                   <span style="margin-right:6px;">
                     ${esc(a)}
                     ${deletable ? renderDeleteBrandAliasButton(brandName, a, esc) : ""}
                   </span>
                 `).join("")}
               </div>`
             : ""
         }
        <div style="margin-top:8px;">
          <div style="font-size:14px; font-weight:600; opacity:.9; margin-bottom:4px;">
                    Series
            </div>
          ${wrapAdaptive(seriesHtml, series.length)}
        </div>

        <div style="margin-top:8px;">
          <div style="font-size:14px; font-weight:600; opacity:.9; margin-bottom:4px;">
            Canonicals
            </div>
          ${wrapAdaptive(canonHtml, canonicals.length)}
        </div>
      </div>
    `;
  }).join("");
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
