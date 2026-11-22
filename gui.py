"""Interface graphique : Nombre de points de la copie.

Bouton "Caméra" : ouvre la caméra en direct avec aperçu, capture automatique
des pages stables, détection des changements de copie, total en temps réel.
Bouton "Vidéo" : analyse d'un fichier vidéo existant.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from app.aggregate import Copie, Zone, exporter_csv, exporter_json
from app.extractor import iterer_pages_camera
from app.pipeline import SessionOcr, analyser_page, analyser_video

EXTENSIONS = [
    ("Vidéos", "*.mp4 *.avi *.mov *.mkv *.webm"),
    ("Tous les fichiers", "*.*"),
]


class JournalTk:
    """Redirige les print du pipeline vers la zone de journal de la fenêtre."""

    def __init__(self, fenetre, widget_text):
        self._fenetre = fenetre
        self._widget = widget_text

    def write(self, texte: str) -> None:
        texte = texte.rstrip("\n")
        if texte.strip():
            self._fenetre.after(0, self._ecrire, texte)

    def _ecrire(self, texte: str) -> None:
        self._widget.configure(state=tk.NORMAL)
        self._widget.insert(tk.END, texte + "\n")
        self._widget.see(tk.END)
        self._widget.configure(state=tk.DISABLED)

    def flush(self) -> None:
        pass


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nombre de points de la copie")
        self.geometry("920x640")
        self.minsize(760, 540)

        self.video_choisie: str | None = None
        self.en_cours = False
        self.stop_event = threading.Event()
        self.cap_camera = None
        self._photo: ImageTk.PhotoImage | None = None
        self._cadre_affiche = 0

        self.copie_courante: Copie | None = None
        self.copies_fermees: list[Copie] = []
        self.prochaine_numero = 1

        cadre = ttk.Frame(self, padding=12)
        cadre.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            cadre,
            text="Appuyez sur « Caméra », présentez chaque page bien à plat et sans ombre : "
            "l'app lit les notes (ex. 1,5/2) et calcule les points de chaque copie.",
            wraplength=880,
        ).pack(anchor=tk.W)

        boutons = ttk.Frame(cadre)
        boutons.pack(fill=tk.X, pady=8)
        self.btn_camera = ttk.Button(boutons, text="🎥 Caméra", command=self.camera)
        self.btn_camera.pack(side=tk.LEFT)
        self.btn_arret = ttk.Button(boutons, text="⏹ Arrêter", command=self.arreter_camera, state=tk.DISABLED)
        self.btn_arret.pack(side=tk.LEFT, padx=6)
        self.btn_nouvelle = ttk.Button(boutons, text="➕ Nouvelle copie", command=self.nouvelle_copie, state=tk.DISABLED)
        self.btn_nouvelle.pack(side=tk.LEFT)
        self.btn_video = ttk.Button(boutons, text="🎞️ Fichier vidéo…", command=self.choisir_video)
        self.btn_video.pack(side=tk.LEFT, padx=6)
        self.btn_resultats = ttk.Button(boutons, text="📂 Résultats", command=self.ouvrir_resultats, state=tk.DISABLED)
        self.btn_resultats.pack(side=tk.LEFT)

        zones = ttk.Frame(cadre)
        zones.pack(fill=tk.BOTH, expand=True)

        gauche = ttk.Frame(zones)
        gauche.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(gauche, width=480, height=360, bg="#101820", highlightthickness=0)
        self.canvas.pack(pady=(0, 6))
        self.label_etat = ttk.Label(gauche, text="Caméra éteinte — appuyez sur 🎥 Caméra.")
        self.label_etat.pack()

        droite = ttk.Frame(zones)
        droite.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))
        colonnes = ("copie", "pages", "notes", "points")
        self.arbre = ttk.Treeview(droite, columns=colonnes, show="headings", height=8)
        for col, texte, largeur in zip(colonnes, ("Copie", "Pages", "Notes", "Points"), (60, 60, 70, 90)):
            self.arbre.heading(col, text=texte)
            self.arbre.column(col, width=largeur, anchor=tk.CENTER)
        self.arbre.pack(fill=tk.X)
        self.label_total = ttk.Label(droite, text="", font=("TkDefaultFont", 12, "bold"))
        self.label_total.pack(anchor=tk.W, pady=6)
        ttk.Label(droite, text="Journal :").pack(anchor=tk.W)
        journal = tk.Text(droite, height=10, state=tk.DISABLED, font=("Tk Fixed Font", 9))
        journal.pack(fill=tk.BOTH, expand=True)
        self.journal = journal

    # ---------- caméra en direct ----------

    def camera(self) -> None:
        if self.en_cours:
            return
        self.en_cours = True
        self.stop_event.clear()
        self.btn_camera.configure(state=tk.DISABLED)
        self.btn_video.configure(state=tk.DISABLED)
        self.btn_arret.configure(state=tk.NORMAL)
        self.btn_nouvelle.configure(state=tk.NORMAL)
        threading.Thread(target=self._flux_camera, daemon=True).start()

    def arreter_camera(self) -> None:
        self.stop_event.set()

    def _flux_camera(self) -> None:
        try:
            self.cap_camera, pages = iterer_pages_camera(
                0, stop_event=self.stop_event, sur_frame=self._afficher_apercu_differe
            )
        except RuntimeError as erreur:
            self.after(0, self._echec, str(erreur))
            return

        session = SessionOcr("rapidocr")
        try:
            for image, nouvelle in pages:
                if nouvelle or self.copie_courante is None:
                    self._fermer_copie()
                    self.copie_courante = Copie(numero=self.prochaine_numero)
                    self.prochaine_numero += 1
                nb_pages = len(self.copie_courante.apercus) + 1
                notes, annotation = analyser_page(image, session, 8, 0.5, False)
                for zone_box, note in notes:
                    self.copie_courante.zones.append(
                        Zone(page=nb_pages, index_image=-1, boite=zone_box, note=note)
                    )
                self.copie_courante.apercus.append("")
                chemin = Path("resultats-camera") / "pages" / f"copie{self.copie_courante.numero:03d}_page{nb_pages:02d}.png"
                chemin.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(chemin), annotation)
                self.copie_courante.apercus[-1] = str(chemin)
                self.after(0, self._page_traitee, len(notes), nouvelle)
        finally:
            if self.cap_camera is not None:
                self.cap_camera.release()
                self.cap_camera = None
            self.after(0, self._fin_flux)

    def _afficher_apercu_differe(self, image) -> None:
        self._cadre_affiche += 1
        if self._cadre_affiche % 3 == 0:
            self.after(0, self._afficher_apercu, image)

    def _afficher_apercu(self, image) -> None:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        inter = Image.fromarray(rgb).resize((480, 360))
        self._photo = ImageTk.PhotoImage(inter)
        self.canvas.create_image(0, 0, image=self._photo, anchor=tk.NW)
        self.label_etat.configure(
            text="Caméra active — gardez la page immobile 1 s ; tournez la page ou écartez la copie pour la page suivante."
        )

    def _page_traitee(self, nb_notes: int, nouvelle: bool) -> None:
        prefixe = "[NOUVELLE COPIE] " if nouvelle else ""
        print(f"{prefixe}page analysée : {nb_notes} note(s)")
        self._rafraichir_tableau()

    # ---------- table des résultats ----------

    def _fermer_copie(self) -> None:
        if self.copie_courante is not None:
            self.copies_fermees.append(self.copie_courante)
            self.copie_courante = None

    def nouvelle_copie(self) -> None:
        self._fermer_copie()
        self.copie_courante = Copie(numero=self.prochaine_numero)
        self.prochaine_numero += 1
        print("Nouvelle copie (manuelle)")
        self._rafraichir_tableau()

    def _rafraichir_tableau(self) -> None:
        self.arbre.delete(*self.arbre.get_children())
        total = 0.0
        copies = self.copies_fermees + ([self.copie_courante] if self.copie_courante else [])
        for copie in copies:
            total += copie.total
            self.arbre.insert("", tk.END, values=(
                copie.numero, len(copie.apercus), len(copie.zones), f"{copie.total:g}".replace(".", ",")
            ))
        self.label_total.configure(
            text=f"Total : {f'{total:g}'.replace('.', ',')} points sur {len(copies)} copie(s)"
        )

    # ---------- fichier vidéo ----------

    def choisir_video(self) -> None:
        chemin = filedialog.askopenfilename(title="Choisir la vidéo des copies", filetypes=EXTENSIONS)
        if chemin:
            self.video_choisie = chemin
            threading.Thread(target=self._analyser_fichier, daemon=True).start()

    def _analyser_fichier(self) -> None:
        sortie = str(Path(self.video_choisie).parent / "resultats")
        args = argparse.Namespace(
            video=self.video_choisie,
            sortie=sortie,
            moteur="rapidocr",
            pas_echantillon=5,
            seuil_similarite=0.97,
            pages_par_copie=0,
            marge=8,
            confiance_min=0.5,
            accepter_entiers=False,
        )
        try:
            copies = analyser_video(args)
            exporter_csv(copies, Path(sortie) / "report.csv")
            exporter_json(copies, Path(sortie) / "report.json")
        except Exception as erreur:  # noqa: BLE001 - message utilisateur
            self.after(0, self._echec, str(erreur))
            return
        self.after(0, self._fichier_termine, copies, sortie)

    def _fichier_termine(self, copies, sortie):
        self.copies_fermees = list(copies)
        self.copie_courante = None
        self._rafraichir_tableau()
        self.dossier_resultats = sortie
        self.btn_resultats.configure(state=tk.NORMAL)

    # ---------- divers ----------

    def _echec(self, message: str) -> None:
        self.en_cours = False
        self.btn_camera.configure(state=tk.NORMAL)
        self.btn_video.configure(state=tk.NORMAL)
        self.btn_arret.configure(state=tk.DISABLED)
        self.btn_nouvelle.configure(state=tk.DISABLED)
        messagebox.showerror("Erreur", message, parent=self)

    def _fin_flux(self) -> None:
        self._fermer_copie()
        self._rafraichir_tableau()
        self.en_cours = False
        sortie = Path("resultats-camera")
        exporter_csv(self.copies_fermees, sortie / "report.csv")
        exporter_json(self.copies_fermees, sortie / "report.json")
        self.dossier_resultats = str(sortie)
        self.btn_resultats.configure(state=tk.NORMAL)
        self.btn_camera.configure(state=tk.NORMAL)
        self.btn_video.configure(state=tk.NORMAL)
        self.btn_arret.configure(state=tk.DISABLED)
        self.btn_nouvelle.configure(state=tk.DISABLED)
        self.label_etat.configure(text="Caméra arrêtée — résultats dans resultats-camera\\")
        print("Résultats de la caméra écrits dans : resultats-camera/")

    def ouvrir_resultats(self) -> None:
        dossier = getattr(self, "dossier_resultats", None)
        if dossier and Path(dossier).exists():
            if sys.platform == "win32":
                os.startfile(dossier)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{dossier}"')
            else:
                os.system(f'xdg-open "{dossier}" >/dev/null 2>&1 &')


def main() -> int:
    app = Application()
    sys.stdout = JournalTk(app, app.journal)  # type: ignore[assignment]
    sys.stderr = JournalTk(app, app.journal)  # type: ignore[assignment]
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
