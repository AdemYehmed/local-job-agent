// Remplacez par l'URL de votre backend une fois déployé (ex: https://votre-backend.onrender.com)
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "https://REMPLACEZ-PAR-VOTRE-BACKEND.onrender.com";

const keywordsEl = document.getElementById("job-keywords");
const regionEl = document.getElementById("job-region");
const timelimitEl = document.getElementById("job-timelimit");
const experienceEl = document.getElementById("job-experience");
const searchBtn = document.getElementById("search-jobs-btn");
const searchStatusEl = document.getElementById("search-status");
const resultsSummaryEl = document.getElementById("results-summary");
const tableBodyEl = document.getElementById("jobs-table-body");

function setStatus(el, text, type) {
    el.textContent = text;
    el.className = "status-text" + (type ? ` ${type}` : "");
}

function getSelectedSources() {
    const checkboxes = document.querySelectorAll('.source-checkbox input[type="checkbox"]');
    return Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
}

function renderOffers(offers) {
    tableBodyEl.innerHTML = "";

    if (!offers.length) {
        tableBodyEl.innerHTML = `<tr><td colspan="6" class="empty-results">Aucune offre trouvée. Essaie d'autres mots-clés.</td></tr>`;
        return;
    }

    offers.forEach((offer) => {
        const row = document.createElement("tr");

        const titleCell = document.createElement("td");
        titleCell.className = "job-title-cell";
        const link = document.createElement("a");
        link.href = offer.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = offer.title || "(sans titre)";
        titleCell.appendChild(link);

        const companyCell = document.createElement("td");
        companyCell.textContent = offer.company || "—";
        if (!offer.company) companyCell.className = "job-company-empty";

        const locationCell = document.createElement("td");
        locationCell.textContent = offer.location || "—";

        const methodCell = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `method-badge ${offer.application_method}`;
        badge.textContent = offer.application_method === "email" ? "email" : "lien";
        methodCell.appendChild(badge);

        const dateCell = document.createElement("td");
        dateCell.textContent = offer.date_hint || "—";

        const actionCell = document.createElement("td");
        const viewLink = document.createElement("a");
        viewLink.className = "view-offer-link";
        viewLink.href = offer.url;
        viewLink.target = "_blank";
        viewLink.rel = "noopener noreferrer";
        viewLink.textContent = "Voir l'offre ↗";
        actionCell.appendChild(viewLink);

        row.append(titleCell, companyCell, locationCell, methodCell, dateCell, actionCell);
        tableBodyEl.appendChild(row);
    });
}

searchBtn.addEventListener("click", async () => {
    const keywords = keywordsEl.value.trim();
    if (!keywords) {
        setStatus(searchStatusEl, "Entre au moins un mot-clé.", "error");
        return;
    }

    const sources = getSelectedSources();
    if (!sources.length) {
        setStatus(searchStatusEl, "Sélectionne au moins une source.", "error");
        return;
    }

    searchBtn.disabled = true;
    resultsSummaryEl.textContent = "";
    tableBodyEl.innerHTML = "";
    setStatus(searchStatusEl, "Recherche en cours (peut prendre 15-40s)...", "");

    try {
        const response = await fetch(`${API_BASE}/api/search-jobs`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                keywords,
                region: regionEl.value,
                timelimit: timelimitEl.value,
                experience: experienceEl.value,
                sources,
            }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        const data = await response.json();
        resultsSummaryEl.textContent = `${data.filtered_count} offre(s) trouvée(s) sur ${data.raw_count} résultat(s) analysé(s)`;
        renderOffers(data.offers);
        setStatus(searchStatusEl, "Recherche terminée.", "success");
    } catch (err) {
        setStatus(searchStatusEl, `Erreur : ${err.message}`, "error");
    } finally {
        searchBtn.disabled = false;
    }
});
