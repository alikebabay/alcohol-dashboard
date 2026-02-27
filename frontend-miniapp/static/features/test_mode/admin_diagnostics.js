import { graphTest } from "./diagnostics_model.js";
import { getTestInputText, renderRunning, renderGraphDiff, renderError } from "./diagnostics_view.js";

export async function runGraphTest() {
  const text = getTestInputText();

  if (!text.trim()) {
    showToast("No input text");
    return;
  }

  renderRunning();

  try {
    const result = await graphTest(text);
    renderGraphDiff(result.rows, result.logs);
  } catch (e) {
    renderError(e?.message);
  }
}

export function testGBX() {
  showToast("GBX test not implemented yet");
}

export function testPrice() {
  showToast("Price test not implemented yet");
}