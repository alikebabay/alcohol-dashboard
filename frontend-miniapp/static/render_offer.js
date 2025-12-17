// render_offer.js
// Pure UI renderer for Offer cards

function renderOfferCard(n) {
    return `
        <div class="offer-card" data-id="${n.id}">
            <button class="node-delete" title="Delete">🗑</button>

            <div class="offer-title">${n.name ?? ""}</div>

            <div class="offer-grid">
                <!-- LEFT -->
                <div class="offer-col">
                    <div class="offer-row price">💰 ${n.price_bottle ?? "—"} / btl</div>
                    <div class="offer-row price">📦 ${n.price_case ?? "—"} / case</div>
                    <div class="offer-row currency">Currency ${n.currency ?? ""}</div>
                </div>

                <!-- RIGHT -->
                <div class="offer-col">
                    <div class="offer-row">🍾 ${n.cl ?? "?"} cl</div>
                    <div class="offer-row">
                        📦 ${n.bottles_per_case ?? "?"} / case
                    </div>
                    <div class="offer-row">📍 ${n.location ?? ""}</div>
                </div>
            </div>

            <div class="offer-access">
                🚚 ${n.access ?? ""}
            </div>
        </div>
    `;
}

// expose globally (important)
window.renderOfferCard = renderOfferCard;
