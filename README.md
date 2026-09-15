# MiniLLM — Assistant IA local de recherche d'emploi

Un assistant qui tourne **entièrement sur votre machine** : recherche d'offres (LinkedIn, Indeed, Tanitjobs, web), score de compatibilité avec votre profil, génération d'email de candidature avec CV joint, chat local avec votre propre LLM.

Aucune donnée personnelle n'est envoyée à un tiers, à l'exception de la génération d'email si vous activez optionnellement l'API Gemini (désactivée par défaut — le LLM local est utilisé).

---

## Prérequis

- **Python 3.10+**
- **~5 Go d'espace disque** (modèle LLM) et **~10 Go de RAM disponible**
- **cmake** et **g++** (pour compiler llama.cpp)
- Un compte Gmail (pour l'envoi d'email, optionnel mais recommandé)

---

## Installation

### 1. Cloner le dépôt

```bash
git clone <url-du-depot> ~/llm_project
cd ~/llm_project
```

### 2. Compiler llama.cpp

```bash
cd ~/llm_project/third_party/llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j$(nproc)
```

### 3. Télécharger le modèle LLM

```bash
mkdir -p ~/llm_project/models
cd ~/llm_project/models
wget https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf
```

### 4. Installer le backend Python

```bash
cd ~/llm_project/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Configurer vos secrets

```bash
cp .env.example .env
nano .env
```

Remplissez **au minimum** `SMTP_USER` et `SMTP_APP_PASSWORD` si vous voulez envoyer des emails (voir les instructions dans le fichier). Laissez `GEMINI_API_KEY` vide si vous ne voulez pas l'utiliser — tout fonctionne avec le LLM local seul.

⚠️ **Ne partagez jamais votre fichier `.env` rempli.** Il contient vos identifiants.

---

## Lancer l'application

Trois terminaux, dans cet ordre :

```bash
# Terminal 1 — le LLM local
~/llm_project/scripts/start_llm.sh

# Terminal 2 — le backend
cd ~/llm_project/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3 — le frontend
cd ~/llm_project/frontend
python3 -m http.server 5500
```

Ouvrez ensuite **http://127.0.0.1:5500/home.html**.

La page d'accueil affiche un **panneau d'état** qui vérifie automatiquement que tout est bien configuré (LLM, email, profil, CV) et vous indique quoi faire si quelque chose manque.

---

## Fonctionnalités

| Page | Description |
|---|---|
| **Chat** | Discutez avec le LLM local, avec recherche web et contexte de profil activables à la demande |
| **Offres** | Recherchez des offres par mots-clés, région, période, niveau d'expérience et source |
| **Candidature** | Générez un email de candidature (offre précise ou spontanée générique), CV joint automatiquement, validation avant envoi |
| **Profil** | Gérez vos informations, avec extraction automatique depuis votre CV |

---

## Notes de confidentialité

- Le LLM tourne localement (llama.cpp) — vos données ne quittent pas votre machine par défaut
- L'envoi d'email utilise votre propre compte Gmail (SMTP), aucun serveur tiers
- La recherche d'offres LinkedIn/Indeed utilise [JobSpy](https://github.com/speedyapply/JobSpy), qui interroge les résultats publics sans connexion ni cookies
- Gemini (optionnel, désactivé par défaut) enverrait le contenu de votre profil à Google si activé — à activer en connaissance de cause

---

## Licence

Projet personnel, partagé à but éducatif/portfolio. Adaptez-le librement pour votre propre usage.
