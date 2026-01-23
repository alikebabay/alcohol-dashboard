// ============================================================
// Clipboard helper class (ES module)
// ============================================================
export class ClipboardHelper {
    static async copy(text) {
        try {
            // modern API (https or localhost)
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                return true;
            }

            // fallback for http / restricted envs
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();

            const ok = document.execCommand("copy");
            document.body.removeChild(ta);
            return ok;
        } catch (err) {
            console.error("Clipboard copy failed", err);
            return false;
        }
    }
}
