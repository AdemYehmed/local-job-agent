/* ============================================================
   home-profile.js — barre de profil animée sur la page d'accueil
   ============================================================ */

(function () {
    const ROLES = [
        "Ingénieur en Génie Électrique",
        "Systèmes Embarqués",
        "Intelligence Artificielle",
        "Auteur de MiniLLM",
    ];

    const el = document.getElementById("typed-role");
    if (el) {
        let roleIndex = 0;
        let charIndex = 0;
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

        window.setTimeout(tick, 500);
    }

    const emailBtn = document.getElementById("email-copy-btn");
    if (emailBtn && navigator.clipboard) {
        emailBtn.addEventListener("click", (e) => {
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
        });
    }
})();
