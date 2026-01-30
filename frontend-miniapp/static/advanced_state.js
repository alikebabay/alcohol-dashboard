// advanced_state.js
import { getLogger } from "./logger.js";
const log = getLogger("advanced_state");

import { renderOutput } from "./admin_editor.js";
import { mountDefaultSeriesPanel }
  from "./features/default_series/default_series_controller.js";

export function renderAdvancedState(appState, helpers) {
    log.info("renderAdvancedState");
    const { moveBrandPanel, exitAdvancedMode } = helpers;

    const lbl = document.getElementById("active_supplier");
    const out = document.getElementById("output");
    const adminPanel = document.getElementById("admin_panel");
    const brandPanel = document.getElementById("brand_panel");
    const dfoutBlock = document.getElementById("dfout_block");
    const testPanel  = document.getElementById("test_panel");
    const modeBox = document.getElementById("mode_controls");

    lbl.innerText = "ADVANCED MODE";

    if (adminPanel) adminPanel.style.display = "none";
    if (dfoutBlock) dfoutBlock.style.display = "none";
    if (testPanel)  testPanel.style.display = "none";

    moveBrandPanel("left");
    if (brandPanel) brandPanel.style.display = "block";

    out.style.display = "block";
    renderOutput();

    mountDefaultSeriesPanel();
    log.info("calling mountDefaultSeriesPanel");
    
    modeBox.innerHTML = `
        <button id="btn_back_default">← Back</button>
    `;
    document.getElementById("btn_back_default")
        ?.addEventListener("click", exitAdvancedMode);
}
