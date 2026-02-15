//renders offer editing space
///static/festures/edit_offer/offer_view.js
import { appState } from "../../admin_state.js";
import { renderState } from "../../admin_state.js";



export function exitEditor() {
    appState.activeOfferId = null;
    appState.editorOriginals = null;
    appState.state = 1;
    appState.viewMode = "offers";
    renderState();
}

 