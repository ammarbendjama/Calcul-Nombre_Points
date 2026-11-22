"""Interface graphique : Nombre de points de la copie.

Double-clic sur NombrePoints.exe → choisir la vidéo → Analyser → résultats.
Aucune installation ni ligne de commande.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.aggregate import Copie
from app.pipeline import analyser_video

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
        texte = texte.strip()
        if texte:
            self._fenetre.after(0, self._ecrire, texte)

    def _ecrire(self, texte: str) -> None:
        self._widget.configure(state=tk.NORMAL)
        self._widget.insert(tk.END, texte + "\n")
        self._widget.see(tk.END)
        self._widget.configure(state=tk.DISABLED)

    def flush(self) -> None:  # interface fichier
        pass


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nombre de points de la copie")
        self.geometry("760x520")
        self.minsize(640, 420)

        self.video_choisie: str | None = None
        self.en_cours = False

        cadre = ttk.Frame(self, padding=14)
        cadre.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            cadre,
            text="Calcule le nombre de points de chaque copie d'examen à partir d'une vidéo.",
            wraplength=700,
        ).pack(anchor=tk.W)

        boutons = ttk.Frame(cadre)
        boutons.pack(fill=tk.X, pady=8)
        self.btn_choisir = ttk.Button(boutons, text="1. Choisir la vidéo…", command=self.choisir_video)
        self.btn_choisir.pack(side=tk.LEFT)
        self.btn_analyser = ttk.Button(boutons, text="2. Analyser", command=self.lancer_analyse, state=tk.DISABLED)
        self.btn_analyser.pack(side=tk.LEFT, padx=8)
        self.btn_resultats = ttk.Button(boutons, text="3. Ouvrir les résultats", command=self.ouvrir_resultats, state=tk.DISABLED)
        self.btn_resultats.pack(side=tk.LEFT)

        self.label_video = ttk.Label(cadre, text="Aucune vidéo choisie.")
        self.label_video.pack(anchor=tk.W)

        self.progression = ttk.Progressbar(cadre, mode="indeterminate")

        colonnes = ("copie", "pages", "zones", "points")
        arbre = ttk.Treeview(cadre, columns=colonnes, show="headings", height=8)
        for col, texte, largeur in zip(colonnes, ("Copie", "Pages", "Notes lues", "Points"), (80, 80, 100, 100)):
            arbre.heading(col, text=texte)
            arbre.column(col, width=largeur, anchor=tk.CENTER)
        arbre.pack(fill=tk.X, pady=8)
        self.arbre = arbre

        self.label_total = ttk.Label(cadre, text="", font=("TkDefaultFont", 11, "bold"))
        self.label_total.pack(anchor=tk.W)

        ttk.Label(cadre, text="Journal :").pack(anchor=tk.W)
        journal = tk.Text(cadre, height=8, state=tk.DISABLED, font=("Tk Fixed Font", 9))
        journal.pack(fill=tk.BOTH, expand=True)
        self.journal = journal

    def choisir_video(self) -> None:
        chemin = filedialog.askopenfilename(title="Choisir la vidéo des copies", filetypes=EXTENSIONS)
        if chemin:
            self.video_choisie = chemin
            self.label_video.configure(text=f"Vidéo : {Path(chemin).name}")
            self.btn_analyser.configure(state=tk.NORMAL)

    def lancer_analyse(self) -> None:
        if self.en_cours or not self.video_choisie:
            return
        self.en_cours = True
        self.btn_analyser.configure(state=tk.DISABLED)
        self.btn_choisir.configure(state=tk.DISABLED)
        self.arbre.delete(*self.arbre.get_children())
        self.label_total.configure(text="")
        self.progression.pack(fill=tk.X, pady=4)
        self.progression.start(12)
        threading.Thread(target=self._analyser, daemon=True).start()

    def _analyser(self) -> None:
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
        except Exception as erreur:  # noqa: BLE001 - message utilisateur
            self.after(0, self._echec, str(erreur))
            return
        self.after(0, self._termine, copies, sortie)

    def _echec(self, message: str) -> None:
        self._fin_analyse()
        messagebox.showerror("Erreur", message, parent=self)

    def _termine(self, copies: list[Copie], sortie: str) -> None:
        self._fin_analyse()
        total = 0.0
        for copie in copies:
            self.arbre.insert("", tk.END, values=(
                copie.numero, len(copie.apercus), len(copie.zones), f"{copie.total:g}".replace(".", ",")
            ))
            total += copie.total
        self.label_total.configure(
            text=f"Total : {f'{total:g}'.replace('.', ',')} points sur {len(copies)} copie(s)"
        )
        self.btn_resultats.configure(state=tk.NORMAL)
        self.dossier_resultats = sortie

    def _fin_analyse(self) -> None:
        self.progression.stop()
        self.progression.pack_forget()
        self.en_cours = False
        self.btn_choisir.configure(state=tk.NORMAL)
        self.btn_analyser.configure(state=tk.NORMAL if self.video_choisie else tk.DISABLED)

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
