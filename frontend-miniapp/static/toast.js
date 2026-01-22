// toast.js
export function showToast(msg) {
    const t = document.createElement("div");
    t.innerText = msg;

    t.style.position = "fixed";
    t.style.top = "20px";
    t.style.right = "20px";
    t.style.background = "black";
    t.style.color = "white";
    t.style.padding = "10px 16px";
    t.style.borderRadius = "6px";
    t.style.opacity = "0";
    t.style.transition = "opacity 0.25s ease";
    t.style.zIndex = 9999;

    document.body.appendChild(t);
    requestAnimationFrame(() => t.style.opacity = "1");

    setTimeout(() => {
        t.style.opacity = "0";
        setTimeout(() => t.remove(), 250);
    }, 900);
}



export function showToastAt(x, y, msg) {
    const t = document.createElement("div");
    t.innerText = msg;

    t.style.position = "fixed";
    t.style.left = (x + 12) + "px";   // смещение от курсора
    t.style.top  = (y + 12) + "px";

    t.style.background = "rgba(0,0,0,0.9)";
    t.style.color = "white";
    t.style.padding = "8px 14px";
    t.style.borderRadius = "6px";
    t.style.fontSize = "14px";
    t.style.zIndex = 99999;

    t.style.opacity = "0";
    t.style.transition = "opacity 0.2s ease, transform 0.2s ease";
    t.style.transform = "translateY(4px)";

    document.body.appendChild(t);

    requestAnimationFrame(() => {
        t.style.opacity = "1";
        t.style.transform = "translateY(0)";
    });

    setTimeout(() => {
        t.style.opacity = "0";
        t.style.transform = "translateY(4px)";
        setTimeout(() => t.remove(), 200);
    }, 900);
}
