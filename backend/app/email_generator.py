import json
import re
from pathlib import Path
from app.models import ChatMessage
from app.llm_client import llm_client
from app.generic_email import build_fixed_generic_email, find_company_hr_email

PROFILE_PATH = Path(__file__).parent / "data" / "profile.json"

EMAIL_SYSTEM_PROMPT = """Tu es un assistant qui aide un CANDIDAT à rédiger un email de candidature spontanée.

Contexte important :
- Le CANDIDAT (dont le profil est fourni) est l'AUTEUR de l'email.
- L'email est envoyé PAR le candidat VERS l'entreprise, pour se présenter et proposer sa candidature.
- Le candidat n'a PAS encore été contacté par l'entreprise : c'est une démarche spontanée.
- L'email doit s'adresser au service recrutement de l'entreprise (pas au candidat lui-même).
- La signature à la fin doit être le nom du candidat.

Règles strictes pour le contenu :
- Utilise UNIQUEMENT les informations du profil fourni (compétences, formation, résumé).
- N'invente JAMAIS d'expérience, de compétence ou de projet non mentionné dans le profil.
- Le ton doit être professionnel, direct, sans formules creuses, et SANS répéter la même idée ou la même formule plusieurs fois.
- L'email doit être complet, entre 120 et 180 mots pour le corps, avec formule d'introduction, présentation, lien avec l'offre, et formule de politesse finale.
- Le corps DOIT OBLIGATOIREMENT commencer par une formule d'appel (ex: "Madame, Monsieur," ou "Bonjour,").
- Le corps DOIT OBLIGATOIREMENT se terminer par une formule de politesse (ex: "Cordialement,") suivie du nom complet du candidat, sur des lignes séparées.
- Ne saute JAMAIS ces deux formules, même si le reste du texte est court.

Règle pour l'extraction du destinataire :
- Cherche dans le texte de l'offre une adresse email de contact (recrutement, RH, contact direct, etc.).
- Si tu en trouves une, mets-la dans "recipient_email".
- Si aucune adresse email n'est présente dans le texte de l'offre, laisse "recipient_email" à une chaîne vide "".
- N'invente JAMAIS d'adresse email.

Tu dois répondre STRICTEMENT en JSON valide, sans aucun texte avant ou après, au format :
{
  "subject": "objet de l'email",
  "body": "corps complet de l'email, de la formule d'introduction jusqu'à la signature du candidat",
  "recipient_email": "email trouvé dans l'offre, ou chaîne vide si absent"
}
"""


def load_profile() -> dict:
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_user_prompt(job_text: str, profile: dict) -> str:
    return f"""Voici le profil du CANDIDAT qui écrit cet email (c'est lui l'expéditeur) :
{json.dumps(profile, ensure_ascii=False, indent=2)}

Voici l'offre d'emploi à laquelle le candidat postule spontanément :
{job_text}

Rédige, du point de vue du candidat, l'email de candidature spontanée pour cette offre, signé par le candidat, et extrais l'email destinataire si présent, en respectant le format JSON demandé."""


def build_generic_prompt(company_name: str, profile: dict) -> str:
    return f"""Voici le profil du CANDIDAT qui écrit cet email (c'est lui l'expéditeur) :
{json.dumps(profile, ensure_ascii=False, indent=2)}

Le candidat souhaite envoyer une candidature spontanée GÉNÉRIQUE à l'entreprise "{company_name}",
SANS offre précise en tête (aucun poste particulier n'est visé).

Rédige un email de candidature spontanée générique :
- Ne mentionne AUCUN intitulé de poste précis.
- Reste général : présente le candidat, sa formation, sa motivation à rejoindre l'entreprise.
- Ne liste PAS toutes les compétences techniques une par une : mentionne au maximum 3-4 compétences clés, groupées naturellement dans une phrase.
- N'exprime l'idée de "chercher une opportunité" QU'UNE SEULE FOIS dans tout l'email. Ne répète pas cette idée sous une autre formulation.
- Mentionne que le CV est joint.
- Demande à pouvoir échanger sur les opportunités actuelles ou futures correspondant à son profil.
- Ton professionnel, formules de politesse classiques (Bonjour Madame, Monsieur / Cordialement).
- Le champ "subject" doit être un OBJET D'EMAIL COURT (5-8 mots maximum), par exemple "Candidature spontanée - {company_name}". Ce n'est JAMAIS une phrase complète ni un résumé de l'email.

Réponds en respectant le format JSON demandé (recipient_email doit rester vide, car aucune offre n'est fournie)."""


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("Aucun JSON trouvé dans la réponse du modèle.")
    return json.loads(match.group(0), strict=False)


async def generate_application_email(job_text: str = "", company_name: str = "", generic: bool = False) -> dict:
    profile = load_profile()

    if generic:
        if not company_name.strip():
            raise ValueError("Le nom de l'entreprise est requis pour une candidature spontanée générique.")
        company_clean = company_name.strip()
        fixed = build_fixed_generic_email(company_clean, profile.get("name", ""))
        hr_email = find_company_hr_email(company_clean)
        return {
            "subject": fixed["subject"],
            "body": fixed["body"],
            "candidate_email": profile.get("email", ""),
            "recipient_email": hr_email,
        }

    if not job_text.strip():
        raise ValueError("Le texte de l'offre est requis.")
    user_prompt = build_user_prompt(job_text, profile)

    messages = [
        ChatMessage(role="system", content=EMAIL_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_prompt),
    ]

    raw_response = await llm_client.chat(messages, temperature=0.4, max_tokens=1500)

    try:
        parsed = extract_json(raw_response)
    except (ValueError, json.JSONDecodeError):
        retry_messages = messages + [
            ChatMessage(role="assistant", content=raw_response),
            ChatMessage(role="user", content="Ta réponse n'était pas un JSON valide ou était incomplète. Réponds UNIQUEMENT avec un JSON complet et valide, rien d'autre, avec un body qui va jusqu'à la signature."),
        ]
        raw_response = await llm_client.chat(retry_messages, temperature=0.2, max_tokens=1500)
        parsed = extract_json(raw_response)

    return {
        "subject": parsed.get("subject", ""),
        "body": parsed.get("body", ""),
        "candidate_email": profile.get("email", ""),
        "recipient_email": parsed.get("recipient_email", ""),
    }
