"""Dessine le schéma de la chaîne de traitement (rapport/figures/fig00_chaine.png)."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SORTIE = Path(__file__).resolve().parents[1] / "rapport" / "figures" / "fig00_chaine.png"
plt.rcParams["font.family"] = "Times New Roman"

BLEU, OR, VIOLET, NUIT = "#1f5bff", "#c58c12", "#7c5cff", "#0b1a33"

fig, ax = plt.subplots(figsize=(10, 4.2), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 42)
ax.axis("off")


def boite(x, y, l, h, texte, couleur=NUIT, taille=10.5):
    ax.add_patch(FancyBboxPatch((x, y), l, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                linewidth=1.3, edgecolor=couleur, facecolor="white"))
    ax.text(x + l / 2, y + h / 2, texte, ha="center", va="center", fontsize=taille, color=NUIT)


def fleche(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, linewidth=1.1, color=NUIT))


# Entrée
boite(1, 17, 12, 8, "Fichier WAV\noriginal")
boite(17, 17, 12, 8, "Extrait\n0 à 20 s")
fleche(13.8, 21, 16.2, 21)

# Séparation en trois bandes
bandes = [
    (31, "Graves\npasse-bas 250 Hz", BLEU),
    (17, "Médiums\npasse-bas 4 kHz − passe-bas 250 Hz", OR),
    (3, "Aigus\nsignal − passe-bas 4 kHz", VIOLET),
]
gains = ["× 10^(G_g / 20)", "× 10^(G_m / 20)", "× 10^(G_a / 20)"]
for (y, texte, couleur), gain in zip(bandes, gains):
    boite(34, y, 24, 8, texte, couleur, 10)
    boite(62, y, 12, 8, gain, couleur, 10)
    fleche(29.8, 21, 33.2, y + 4)
    fleche(58.8, y + 4, 61.2, y + 4)
    fleche(74.8, y + 4, 77.6, 21)

# Recombinaison et sortie
ax.add_patch(plt.Circle((80, 21), 2.3, fill=False, linewidth=1.3, color=NUIT))
ax.text(80, 21, "+", ha="center", va="center", fontsize=14, color=NUIT)
boite(85, 26, 13.5, 9, "Contrôle de crête\n(abaissement à\n−1 dBFS si > 0 dBFS)", NUIT, 9)
boite(85, 8, 13.5, 8, "Fichier WAV\négalisé", NUIT, 10)
fleche(82.3, 21, 85.6, 29)
fleche(91.75, 25.4, 91.75, 16.6)

ax.text(46, 40.5, "Séparation en trois bandes", ha="center", fontsize=10, style="italic", color=NUIT)
ax.text(68, 40.5, "Gains", ha="center", fontsize=10, style="italic", color=NUIT)
ax.text(80, 16.5, "Somme", ha="center", fontsize=9.5, style="italic", color=NUIT)

fig.tight_layout()
SORTIE.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(SORTIE, bbox_inches="tight", facecolor="white")
print(SORTIE)
