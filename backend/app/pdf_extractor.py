import pymupdf as fitz
from pathlib import Path

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extrait tout le texte d'un fichier PDF.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"Fichier PDF introuvable : {pdf_path}")

    text_parts = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ValueError("Aucun texte extrait du PDF (peut-être un PDF scanné/image).")

    return full_text
