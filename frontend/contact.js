const API_BASE = "http://127.0.0.1:8000";

/* ---------- Effet de frappe sur le rôle ---------- */
const ROLES = [
    "Ingénieur en Génie Électrique",
    "Systèmes Embarqués",
    "Intelligence Artificielle",
    "Auteur de MiniLLM",
];

function startTypedRole() {
    const el = document.getElementById("typed-role");
    if (!el) return;

    let roleIndex = 0;
    let charIndex = ROLES[0].length;
    let deleting = false;

    function tick() {
        const current = ROLES[roleIndex];

        if (!deleting) {
            charIndex++;
            if (charIndex > current.length) {
                deleting = true;
                window.setTimeout(tick, 1600);
                return;
            }
        } else {
            charIndex--;
            if (charIndex < 0) {
                deleting = false;
                roleIndex = (roleIndex + 1) % ROLES.length;
                charIndex = 0;
            }
        }

        el.textContent = current.slice(0, charIndex);
        window.setTimeout(tick, deleting ? 35 : 55);
    }

    charIndex = 0;
    el.textContent = "";
    window.setTimeout(tick, 400);
}

/* ---------- Compteurs animés ---------- */
function animateCounter(el, target, duration = 900) {
    if (!el) return;
    const start = performance.now();

    function step(now) {
        const progress = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(eased * target);
        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            el.textContent = target;
        }
    }
    requestAnimationFrame(step);
}

/* ---------- Barres de compétences + langues (profil réel) ---------- */
function renderSkillBars(skills) {
    const container = document.getElementById("skills-bars");
    if (!container) return;

    if (!skills || !skills.length) {
        container.innerHTML = `<p class="skills-empty">Aucune compétence enregistrée pour l'instant — renseignez votre profil.</p>`;
        return;
    }

    container.innerHTML = "";
    skills.forEach((skill, i) => {
        const pct = 72 + ((i * 7) % 23); // variation visuelle, sans prétendre à une mesure exacte
        const row = document.createElement("div");
        row.className = "skill-row";
        row.innerHTML = `
            <div class="skill-row-top">
                <span class="skill-row-name">${skill}</span>
                <span class="skill-row-pct">${pct}%</span>
            </div>
            <div class="skill-bar-track">
                <div class="skill-bar-fill" style="width:0%"></div>
            </div>
        `;
        container.appendChild(row);

        const fill = row.querySelector(".skill-bar-fill");
        window.setTimeout(() => {
            fill.style.width = pct + "%";
        }, 120 + i * 90);
    });
}

function renderLangChips(languages) {
    const container = document.getElementById("langs-chips");
    if (!container) return;

    const entries = Object.entries(languages || {});
    if (!entries.length) {
        container.innerHTML = `<p class="skills-empty">Aucune langue enregistrée pour l'instant.</p>`;
        return;
    }

    container.innerHTML = "";
    entries.forEach(([lang, level], i) => {
        const chip = document.createElement("span");
        chip.className = "lang-chip";
        chip.style.animationDelay = `${i * 0.08}s`;
        chip.innerHTML = `${lang}${level ? ` <span class="lang-level-tag">${level}</span>` : ""}`;
        container.appendChild(chip);
    });
}

async function loadProfileIntoPage() {
    try {
        const response = await fetch(`${API_BASE}/api/profile`);
        if (!response.ok) throw new Error("profil indisponible");
        const data = await response.json();

        const skills = data.skills || [];
        const languages = data.languages || {};

        renderSkillBars(skills);
        renderLangChips(languages);

        animateCounter(document.getElementById("stat-skills"), skills.length);
        animateCounter(document.getElementById("stat-langs"), Object.keys(languages).length);

        const locEl = document.getElementById("about-location");
        if (locEl && data.location) {
            locEl.textContent = `📍 ${data.location}`;
        }

        const bioEl = document.getElementById("about-bio");
        if (bioEl && data.summary) {
            bioEl.textContent = data.summary;
        }
    } catch (err) {
        renderSkillBars([]);
        renderLangChips({});
    }
}

/* ---------- Copie rapide de l'email ---------- */
const emailBtn = document.getElementById("email-copy-btn");
if (emailBtn) {
    emailBtn.addEventListener("click", (e) => {
        if (navigator.clipboard) {
            e.preventDefault();
            navigator.clipboard.writeText("ademyehmed2018@gmail.com").then(() => {
                const original = emailBtn.textContent;
                emailBtn.textContent = "✓ Copié !";
                window.setTimeout(() => {
                    emailBtn.textContent = original;
                }, 1600);
            }).catch(() => {
                window.location.href = "mailto:ademyehmed2018@gmail.com";
            });
        }
    });
}

startTypedRole();
loadProfileIntoPage();
