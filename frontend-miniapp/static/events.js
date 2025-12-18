// events.js

const EventStore = {
    items: [],

    push(msg, type = "info") {
        this.items.push({
            ts: Date.now(),
            msg,
            type
        });

        // ограничим память сессии
        if (this.items.length > 200) {
            this.items.shift();
        }
    }
};

function logEvent(msg, type = "info") {
    EventStore.push(msg, type);

    // РЕНДЕРИМ ТОЛЬКО КОГДА НА ЭКРАНЕ ИВЕНТОВ (0/1)
    // иначе ты сам себе сносишь nodes/offers в #output
    if (window.state === 0 || window.state === 1) {
        renderEvents();
    }
}

function renderEvents() {
    const out = document.getElementById("output");
    if (!out) return;

    out.innerHTML = EventStore.items
        .slice()
        .reverse()
        .map(ev => `
            <div class="event-item event-${ev.type}">
                <div class="event-time">
                    ${new Date(ev.ts).toLocaleTimeString()}
                </div>
                <div class="event-msg">${ev.msg}</div>
            </div>
        `)
        .join("");
}


// чтобы из консоли и из inline-скрипта точно были доступны
window.EventStore = EventStore;
window.logEvent = logEvent;
window.renderEvents = renderEvents;


function showToastAt(x, y, msg) {
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
