# MiniLLM JobAgent — frontend

Refonte UI/UX complète. **Aucun changement backend, API, endpoint ou logique métier.**
`app.js`, `apply.js` et `profile.js` sont **strictement identiques** aux fichiers d'origine (vérifié octet par octet).

---

## 1. Contenu du dossier

```text
frontend/
├── home.html      ← NOUVEAU : dashboard, page d'entrée
├── home.css       ← NOUVEAU
├── index.html     ← Chat (refonte HTML uniquement)
├── jobs.html      ← Offres — recherche multi-sources (refonte HTML uniquement)
├── jobs.css       ← styles propres à la page offres
├── apply.html     ← Candidature (refonte HTML uniquement)
├── profile.html   ← Profil (refonte HTML uniquement)
├── style.css      ← tokens + navigation globale + composants + page chat
├── apply.css      ← styles propres à la page candidature
├── profile.css    ← styles propres à la page profil
├── logo.svg       ← NOUVEAU : logo / favicon
├── nav.js         ← NOUVEAU : menu mobile + tiroir historique + thème (UI seulement)
├── app.js         ← INCHANGÉ
├── apply.js       ← INCHANGÉ (version avec loadPendingJobOffer)
├── jobs.js        ← INCHANGÉ
├── profile.js     ← INCHANGÉ
├── start.bat      ← lancement Windows
└── README.md
```

La navigation (`Home · Chat · Offres · Candidature · Profil` + badge `● LOCAL`) est présente
sur les 5 pages, avec la page courante marquée dans la couleur d'accent.

---

## 2. Lancer le frontend sous Windows

### Méthode recommandée — serveur local

1. Démarrez d'abord votre backend habituel (il doit écouter sur `http://127.0.0.1:8000`).
2. Double-cliquez sur **`start.bat`**.
3. Le navigateur s'ouvre sur `http://localhost:5500/home.html`.
4. Pour arrêter : fermez la fenêtre noire ou faites `Ctrl + C`.

Équivalent en ligne de commande (PowerShell ou CMD, dans le dossier `frontend`) :

```bat
python -m http.server 5500
```

puis ouvrir `http://localhost:5500/home.html`.

> Si Windows dit que `python` est introuvable : installez Python depuis le Microsoft Store,
> ou utilisez `py -m http.server 5500`, ou l'extension **Live Server** de VS Code
> (clic droit sur `home.html` → *Open with Live Server*).

### Méthode rapide — sans serveur

Double-cliquez simplement sur `home.html`. La navigation et tout le design sont
testables, mais selon la configuration du navigateur les appels `fetch` vers le
backend peuvent être refusés (origine `file://`). Utile pour vérifier l'UI, pas le flux complet.

### Si les appels API échouent (« Failed to fetch » / erreur CORS)

Le frontend appelle toujours `http://127.0.0.1:8000` comme avant. Vérifiez simplement
que votre backend autorise l'origine du serveur de test dans son `CORSMiddleware`
(`http://localhost:5500`). Si votre configuration est déjà `allow_origins=["*"]`,
il n'y a rien à faire. Aucun fichier backend n'a été touché ici.

---

## 3. Checklist de test

### Navigation
- [ ] `home.html` s'ouvre et affiche les 3 cartes.
- [ ] Depuis Home : Chat, Candidature, Profil accessibles (barre + cartes).
- [ ] Depuis Chat : Home, Candidature, Profil accessibles.
- [ ] Depuis Candidature : Home, Chat, Profil accessibles.
- [ ] Depuis Profil : Home, Chat, Candidature accessibles.
- [ ] La page ouverte est bien surlignée en ambre dans la barre.
- [ ] Le logo `◆ MiniLLM` renvoie vers Home depuis n'importe quelle page.

### Chat (`index.html`)
- [ ] `+ nouvelle_conversation` crée une conversation.
- [ ] L'historique s'affiche à gauche et le clic recharge la conversation.
- [ ] Envoi par le bouton **ENVOYER** et par la touche `Entrée`.
- [ ] `Maj + Entrée` insère un retour à la ligne, le textarea grandit tout seul.
- [ ] Pendant la génération : bouton désactivé + spinner, curseur ambre clignotant.
- [ ] La réponse s'écrit token par token, le scroll suit.
- [ ] Le bloc **sources** apparaît sous la réponse quand le backend en renvoie.

### Offres (`jobs.html`)
- [ ] Les offres déjà enregistrées se chargent à l'ouverture (`GET /api/stored-jobs`).
- [ ] Recherche sans mot-clé → message rouge ; sans source cochée → message rouge.
- [ ] Recherche normale → tableau rempli et résumé « X offre(s) retenue(s) sur Y ».
- [ ] Les quatre sources (`web`, `linkedin`, `tanitjobs`, `indeed`) sont bien envoyées.
- [ ] **POSTULER →** ouvre Candidature avec l'offre et l'email pré-remplis.
- [ ] **VIDER L'HISTORIQUE** (`DELETE /api/stored-jobs`) vide le tableau.

### Candidature (`apply.html`)
- [ ] Le statut du CV se charge à l'ouverture (`/api/cv-status`).
- [ ] Une offre envoyée depuis la page Offres arrive pré-remplie avec son message vert.
- [ ] Choix d'un PDF + **UPLOADER** → message vert avec la taille.
- [ ] **GÉNÉRER L'EMAIL** sans offre collée → message rouge.
- [ ] Avec une offre → objet et corps remplis, bouton d'envoi activé.
- [ ] Les champs restent modifiables avant envoi.
- [ ] **VALIDER ET ENVOYER** → fenêtre de confirmation, puis message de succès ou d'erreur.

### Profil (`profile.html`)
- [ ] Les données existantes se chargent à l'ouverture.
- [ ] **EXTRAIRE DEPUIS MON CV** remplit les champs.
- [ ] Ajout/suppression d'une compétence (bouton `+` et touche `Entrée`, croix `×`).
- [ ] Ajout/suppression d'une langue avec son niveau.
- [ ] **ENREGISTRER LE PROFIL** → `Profil enregistré ✓`.
- [ ] Rechargement de la page : les données sont bien revenues.

### Palettes et animations
- [ ] Les quatre pastilles changent la palette instantanément, sur toutes les pages.
- [ ] Le choix est conservé après rechargement et en changeant de page.
- [ ] Le logo se dessine à l'ouverture, la pastille verte respire.
- [ ] Les cartes de Home et les panneaux apparaissent en cascade.

### Responsive
- [ ] 1920×1080 et 1366×768 : deux colonnes, rien de coupé.
- [ ] Tablette (~900 px) : les colonnes passent l'une sous l'autre.
- [ ] Smartphone (~390 px) : menu `☰` fonctionnel, historique du chat accessible
      via le bouton `☰` du header, formulaires utilisables.
- [ ] `F12` → onglet Console : aucune erreur JS.

---

## 4. Ce qui a changé, et ce qui n'a pas changé

**Changé (HTML/CSS/UX uniquement)**
- Barre de navigation globale + page Home.
- Logo SVG animé (également utilisé comme favicon).
- Quatre palettes, choisies par les pastilles en haut à droite, mémorisées dans `localStorage` (clé `minillm-palette`) :
  **Vitrail** (par défaut, porcelaine + outremer + vermillon), **Atelier** (papier chaud + terre de Sienne + sauge),
  **Aube** (lavande + violet d'encre + pêche), **Nuit** (graphite + ambre, l'ancien thème sombre).
- Animations d'entrée en cascade, soulignement animé de l'onglet actif, micro-interactions au survol.
- Système de design unifié : graphite bleuté, accent ambre, vert `LOCAL`, sans-serif pour le contenu et monospace pour les éléments techniques.
- Chat : sidebar avec infos modèle, messages plus lisibles, indicateur de génération, tiroir historique sur mobile.
- Candidature : étapes numérotées 1 → 3, zone d'upload lisible, panneau email séparé.
- Profil : sections Informations / Compétences / Langues, états vides explicites, bouton d'enregistrement collant.
- États hover, focus clavier visible, disabled, loading, success, error ; `prefers-reduced-motion` respecté.

**Non changé**
- `API_BASE = "http://127.0.0.1:8000"`, tous les endpoints, méthodes, corps JSON et réponses.
- Tous les IDs utilisés par le JavaScript :
  `new-chat-btn`, `history-list`, `messages`, `empty-state`, `chat-form`, `chat-input`, `send-btn`,
  `cv-upload`, `upload-cv-btn`, `cv-status`, `job-text`, `generate-btn`, `generate-status`,
  `email-to`, `email-subject`, `email-body`, `send-status`,
  `job-keywords`, `job-region`, `job-timelimit`, `search-jobs-btn`, `search-status`,
  `results-summary`, `jobs-table`, `jobs-table-body`, `clear-jobs-btn`,
  `p-name`, `p-email`, `p-degree`, `p-year`, `p-location`, `p-summary`,
  `skills-chips`, `new-skill-input`, `add-skill-btn`, `languages-list`,
  `new-lang-name`, `new-lang-level`, `add-lang-btn`, `extract-btn`, `extract-status`,
  `save-profile-btn`, `save-status`.
- Les valeurs envoyées au backend depuis la page Offres : sources `web`, `linkedin`, `tanitjobs`, `indeed` ;
  régions `monde`, `tunisie`, `france`, `maroc`, `algerie` ; périodes `tout`, `jour`, `semaine`, `mois`, `annee` ;
  et la clé `sessionStorage` `pendingJobOffer` qui relie Offres → Candidature.
- Les classes CSS lues par le JS : `status-text`, `error`, `success`, `chip`, `chip-remove`,
  `language-row`, `lang-name`, `lang-level`, `history-item`, `active`, `message`, `role-label`,
  `content`, `sources`, `sources-label`, `source-row`, `source-index`, `empty-state`,
  `job-title-cell`, `job-company-empty`, `skill-tag`, `method-badge`, `apply-row-btn`,
  `empty-results`, `source-checkbox`.
- Aucun framework, aucune dépendance externe, aucun accès réseau en dehors de votre backend.

Les seuls IDs ajoutés sont `nav-toggle`, `nav-menu` et `sidebar-toggle`, utilisés uniquement par `nav.js`.
