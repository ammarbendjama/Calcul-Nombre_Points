/* Nombre de points de la copie — version mobile (PWA). */

let travailleur = null;
let notesCopie = [];
let copiesFermees = [];

const elFichier = document.getElementById("fichier");
const elNotes = document.getElementById("notes");
const elTotal = document.getElementById("total");
const elCopies = document.getElementById("copies");
const elResume = document.getElementById("resume");
const elProgress = document.getElementById("progression");
const elBtnCsv = document.getElementById("btn-csv");
const elBouton = document.getElementById("btn-nouvelle");

function formater(n) {
  return n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function majAffichage() {
  elNotes.innerHTML = "";
  let total = 0;
  for (const n of notesCopie) {
    const li = document.createElement("li");
    li.className = n.points === null ? "rate" : "ok";
    if (n.points !== null) total += n.points;
    li.innerHTML = `<span>${n.points === null ? "non reconnu" : formater(n.points) + " pt"}</span><small>${n.texte || ""}</small>`;
    elNotes.appendChild(li);
  }
  elTotal.textContent = formater(total) + " pt";

  elCopies.innerHTML = "";
  copiesFermees.forEach((t, i) => {
    const li = document.createElement("li");
    li.className = "ok";
    li.innerHTML = `<span>Copie ${i + 1}</span><b>${formater(t)} pt</b>`;
    elCopies.appendChild(li);
  });
  elResume.textContent = copiesFermees.length
    ? `Total des ${copiesFermees.length} copie(s) : ${formater(copiesFermees.reduce((a, b) => a + b, 0))} points.`
    : "Aucune copie terminée.";
  elBtnCsv.disabled = copiesFermees.length === 0 && notesCopie.length === 0;
}

const RE_FRACTION = /(\d+(?:[.,]\d+)?)\s*\/\s*(\d+(?:[.,]\d+)?)/g;
const RE_DECIMAL = /(\d+)[.,](\d+)/;

function versNombre(t) {
  return parseFloat(String(t).replace(",", "."));
}

function notesDuTexte(texte) {
  const notes = [];
  RE_FRACTION.lastIndex = 0;
  let m;
  while ((m = RE_FRACTION.exec(texte)) !== null) {
    const points = versNombre(m[1]);
    const bareme = versNombre(m[2]);
    if (bareme > 0 && bareme <= 100 && points <= 2 * bareme) {
      notes.push({ points, texte: m[0], confiance: 0.95 });
    }
    RE_FRACTION.lastIndex = m.index + m[0].length;
  }
  if (notes.length) return notes;
  const d = RE_DECIMAL.exec(texte);
  if (d) return [{ points: versNombre(d[1] + "." + d[2]), texte: d[0], confiance: 0.75 }];
  return notes;
}

async function ocrPage(canvas) {
  if (!travailleur) travailleur = await Tesseract.createWorker("eng");
  const { data } = await travailleur.recognize(canvas);
  return (data.text || "").replace(/\s+/g, " ").trim();
}

async function traiterImage(canvas, etiquette) {
  const indice = notesCopie.push({ points: null, texte: `${etiquette} : lecture en cours…` }) - 1;
  majAffichage();
  let trouvees = [];
  try {
    const texte = await ocrPage(canvas);
    trouvees = notesDuTexte(texte);
  } catch (err) {
    trouvees = [];
  }
  notesCopie.splice(indice, 1);
  if (trouvees.length === 0) {
    notesCopie.push({ points: null, texte: `${etiquette} : aucune note lue` });
  } else {
    trouvees.forEach(t => notesCopie.push({ points: t.points, texte: `${etiquette} → ${t.texte}` }));
  }
  majAffichage();
}

function canvasReduit(source, largeurSource, hauteurSource, dessiner, largeurCible = 1400) {
  const c = document.createElement("canvas");
  const echelle = Math.min(1, largeurCible / Math.max(largeurSource, hauteurSource));
  c.width = Math.round(largeurSource * echelle);
  c.height = Math.round(hauteurSource * echelle);
  dessiner(c.getContext("2d"), c);
  return c;
}

async function pagesDeLaVideo(url, progression) {
  const video = document.createElement("video");
  video.src = url;
  video.muted = true;
  await new Promise((resolu, echec) => {
    video.onloadedmetadata = resolu;
    video.onerror = () => echec(new Error("Vidéo illisible"));
  });
  const pages = [];
  for (let t = 0; t < video.duration; t += 1.5) {
    await new Promise(resolu => {
      video.onseeked = resolu;
      video.currentTime = t;
    });
    const c = canvasReduit(
      video, video.videoWidth, video.videoHeight,
      (ctx, canevas) => ctx.drawImage(video, 0, 0, canevas.width, canevas.height)
    );
    pages.push(c);
    progression(t / video.duration);
  }
  return pages;
}

elBouton.addEventListener("click", () => {
  if (notesCopie.length) {
    copiesFermees.push(notesCopie.reduce((a, n) => a + (n.points || 0), 0));
  }
  notesCopie = [];
  majAffichage();
  elFichier.click();
});

elBtnCsv.addEventListener("click", () => {
  const lignes = ["copie;points"];
  copiesFermees.forEach((t, i) => lignes.push(`${i + 1};${String(t).replace(".", ",")}`));
  if (notesCopie.length) {
    const enCours = notesCopie.reduce((a, n) => a + (n.points || 0), 0);
    lignes.push(`en cours;${String(enCours).replace(".", ",")}`);
  }
  const blob = new Blob([lignes.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "points-copies.csv";
  a.click();
});

elFichier.addEventListener("change", async () => {
  const fichiers = [...elFichier.files];
  elFichier.value = "";
  if (!fichiers.length) return;
  elProgress.style.display = "block";
  elBtnCsv.disabled = true;
  try {
    for (const fichier of fichiers) {
      if (fichier.type.startsWith("video/")) {
        const pages = await pagesDeLaVideo(URL.createObjectURL(fichier),
          p => (elProgress.firstElementChild.style.width = Math.round(p * 100) + "%"));
        for (let i = 0; i < pages.length; i++) {
          await traiterImage(pages[i], `Vidéo ${i + 1}/${pages.length}`);
          elProgress.firstElementChild.style.width = Math.round((i + 1) / pages.length * 100) + "%";
        }
      } else {
        const img = new Image();
        img.src = URL.createObjectURL(fichier);
        await new Promise((resolu, echec) => { img.onload = resolu; img.onerror = echec; });
        const c = canvasReduit(img, img.width, img.height,
          (ctx, canevas) => ctx.drawImage(img, 0, 0, canevas.width, canevas.height));
        await traiterImage(c, "Photo");
      }
    }
  } catch (err) {
    alert("Erreur de lecture : " + err.message);
  }
  elProgress.style.display = "none";
  majAffichage();
});

majAffichage();

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
