/* ============================================================
   nav.js — navigation globale (UI uniquement)
   Ne touche à aucun appel API ni à aucune logique métier.
   Chargé sur home.html, index.html, apply.html, profile.html.
   ============================================================ */

(function () {
    /* --- Palette de couleurs (préférence locale, aucun appel réseau) --- */
    const PALETTE_KEY = "minillm-palette";
    const DEFAULT_PALETTE = "vitrail";
    const swatches = document.querySelectorAll(".swatch[data-palette]");

    const applyPalette = (palette, animate) => {
        if (animate) {
            document.documentElement.classList.add("theme-switching");
            window.setTimeout(() => {
                document.documentElement.classList.remove("theme-switching");
            }, 320);
        }
        if (palette === DEFAULT_PALETTE) {
            document.documentElement.removeAttribute("data-theme");
        } else {
            document.documentElement.setAttribute("data-theme", palette);
        }
        swatches.forEach((s) => {
            s.setAttribute("aria-pressed", s.dataset.palette === palette ? "true" : "false");
        });
        try { localStorage.setItem(PALETTE_KEY, palette); } catch (e) {}
    };

    if (swatches.length) {
        let saved = DEFAULT_PALETTE;
        try { saved = localStorage.getItem(PALETTE_KEY) || DEFAULT_PALETTE; } catch (e) {}
        applyPalette(saved, false);

        swatches.forEach((s) => {
            s.addEventListener("click", () => applyPalette(s.dataset.palette, true));
        });
    }

    /* --- Menu mobile --- */
    const toggle = document.getElementById("nav-toggle");
    const menu = document.getElementById("nav-menu");

    if (toggle && menu) {
        toggle.addEventListener("click", () => {
            const open = menu.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && menu.classList.contains("is-open")) {
                menu.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
                toggle.focus();
            }
        });
    }

    /* --- Page active (secours si la classe n'est pas déjà posée dans le HTML) --- */
    const links = document.querySelectorAll(".nav-menu .nav-link");
    if (links.length && !document.querySelector(".nav-menu .nav-link.is-active")) {
        let page = window.location.pathname.split("/").pop();
        if (!page) page = "index.html";
        links.forEach((link) => {
            if (link.getAttribute("href") === page) {
                link.classList.add("is-active");
                link.setAttribute("aria-current", "page");
            }
        });
    }

    /* --- Tiroir historique de la page Chat (mobile) --- */
    const app = document.querySelector(".app");
    const sidebarToggle = document.getElementById("sidebar-toggle");
    const scrim = document.querySelector(".sidebar-scrim");

    if (app && sidebarToggle) {
        const setOpen = (open) => {
            app.classList.toggle("sidebar-open", open);
            sidebarToggle.setAttribute("aria-expanded", open ? "true" : "false");
        };

        sidebarToggle.addEventListener("click", () => {
            setOpen(!app.classList.contains("sidebar-open"));
        });

        if (scrim) {
            scrim.addEventListener("click", () => setOpen(false));
        }

        // Fermer le tiroir après un clic dans l'historique ou sur "nouvelle conversation"
        app.querySelectorAll(".sidebar").forEach((el) => {
            el.addEventListener("click", (e) => {
                if (window.innerWidth <= 780 &&
                    (e.target.closest(".history-item") || e.target.closest("#new-chat-btn"))) {
                    setOpen(false);
                }
            });
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") setOpen(false);
        });
    }
})();
