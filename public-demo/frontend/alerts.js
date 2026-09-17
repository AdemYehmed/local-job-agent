const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "https://local-job-agent.onrender.com";

const keywordsEl = document.getElementById("alert-keywords");
const regionEl = document.getElementById("alert-region");
const timelimitEl = document.getElementById("alert-timelimit");
const experienceEl = document.getElementById("alert-experience");
const intervalEl = document.getElementById("alert-interval");
const emailEl = document.getElementById("alert-email");
const saveBtn = document.getElementById("save-alert-btn");
const statusMsgEl = document.getElementById("alert-status-msg");
const statusDisplayEl = document.getElementById("alert-status-display");

function setStatus(el, text, type) {
    el.textContent = text;
    el.className = "status-text" + (type ? ` ${type}` : "");
}

function getSelectedSources() {
    const checkboxes = document.querySelectorAll('.source-checkbox input[type="checkbox"]');
    return Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
}

async function loadCurrentConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/alert-config`);
        const data = await response.json();
        if (data && data.keywords) {
            keywordsEl.value = data.keywords || "";
            regionEl.value = data.region || "monde";
            timelimitEl.value = data.timelimit || "mois";
            experienceEl.value = data.experience || "tout";
            intervalEl.value = data.interval_hours || 1;
            emailEl.value = data.email || "";
            document.querySelectorAll('.source-checkbox input[type="checkbox"]').forEach(cb => {
                cb.checked = (data.sources || []).includes(cb.value);
            });
        }
    } catch (err) {
        // pas grave si aucune config n'existe encore
    }
}

async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/alert-status`);
        const data = await response.json();
        if (!data.last_run) {
            statusDisplayEl.textContent = "Aucune vérification effectuée pour l'instant.";
            return;
        }
        const date = new Date(data.last_run).toLocaleString("fr-FR");
        statusDisplayEl.textContent = `Dernière vérification : ${date} — ${data.last_new_count} nouvelle(s) offre(s) trouvée(s) — ${data.total_seen} offre(s) suivie(s) au total.`;
    } catch (err) {
        statusDisplayEl.textContent = "Statut indisponible.";
    }
}

saveBtn.addEventListener("click", async () => {
    const keywords = keywordsEl.value.trim();
    const email = emailEl.value.trim();
    if (!keywords || !email) {
        setStatus(statusMsgEl, "Renseigne au moins les mots-clés et l'email.", "error");
        return;
    }

    const sources = getSelectedSources();
    if (!sources.length) {
        setStatus(statusMsgEl, "Sélectionne au moins une source.", "error");
        return;
    }

    saveBtn.disabled = true;
    setStatus(statusMsgEl, "Enregistrement...", "");

    try {
        const response = await fetch(`${API_BASE}/api/alert-config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                keywords,
                region: regionEl.value,
                timelimit: timelimitEl.value,
                experience: experienceEl.value,
                sources,
                interval_hours: parseFloat(intervalEl.value) || 1,
                email,
                active: true,
            }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        setStatus(statusMsgEl, "Alerte enregistrée et active. La première vérification aura lieu sous peu.", "success");
        loadStatus();
    } catch (err) {
        setStatus(statusMsgEl, `Erreur : ${err.message}`, "error");
    } finally {
        saveBtn.disabled = false;
    }
});

loadCurrentConfig();
loadStatus();
