"""Pipeline principal : vidéo -> pages -> zones -> OCR -> points par copie."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from .aggregate import Copie, Zone, exporter_csv, exporter_json
from .detector import preparer_ocr, trouver_zones_notes
from .extractor import grouper_copies, iterer_pages
from .ocr import lire_note, ocr_zone
from .recognizer import notes_du_texte


class SessionOcr:
    """Session d'analyse : gère le moteur OCR et n'avertit qu'une seule fois."""

    def __init__(self, moteur: str):
        self.moteur = moteur
        self.avertie = False

    def lire(self, image, zone_box, marge: int, confiance_min: float, accepter_entiers: bool):
        try:
            morceau = preparer_ocr(image, zone_box, marge_px=marge)
            note = lire_note(morceau, accepter_entiers=accepter_entiers, moteur=self.moteur)
        except RuntimeError as erreur:
            if not self.avertie:
                print(f"ATTENTION : {erreur}", file=sys.stderr)
                self.avertie = True
            return None
        if note is None or note.confiance < confiance_min:
            return None
        return note


def analyser_page(image, session: SessionOcr, marge: int, confiance_min: float,
                  accepter_entiers: bool):
    """Analyse une page : retourne ([(boite|None, note)], image_annotée).

    boite vaut None quand la note vient de l'analyse de la page entière
    (filet de sécurité quand la détection de zones n'a rien donné).
    """
    annotation = image.copy()
    resultat = []
    for zone_box in trouver_zones_notes(image):
        note = session.lire(image, zone_box, marge, confiance_min, accepter_entiers)
        if note is None:
            continue
        resultat.append((zone_box, note))
        x, y, l, h = zone_box
        cv2.rectangle(annotation, (x, y), (x + l, y + h), (0, 0, 255), 3)
        cv2.putText(
            annotation,
            f"{note.points:g} pts",
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )

    if not resultat:
        page_complete = preparer_ocr(image, None, marge_px=0)
        texte = ocr_zone(page_complete, moteur=session.moteur) if page_complete is not None else None
        for note in notes_du_texte(texte or ""):
            if note.confiance >= confiance_min * 0.8:
                resultat.append((None, note))
    return resultat, annotation


def analyser_video(args: argparse.Namespace) -> list[Copie]:
    pages: list[tuple[int, object, bool]] = []
    for index, image, nouvelle_copie in iterer_pages(
        args.video, args.pas_echantillon, args.seuil_similarite
    ):
        pages.append((index, image, nouvelle_copie))
        print(
            f"  page unique n°{len(pages)} (image vidéo {index})",
            " [nouvelle copie]" if nouvelle_copie else "",
            flush=True,
        )

    if not pages:
        print("Aucune page détectée dans la vidéo.", file=sys.stderr)
        return []

    flags = [nouvelle for _i, _img, nouvelle in pages]
    groupes = grouper_copies(flags)
    if args.pages_par_copie > 0:
        groupes = [
            list(range(i, min(i + args.pages_par_copie, len(pages))))
            for i in range(0, len(pages), args.pages_par_copie)
        ]

    sortie = Path(args.sortie)
    dossier_pages = sortie / "pages"
    dossier_pages.mkdir(parents=True, exist_ok=True)

    copies: list[Copie] = []
    session = SessionOcr(args.moteur)
    for numero, indices in enumerate(groupes, start=1):
        copie = Copie(numero=numero)
        for ordre, idx in enumerate(indices, start=1):
            index_image, image, _nouvelle = pages[idx]
            notes_trouvees, annotation = analyser_page(
                image, session, args.marge, args.confiance_min, args.accepter_entiers
            )
            for zone_box, note in notes_trouvees:
                copie.zones.append(Zone(page=ordre, index_image=index_image, boite=zone_box, note=note))
            chemin = dossier_pages / f"copie{numero:03d}_page{ordre:02d}.png"
            copie.apercus.append(str(chemin))
            cv2.imwrite(str(chemin), annotation)
            print(f"  copie {numero} page {ordre} : {len(notes_trouvees)} note(s)")
        copies.append(copie)
    return copies
    return copies


def resume(copies: list[Copie]) -> str:
    lignes = ["", "=== RESUME ===", "Copie | Pages | Zones | Points"]
    total_zones = 0
    for copie in copies:
        total_zones += len(copie.zones)
        ligne = f"{copie.numero}     | {len(copie.apercus)}     | {len(copie.zones)}     | {copie.total:g}".rstrip()
        if copie.bareme_total is not None:
            ligne += f" (barème {copie.bareme_total:g})"
        lignes.append(ligne)
    lignes.append(f"Total zones de notes lues : {total_zones}")
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nombre-de-points-de-la-copie",
        description="Calcule le nombre de points de chaque copie d'examen à partir d'une vidéo.",
    )
    parser.add_argument("video", help="chemin de la vidéo (mp4, avi, mov...)")
    parser.add_argument("-o", "--sortie", default="resultats", help="dossier des résultats")
    parser.add_argument("--moteur", choices=["pytesseract", "easyocr", "rapidocr"], default="pytesseract")
    parser.add_argument("--pas-echantillon", type=int, default=5, help="1 image analysée tous les N (défaut 5)")
    parser.add_argument("--seuil-similarite", type=float, default=0.97, help="similarité min pour rester même page")
    parser.add_argument("--pages-par-copie", type=int, default=0, help="forcer N pages par copie (0 = auto)")
    parser.add_argument("--marge", type=int, default=8, help="marge autour de chaque zone (px)")
    parser.add_argument("--confiance-min", type=float, default=0.5, help="confiance OCR minimale")
    parser.add_argument("--accepter-entiers", action="store_true", help="accepter les notes entières seules (ex: 2)")

    args = parser.parse_args(argv)
    if not Path(args.video).exists():
        parser.error(f"vidéo introuvable : {args.video}")

    print(f"Analyse de {args.video} ...")
    copies = analyser_video(args)
    print(resume(copies))

    sortie = Path(args.sortie)
    exporter_csv(copies, sortie / "report.csv")
    exporter_json(copies, sortie / "report.json")
    print(f"\nRésultats écrits dans : {sortie.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
