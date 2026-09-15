const API_BASE = "http://127.0.0.1:8000";

const jobTextEl = document.getElementById("job-text");
const companyNameEl = document.getElementById("company-name");
const generateBtn = document.getElementById("generate-btn");
const generateStatusEl = document.getElementById("generate-status");

const emailToEl = document.getElementById("email-to");
const emailSubjectEl = document.getElementById("email-subject");
const emailBodyEl = document.getElementById("email-body");
const sendBtn = document.getElementById("send-btn");
const sendStatusEl = document.getElementById("send-status");

const modeTabOffer = document.getElementById("mode-tab-offer");
const modeTabGeneric = document.getElementById("mode-tab-generic");
const offerModeFields = document.getElementById("offer-mode-fields");
const genericModeFields = document.getElementById("generic-mode-fields");
const scoreBtnRef = document.getElementById("score-btn");

let currentMode = "offer";

function setStatus(el, text, type) {
    el.textContent = text;
    el.className = "status-text" + (type ? ` ${type}` : "");
}

function setMode(mode) {
    currentMode = mode;
    modeTabOffer.classList.toggle("is-active", mode === "offer");
    modeTabGeneric.classList.toggle("is-active", mode === "generic");
    offerModeFields.style.display = mode === "offer" ? "block" : "none";
    genericModeFields.style.display = mode === "generic" ? "block" : "none";
    if (scoreBtnRef) {
        scoreBtnRef.disabled = mode === "generic";
        scoreBtnRef.title = mode === "generic" ? "Le score nécessite une offre précise" : "";
    }
}

if (modeTabOffer && modeTabGeneric) {
    modeTabOffer.addEventListener("click", () => setMode("offer"));
    modeTabGeneric.addEventListener("click", () => setMode("generic"));
}

generateBtn.addEventListener("click", async () => {
    let payload;

    if (currentMode === "generic") {
        const companyName = companyNameEl.value.trim();
        if (!companyName) {
            setStatus(generateStatusEl, "Indique le nom de l'entreprise.", "error");
            return;
        }
        payload = { generic: true, company_name: companyName };
    } else {
        const jobText = jobTextEl.value.trim();
        if (!jobText) {
            setStatus(generateStatusEl, "Colle d'abord le texte de l'offre.", "error");
            return;
        }
        payload = { job_text: jobText };
    }

    generateBtn.disabled = true;
    setStatus(generateStatusEl, "Génération en cours (peut prendre 10-30s)...", "");
    sendBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/generate-email`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        const data = await response.json();
        emailSubjectEl.value = data.subject || "";
        emailBodyEl.value = data.body || "";
        if (data.recipient_email) {
            emailToEl.value = data.recipient_email;
        }
        setStatus(generateStatusEl, "Email généré. Relis-le avant d'envoyer.", "success");
        sendBtn.disabled = false;
    } catch (err) {
        setStatus(generateStatusEl, `Erreur : ${err.message}`, "error");
    } finally {
        generateBtn.disabled = false;
    }
});

sendBtn.addEventListener("click", async () => {
    const toEmail = emailToEl.value.trim();
    const subject = emailSubjectEl.value.trim();
    const body = emailBodyEl.value.trim();

    if (!toEmail || !subject || !body) {
        setStatus(sendStatusEl, "Renseigne le destinataire, l'objet et le corps avant d'envoyer.", "error");
        return;
    }

    const confirmed = confirm(`Envoyer cet email à ${toEmail} ?\n\nObjet : ${subject}`);
    if (!confirmed) return;

    sendBtn.disabled = true;
    setStatus(sendStatusEl, "Envoi en cours...", "");

    try {
        const response = await fetch(`${API_BASE}/api/send-email`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ to_email: toEmail, subject, body }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        const data = await response.json();
        setStatus(sendStatusEl, `Email envoyé à ${data.to} ✓`, "success");
    } catch (err) {
        setStatus(sendStatusEl, `Erreur : ${err.message}`, "error");
        sendBtn.disabled = false;
    }
});

const cvUploadEl = document.getElementById("cv-upload");
const uploadCvBtn = document.getElementById("upload-cv-btn");
const cvStatusEl = document.getElementById("cv-status");

async function checkCvStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/cv-status`);
        const data = await response.json();
        if (data.has_cv) {
            const kb = Math.round(data.size_bytes / 1024);
            setStatus(cvStatusEl, `CV actuel : ${kb} Ko`, "success");
        } else {
            setStatus(cvStatusEl, "Aucun CV uploadé pour l'instant.", "");
        }
    } catch (err) {
        setStatus(cvStatusEl, "Impossible de vérifier le statut du CV.", "error");
    }
}

uploadCvBtn.addEventListener("click", async () => {
    const file = cvUploadEl.files[0];
    if (!file) {
        setStatus(cvStatusEl, "Choisis d'abord un fichier PDF.", "error");
        return;
    }

    uploadCvBtn.disabled = true;
    setStatus(cvStatusEl, "Upload en cours...", "");

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE}/api/upload-cv`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        const data = await response.json();
        const kb = Math.round(data.size_bytes / 1024);
        setStatus(cvStatusEl, `CV uploadé : ${data.filename} (${kb} Ko)`, "success");
    } catch (err) {
        setStatus(cvStatusEl, `Erreur : ${err.message}`, "error");
    } finally {
        uploadCvBtn.disabled = false;
    }
});

checkCvStatus();

function loadPendingJobOffer() {
    const pending = sessionStorage.getItem("pendingJobOffer");
    if (!pending) return;

    try {
        const data = JSON.parse(pending);
        if (data.jobText) {
            jobTextEl.value = data.jobText;
        }
        if (data.recipientEmail) {
            emailToEl.value = data.recipientEmail;
        }
        sessionStorage.removeItem("pendingJobOffer");
        setStatus(generateStatusEl, "Offre chargée depuis la recherche. Clique sur GÉNÉRER L'EMAIL.", "success");
    } catch (err) {
        // ignore silently
    }
}

loadPendingJobOffer();

const scoreBtn = document.getElementById("score-btn");
const scoreResultEl = document.getElementById("score-result");

function renderScore(data) {
    const scoreClass = data.score >= 70 ? "high" : data.score < 40 ? "low" : "";
    const matchingTags = (data.matching_skills || [])
        .map(s => `<span class="score-skill-tag match">✓ ${s}</span>`)
        .join("");
    const missingTags = (data.missing_skills || [])
        .map(s => `<span class="score-skill-tag missing">✗ ${s}</span>`)
        .join("");

    scoreResultEl.innerHTML = `
        <div class="score-top-row">
            <span class="score-value ${scoreClass}" id="score-value-num">0/100</span>
        </div>
        <div class="score-bar-track">
            <div class="score-bar-fill ${scoreClass}" id="score-bar-fill" style="width:0%"></div>
        </div>
        <div class="score-recommendation">${data.recommendation || ""}</div>
        <div class="score-skills-row">${matchingTags}${missingTags}</div>
    `;
    scoreResultEl.style.display = "block";

    const numEl = document.getElementById("score-value-num");
    const barEl = document.getElementById("score-bar-fill");
    const target = Math.max(0, Math.min(100, data.score || 0));
    const duration = 700;
    const start = performance.now();

    requestAnimationFrame(function tick() {
        barEl.style.width = target + "%";
    });

    function step(now) {
        const progress = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(eased * target);
        numEl.textContent = `${current}/100`;
        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            numEl.textContent = `${target}/100`;
        }
    }
    requestAnimationFrame(step);
}

if (scoreBtn) {
    scoreBtn.addEventListener("click", async () => {
        const jobText = jobTextEl.value.trim();
        if (!jobText) {
            setStatus(generateStatusEl, "Colle d'abord le texte de l'offre.", "error");
            return;
        }

        scoreBtn.disabled = true;
        scoreResultEl.style.display = "none";
        setStatus(generateStatusEl, "Calcul du score en cours (15-30s)...", "");

        try {
            const response = await fetch(`${API_BASE}/api/score-job`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_text: jobText }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
            }

            const data = await response.json();
            renderScore(data);
            setStatus(generateStatusEl, "Score calculé.", "success");
        } catch (err) {
            setStatus(generateStatusEl, `Erreur : ${err.message}`, "error");
        } finally {
            scoreBtn.disabled = false;
        }
    });
}
