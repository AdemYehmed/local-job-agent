// API_BASE est déjà déclaré par profile.js (chargé avant ce fichier)

const companyDomainEl = document.getElementById("company-domain");
const companyRegionEl = document.getElementById("company-region");
const searchCompaniesBtn = document.getElementById("search-companies-btn");
const exportCsvBtn = document.getElementById("export-csv-btn");
const companiesStatusEl = document.getElementById("companies-status");
const companiesTable = document.getElementById("companies-table");
const companiesTableBody = document.getElementById("companies-table-body");

let lastCompanies = [];

function setCompaniesStatus(text, type) {
    companiesStatusEl.textContent = text;
    companiesStatusEl.className = "status-text" + (type ? ` ${type}` : "");
}

function renderCompaniesTable(companies) {
    companiesTableBody.innerHTML = "";

    if (!companies.length) {
        companiesTable.style.display = "none";
        exportCsvBtn.disabled = true;
        return;
    }

    companies.forEach((c) => {
        const row = document.createElement("tr");

        const nameCell = document.createElement("td");
        nameCell.contentEditable = "true";
        nameCell.textContent = c.company || "";

        const emailCell = document.createElement("td");
        emailCell.contentEditable = "true";
        emailCell.textContent = c.email || "";
        if (!c.email) {
            emailCell.innerHTML = `<span class="job-company-empty">à compléter</span>`;
        }

        const urlCell = document.createElement("td");
        const link = document.createElement("a");
        link.href = c.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "voir la source";
        urlCell.appendChild(link);

        row.append(nameCell, emailCell, urlCell);
        companiesTableBody.appendChild(row);
    });

    companiesTable.style.display = "table";
    exportCsvBtn.disabled = false;
}

document.querySelectorAll(".suggested-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        companyDomainEl.value = chip.dataset.kw;
        companyDomainEl.focus();
    });
});

searchCompaniesBtn.addEventListener("click", async () => {
    const domain = companyDomainEl.value.trim();
    if (!domain) {
        setCompaniesStatus("Entre un domaine ou des mots-clés.", "error");
        return;
    }
    const region = companyRegionEl.value.trim() || "Tunisie";

    searchCompaniesBtn.disabled = true;
    companiesTable.style.display = "none";
    exportCsvBtn.disabled = true;
    setCompaniesStatus("Recherche en cours (20-40s)...", "");

    try {
        const response = await fetch(`${API_BASE}/api/search-companies`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain_keywords: domain, region }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Erreur HTTP ${response.status}`);
        }

        const data = await response.json();
        lastCompanies = data.companies || [];
        renderCompaniesTable(lastCompanies);
        setCompaniesStatus(`${lastCompanies.length} entreprise(s) trouvée(s). Corrigez les emails manquants si vous les connaissez.`, "success");
    } catch (err) {
        setCompaniesStatus(`Erreur : ${err.message}`, "error");
    } finally {
        searchCompaniesBtn.disabled = false;
    }
});

function escapeCsvField(value) {
    const str = String(value ?? "");
    if (str.includes(",") || str.includes('"') || str.includes("\n")) {
        return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
}

exportCsvBtn.addEventListener("click", () => {
    const rows = Array.from(companiesTableBody.querySelectorAll("tr")).map((row) => {
        const cells = row.querySelectorAll("td");
        const name = cells[0].textContent.trim();
        const email = cells[1].textContent.trim() === "à compléter" ? "" : cells[1].textContent.trim();
        const url = cells[2].querySelector("a")?.href || "";
        return [name, email, url];
    });

    const header = ["Entreprise", "Email contact RH", "URL source"];
    const csvLines = [header, ...rows].map((r) => r.map(escapeCsvField).join(","));
    const csvContent = csvLines.join("\n");

    const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "entreprises.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});
