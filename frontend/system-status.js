const API_BASE = "http://127.0.0.1:8000";

const statusItemsEl = document.getElementById("status-items");
const refreshStatusBtn = document.getElementById("refresh-status-btn");

function renderStatus(status) {
    statusItemsEl.innerHTML = "";

    Object.values(status).forEach((item) => {
        const row = document.createElement("div");
        row.className = "status-row" + (item.ok ? " ok" : " missing");

        const icon = document.createElement("span");
        icon.className = "status-icon";
        icon.textContent = item.ok ? "✓" : "✕";

        const label = document.createElement("span");
        label.className = "status-label";
        label.textContent = item.label;

        row.appendChild(icon);
        row.appendChild(label);

        if (!item.ok && item.hint) {
            const hint = document.createElement("span");
            hint.className = "status-hint";
            hint.textContent = item.hint;
            row.appendChild(hint);
        }

        statusItemsEl.appendChild(row);
    });
}

async function loadSystemStatus() {
    statusItemsEl.innerHTML = `<p class="skills-empty">Vérification en cours...</p>`;
    try {
        const response = await fetch(`${API_BASE}/api/system-status`);
        if (!response.ok) throw new Error("backend indisponible");
        const data = await response.json();
        renderStatus(data);
    } catch (err) {
        statusItemsEl.innerHTML = `<p class="skills-empty">Backend injoignable (127.0.0.1:8000). Vérifiez qu'il est bien lancé — voir le README.</p>`;
    }
}

if (refreshStatusBtn) {
    refreshStatusBtn.addEventListener("click", loadSystemStatus);
}

loadSystemStatus();
