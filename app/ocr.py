"""Reconnaissance OCR des notes manuscrites dans une zone de page."""

from __future__ import annotations

from .recognizer import NoteLue, analyser_note

_CONFIG_TESSERACT = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789,."
_OCR_RAPIDE = None


def ocr_zone(image, moteur: str = "pytesseract") -> str | None:
    """Retourne le texte lu dans une image (petite zone découpée)."""
    if image is None or image.size == 0:
        return None

    if moteur == "pytesseract":
        try:
            import pytesseract
        except ImportError as exc:  # pragma: no cover - dépend de l'installation
            raise RuntimeError(
                "pytesseract n'est pas installé : lancez `pip install pytesseract` "
                "et installez le moteur Tesseract (apt install tesseract-ocr)."
            ) from exc
        from PIL import Image

        try:
            texte = pytesseract.image_to_string(Image.fromarray(image), config=_CONFIG_TESSERACT)
        except (RuntimeError, OSError) as exc:
            raise RuntimeError(
                "moteur Tesseract introuvable : installez-le (sudo apt install "
                "tesseract-ocr) ou utilisez --moteur easyocr."
            ) from exc
        return texte.strip() or None
    if moteur == "rapidocr":
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:  # pragma: no cover - dépend de l'installation
            raise RuntimeError(
                "rapidocr n'est pas installé : lancez `pip install rapidocr-onnxruntime`."
            ) from exc
        global _OCR_RAPIDE
        if _OCR_RAPIDE is None:
            _OCR_RAPIDE = RapidOCR()
        resultats, _temps = _OCR_RAPIDE(image)
        if not resultats:
            return None
        return " ".join(str(r[1]) for r in resultats).strip() or None
    if moteur == "easyocr":
        try:
            import easyocr
        except ImportError as exc:  # pragma: no cover - dépend de l'installation
            raise RuntimeError(
                "easyocr n'est pas installé : lancez `pip install easyocr` "
                "(recommandé pour l'écriture manuscrite)."
            ) from exc
        lecteur = easyocr.Reader(["fr"], verbose=False)
        resultats = lecteur.readtext(image)
        if not resultats:
            return None
        return " ".join(str(r[1]) for r in resultats).strip() or None
    raise ValueError(f"Moteur OCR inconnu : {moteur}")


def lire_note(image, accepter_entiers: bool = False, moteur: str = "pytesseract") -> NoteLue | None:
    texte = ocr_zone(image, moteur=moteur)
    return analyser_note(texte, accepter_entiers=accepter_entiers)
