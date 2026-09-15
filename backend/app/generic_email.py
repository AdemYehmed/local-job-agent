import re
from app.websearch import web_search

GENERIC_SUBJECT = "Candidature spontanée – Ingénieur en Génie Électrique et Systèmes Embarqués"

GENERIC_BODY_TEMPLATE = """Bonjour Madame, Monsieur,
Je me permets de vous adresser ma candidature spontanée afin de rejoindre {company} en tant que jeune ingénieur en génie électrique et systèmes embarqués.
Récemment diplômé, je souhaite aujourd'hui intégrer une entreprise dans laquelle je pourrais mettre à profit ma formation, mes expériences professionnelles, ma motivation et ma capacité d'adaptation.
Mes différentes expériences m'ont permis de développer mon autonomie, ma rigueur, mon esprit d'équipe ainsi que ma capacité à m'adapter à différents environnements professionnels.
Très motivé à l'idée de rejoindre vos équipes, je serais heureux de pouvoir échanger avec vous concernant les opportunités actuelles ou futures correspondant à mon profil.
Vous trouverez mon CV en pièce jointe pour plus d'informations sur mon parcours.
Je vous remercie pour l'attention portée à ma candidature.
Cordialement,
{name}"""

EMAIL_REGEX = re.compile(r'[\w\.\-]+@[\w\.\-]+\.[A-Za-z]{2,24}')


def build_fixed_generic_email(company_name: str, candidate_name: str) -> dict:
    """
    Génère l'email générique à partir du TEMPLATE FIXE (pas de LLM),
    seul le nom de l'entreprise et du candidat changent.
    """
    return {
        "subject": GENERIC_SUBJECT,
        "body": GENERIC_BODY_TEMPLATE.format(company=company_name, name=candidate_name),
    }


def find_company_hr_email(company_name: str) -> str:
    """
    Cherche un email de contact/RH pour l'entreprise via recherche web.
    Extraction déterministe (regex), pas de LLM : fiable mais peut ne rien trouver.
    """
    queries = [
        f'"{company_name}" email recrutement RH Tunisie',
        f'"{company_name}" contact careers email',
        f'"{company_name}" "@gmail.com" OR "@{company_name.lower().replace(" ", "")}.com" recrutement',
        f"{company_name} ressources humaines email contact",
        f"{company_name} tanitjobs.com contact",
    ]
    seen_emails = set()
    for query in queries:
        results = web_search(query, max_results=5)
        for r in results:
            text = f"{r.get('title', '')} {r.get('snippet', '')}"
            matches = EMAIL_REGEX.findall(text)
            for m in matches:
                # ignore emails évidemment génériques/non pertinents (ex: noreply, exemple.com)
                if any(bad in m.lower() for bad in ["noreply", "no-reply", "example.com", "domain.com"]):
                    continue
                seen_emails.add(m)
        if seen_emails:
            return sorted(seen_emails)[0]
    return ""
