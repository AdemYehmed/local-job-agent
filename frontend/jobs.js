const API_BASE = "http://127.0.0.1:8000";

const keywordsEl = document.getElementById("job-keywords");
const keywordSuggestionsEl = document.getElementById("keyword-suggestions");
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

const KEYWORD_SUGGESTIONS_CACHE_KEY = "minillm-keyword-suggestions-cache";

function renderKeywordSuggestions(keywords) {
    keywordSuggestionsEl.innerHTML = "";
    if (!keywords || !keywords.length) return;

    const label = document.createElement("span");
    label.className = "companies-suggested-label";
    label.textContent = "Suggestions :";
    keywordSuggestionsEl.appendChild(label);

    keywords.forEach((kw) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "suggested-chip";
        chip.dataset.kw = kw;
        chip.textContent = kw;
        chip.addEventListener("click", () => {
            const current = keywordsEl.value.trim();
            const alreadyIncluded = current
                .split("+")
                .map(k => k.trim().toLowerCase())
                .includes(chip.dataset.kw.toLowerCase());
            if (alreadyIncluded) return;
            keywordsEl.value = current ? `${current} + ${chip.dataset.kw}` : chip.dataset.kw;
            keywordsEl.focus();
        });
        keywordSuggestionsEl.appendChild(chip);
    });
}

async function loadKeywordSuggestions() {
    let cache = null;
    try {
        const raw = localStorage.getItem(KEYWORD_SUGGESTIONS_CACHE_KEY);
        cache = raw ? JSON.parse(raw) : null;
    } catch (e) {
        cache = null;
    }

    let currentProfileSnapshot = null;
    try {
        const profileResp = await fetch(`${API_BASE}/api/profile`);
        if (profileResp.ok) {
            const profileData = await profileResp.json();
            currentProfileSnapshot = JSON.stringify(profileData);
        }
    } catch (e) {
        // pas de profil accessible : on retombera sur le cache s'il existe
    }

    if (cache && cache.profileSnapshot && currentProfileSnapshot && cache.profileSnapshot === currentProfileSnapshot) {
        renderKeywordSuggestions(cache.keywords || []);
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/suggest-keywords`);
        if (!response.ok) {
            if (cache) renderKeywordSuggestions(cache.keywords || []);
            return;
        }
        const data = await response.json();
        renderKeywordSuggestions(data.keywords || []);

        if (currentProfileSnapshot) {
            try {
                localStorage.setItem(KEYWORD_SUGGESTIONS_CACHE_KEY, JSON.stringify({
                    profileSnapshot: currentProfileSnapshot,
                    keywords: data.keywords || [],
                }));
            } catch (e) {
                // stockage indisponible : pas grave, on regénérera la prochaine fois
            }
        }
    } catch (err) {
        if (cache) renderKeywordSuggestions(cache.keywords || []);
    }
}

loadKeywordSuggestions();

function buildJobText(offer) {
    const lines = [
        `Poste : ${offer.title}`,
        offer.company ? `Entreprise : ${offer.company}` : null,
        offer.location ? `Localisation : ${offer.location}` : null,
        offer.skills_mentioned && offer.skills_mentioned.length
            ? `Compétences mentionnées : ${offer.skills_mentioned.join(", ")}`
            : null,
        offer.contact_email ? `Contact : ${offer.contact_email}` : null,
        `Lien de l'offre : ${offer.url}`,
    ].filter(Boolean);
    return lines.join("\n");
}

const SCORES_CACHE_KEY = "minillm-job-scores";

function loadScoreCache() {
    try {
        const raw = localStorage.getItem(SCORES_CACHE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch (e) {
        return {};
    }
}

function saveScoreCache(cache) {
    try {
        localStorage.setItem(SCORES_CACHE_KEY, JSON.stringify(cache));
    } catch (e) {
        // stockage indisponible : on continue sans persister
    }
}

function renderScoreCell(scoreCell, score) {
    const scoreClass = score >= 70 ? "high" : score < 40 ? "low" : "";
    scoreCell.innerHTML = `<span class="score-value-inline score-pop ${scoreClass}">${score}/100</span>`;
}

let pendingScoreCells = [];

async function computeScoresSequentially() {
    const queue = pendingScoreCells;
    pendingScoreCells = [];
    const cache = loadScoreCache();

    for (const { offer, scoreCell } of queue) {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 60000);
        try {
            const response = await fetch(`${API_BASE}/api/score-job`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_text: buildJobText(offer), job_url: offer.url || "" }),
                signal: controller.signal,
            });
            if (!response.ok) {
                throw new Error("erreur");
            }
            const data = await response.json();
            renderScoreCell(scoreCell, data.score);
            cache[offer.url] = data.score;
            saveScoreCache(cache);
        } catch (err) {
            scoreCell.innerHTML = `<span class="job-company-empty">—</span>`;
        } finally {
            window.clearTimeout(timeoutId);
        }
    }
}

function renderOffers(offers) {
    tableBodyEl.innerHTML = "";
    pendingScoreCells = [];

    if (!offers.length) {
        tableBodyEl.innerHTML = `<tr><td colspan="8" class="empty-results">Aucune offre exploitable trouvée. Essaie d'autres mots-clés ou sources.</td></tr>`;
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
        if (offer.company) {
            companyCell.textContent = offer.company;
        } else {
            companyCell.innerHTML = `<span class="job-company-empty">non identifiée</span>`;
        }

        const locationCell = document.createElement("td");
        locationCell.textContent = offer.location || "—";

        const skillsCell = document.createElement("td");
        (offer.skills_mentioned || []).forEach(skill => {
            const tag = document.createElement("span");
            tag.className = "skill-tag";
            tag.textContent = skill;
            skillsCell.appendChild(tag);
        });
        if (!offer.skills_mentioned || !offer.skills_mentioned.length) {
            skillsCell.textContent = "—";
        }

        const methodCell = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `method-badge ${offer.application_method}`;
        badge.textContent = offer.application_method === "email" ? "email" : "lien";
        methodCell.appendChild(badge);

        const dateCell = document.createElement("td");
        dateCell.textContent = offer.date_hint || "—";

        const scoreCell = document.createElement("td");
        if (offer.score !== null && offer.score !== undefined) {
            renderScoreCell(scoreCell, offer.score);
        } else {
            const cachedScores = loadScoreCache();
            if (Object.prototype.hasOwnProperty.call(cachedScores, offer.url)) {
                renderScoreCell(scoreCell, cachedScores[offer.url]);
            } else {
                scoreCell.innerHTML = `<span class="score-pending">…</span>`;
                pendingScoreCells.push({ offer, scoreCell });
            }
        }

        const actionCell = document.createElement("td");
        actionCell.className = "action-cell";

        const viewLink = document.createElement("a");
        viewLink.className = "view-offer-link";
        viewLink.href = offer.url;
        viewLink.target = "_blank";
        viewLink.rel = "noopener noreferrer";
        viewLink.textContent = "Voir l'offre ↗";
        actionCell.appendChild(viewLink);

        const applyBtn = document.createElement("button");
        applyBtn.className = "apply-row-btn";
        applyBtn.textContent = "POSTULER →";
        applyBtn.addEventListener("click", () => {
            sessionStorage.setItem("pendingJobOffer", JSON.stringify({
                jobText: buildJobText(offer),
                recipientEmail: offer.contact_email || "",
            }));
            window.location.href = "apply.html";
        });
        actionCell.appendChild(applyBtn);

        row.append(titleCell, companyCell, locationCell, skillsCell, methodCell, dateCell, scoreCell, actionCell);
        tableBodyEl.appendChild(row);
    });

    computeScoresSequentially();
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
    setStatus(searchStatusEl, "Recherche en cours (peut prendre 30-90s selon le nombre de sources)...", "");

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
        resultsSummaryEl.textContent = `${data.filtered_count} offre(s) retenue(s) sur ${data.raw_count} résultat(s) analysé(s)`;
        renderOffers(data.offers);
        setStatus(searchStatusEl, "Recherche terminée.", "success");
    } catch (err) {
        setStatus(searchStatusEl, `Erreur : ${err.message}`, "error");
    } finally {
        searchBtn.disabled = false;
    }
});


async function loadStoredJobs() {
    try {
        const response = await fetch(`${API_BASE}/api/stored-jobs`);
        const data = await response.json();
        if (data.offers && data.offers.length) {
            resultsSummaryEl.textContent = `${data.offers.length} offre(s) enregistrée(s) depuis les recherches précédentes`;
            renderOffers(data.offers);
        }
    } catch (err) {
        // silencieux, pas grave si ça échoue au chargement initial
    }
}

loadStoredJobs();


const clearJobsBtn = document.getElementById("clear-jobs-btn");
if (clearJobsBtn) {
    clearJobsBtn.addEventListener("click", async () => {
        const confirmed = confirm("Supprimer toutes les offres enregistrées ?");
        if (!confirmed) return;
        try {
            await fetch(`${API_BASE}/api/stored-jobs`, { method: "DELETE" });
            resultsSummaryEl.textContent = "";
            tableBodyEl.innerHTML = "";
        } catch (err) {
            setStatus(searchStatusEl, `Erreur : ${err.message}`, "error");
        }
    });
}
