const API_BASE = "http://127.0.0.1:8000";

const nameEl = document.getElementById("p-name");
const emailEl = document.getElementById("p-email");
const degreeEl = document.getElementById("p-degree");
const yearEl = document.getElementById("p-year");
const locationEl = document.getElementById("p-location");
const summaryEl = document.getElementById("p-summary");

const skillsChipsEl = document.getElementById("skills-chips");
const newSkillInput = document.getElementById("new-skill-input");
const addSkillBtn = document.getElementById("add-skill-btn");

const languagesListEl = document.getElementById("languages-list");
const newLangName = document.getElementById("new-lang-name");
const newLangLevel = document.getElementById("new-lang-level");
const addLangBtn = document.getElementById("add-lang-btn");

const extractBtn = document.getElementById("extract-btn");
const extractStatusEl = document.getElementById("extract-status");
const saveBtn = document.getElementById("save-profile-btn");
const saveStatusEl = document.getElementById("save-status");

let currentSkills = [];
let currentLanguages = {};

function setStatus(el, text, type) {
    el.textContent = text;
    el.className = "status-text" + (type ? ` ${type}` : "");
}

function renderSkills() {
    skillsChipsEl.innerHTML = "";
    currentSkills.forEach((skill, idx) => {
        const chip = document.createElement("div");
        chip.className = "chip";
        chip.innerHTML = `<span>${skill}</span>`;
        const removeBtn = document.createElement("button");
        removeBtn.className = "chip-remove";
        removeBtn.textContent = "×";
        removeBtn.addEventListener("click", () => {
            currentSkills.splice(idx, 1);
            renderSkills();
        });
        chip.appendChild(removeBtn);
        skillsChipsEl.appendChild(chip);
    });
}

function renderLanguages() {
    languagesListEl.innerHTML = "";
    Object.entries(currentLanguages).forEach(([lang, level]) => {
        const row = document.createElement("div");
        row.className = "language-row";
        row.innerHTML = `<span class="lang-name">${lang}</span><span class="lang-level">${level || "—"}</span>`;
        const removeBtn = document.createElement("button");
        removeBtn.className = "chip-remove";
        removeBtn.textContent = "×";
        removeBtn.addEventListener("click", () => {
            delete currentLanguages[lang];
            renderLanguages();
        });
        row.appendChild(removeBtn);
        languagesListEl.appendChild(row);
    });
}

function fillForm(profile) {
    nameEl.value = profile.name || "";
    emailEl.value = profile.email || "";
    degreeEl.value = profile.degree || "";
    yearEl.value = profile.graduation_year || "";
    locationEl.value = profile.location || "";
    summaryEl.value = profile.summary || "";
    currentSkills = [...new Set(profile.skills || [])];
    currentLanguages = { ...(profile.languages || {}) };
    renderSkills();
    renderLanguages();
}

function collectForm() {
    return {
        name: nameEl.value.trim(),
        email: emailEl.value.trim(),
        degree: degreeEl.value.trim(),
        graduation_year: yearEl.value.trim() || null,
        location: locationEl.value.trim(),
        summary: summaryEl.value.trim(),
        skills: currentSkills,
        languages: currentLanguages,
    };
}

async function loadProfile() {
    try {
        const response = await fetch(`${API_BASE}/api/profile`);
        const data = await response.json();
        fillForm(data);
    } catch (err) {
        setStatus(saveStatusEl, `Erreur de chargement : ${err.message}`, "error");
    }
}

addSkillBtn.addEventListener("click", () => {
    const value = newSkillInput.value.trim();
    if (!value) return;
    if (!currentSkills.includes(value)) {
        currentSkills.push(value);
        renderSkills();
    }
    newSkillInput.value = "";
    newSkillInput.focus();
});

newSkillInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        addSkillBtn.click();
    }
});

addLangBtn.addEventListener("click", () => {
    const lang = newLangName.value.trim();
    const level = newLangLevel.value.trim();
    if (!lang) return;
    currentLanguages[lang] = level;
    renderLanguages();
    newLangName.value = "";
    newLangLevel.value = "";
    newLangName.focus();
});

extractBtn.addEventListener("click", async () => {
    extractBtn.disabled = true;
    setStatus(extractStatusEl, "Extraction en cours (peut prendre 15-30s)...", "");

    try {
        const response = await fetch(`${API_BASE}/api/extract-profile-from-cv`, {
            method: "POST",
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        const data = await response.json();
        fillForm(data);
        setStatus(extractStatusEl, "Profil extrait. Vérifie et corrige avant d'enregistrer.", "success");
    } catch (err) {
        setStatus(extractStatusEl, `Erreur : ${err.message}`, "error");
    } finally {
        extractBtn.disabled = false;
    }
});

saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    setStatus(saveStatusEl, "Enregistrement...", "");

    try {
        const response = await fetch(`${API_BASE}/api/profile`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(collectForm()),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        setStatus(saveStatusEl, "Profil enregistré ✓", "success");
    } catch (err) {
        setStatus(saveStatusEl, `Erreur : ${err.message}`, "error");
    } finally {
        saveBtn.disabled = false;
    }
});

loadProfile();
