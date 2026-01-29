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

export function logEvent(msg, type = "info") {
    EventStore.push(msg, type);

    // рендерим логи ТОЛЬКО в state 0
    if (window.appState?.state === 0) {
        renderEvents();
    }
}

export function renderEvents() {
    // защита: логи могут рендериться ТОЛЬКО в state 0
    if (window.appState?.state !== 0) return;
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



