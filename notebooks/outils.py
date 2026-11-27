"""Outils partagés par les notebooks : mesurer, dessiner, écouter.

Ce fichier ne contient aucun filtre. Il n'est pas nécessaire de le lire pour
comprendre les notebooks : il évite seulement de répéter le code des graphiques.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Audio, display

FS = 44_100  # fréquence d'échantillonnage : 44 100 échantillons par seconde

NUIT, BLEU, OR, VIOLET, GRIS, ROUGE = "#0b1a33", "#1f5bff", "#c58c12", "#7c5cff", "#9aa6bb", "#e5484d"
COULEURS_NOTES = [BLEU, OR, VIOLET]

# Figures de 900 pixels de large au plus : elles tiennent sur un écran de portable sans être réduites.
LARGEUR = 9
plt.rcParams.update({
    "figure.dpi": 100, "font.size": 11, "axes.grid": True, "grid.alpha": 0.25,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "legend.fontsize": 9.5, "legend.framealpha": 0.9,
})


# ---------------------------------------------------------------------------
# Mesures
# ---------------------------------------------------------------------------
def en_db(rapport):
    """Rapport d'amplitudes -> décibels (×2 -> +6 dB, ×0,5 -> −6 dB)."""
    return 20 * np.log10(np.abs(rapport))


def amplitude_a(signal, f):
    """Amplitude de la sinusoïde de fréquence f contenue dans le signal (lue dans la FFT).

    La lecture est exacte quand le signal contient un nombre entier de périodes de f.
    """
    N = len(signal)
    k = int(round(f * N / FS))  # numéro de la case de la FFT qui correspond à f
    return 2 * np.abs(np.fft.rfft(signal)[k]) / N


def spectre_db(signal):
    """Spectre du signal : (fréquences en Hz, amplitudes en dB)."""
    N = len(signal)
    amplitudes = 2 * np.abs(np.fft.rfft(signal)) / N
    return np.fft.rfftfreq(N, 1 / FS), 20 * np.log10(np.maximum(amplitudes, 1e-6))


def gain_a(filtre, f, duree=0.4):
    """Gain du filtre à la fréquence f, mesuré : on envoie une sinusoïde d'amplitude 1
    et on mesure l'amplitude qui ressort (la première moitié, où le filtre démarre, est ignorée)."""
    t = np.arange(int(duree * FS)) / FS
    sortie = filtre(np.sin(2 * np.pi * f * t))
    return amplitude_a(sortie[len(t) // 2:], f)


def reponse_mesuree(filtre, frequences=None):
    """Réponse en fréquence mesurée : le gain du filtre pour une série de fréquences de 30 Hz à 20 kHz."""
    if frequences is None:
        frequences = np.unique(np.round(np.logspace(np.log10(30), np.log10(20_000), 40) / 10) * 10)
    return frequences, np.array([gain_a(filtre, f) for f in frequences])


def ecouter(signal, titre):
    """Lecteur audio au niveau réel (sans normalisation). Refuse un signal qui dépasse ±1."""
    crete = np.max(np.abs(signal))
    print(f"{titre} — crête : {crete:.2f}")
    if crete > 1:
        print("  Le signal dépasse 1 : il serait écrêté (distordu). Lecture refusée.")
        return
    display(Audio(signal, rate=FS, normalize=False))


# ---------------------------------------------------------------------------
# Graphiques
# ---------------------------------------------------------------------------
def _axe_frequences(ax):
    ticks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    ax.set_xscale("log")
    ax.set_xlim(20, FS / 2)
    ax.set_xticks(ticks, ["20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "20k"])
    ax.set_xlabel("Fréquence (Hz, échelle logarithmique)")


def _coupures(ax, coupures):
    for i, fc in enumerate(coupures):
        ax.axvline(fc, color=OR, ls="--", lw=1.2, label="Coupure" if i == 0 else None)


def _legende_en_haut(ax, ncol=2):
    """Agrandit le haut du graphique pour que la légende ne cache pas les courbes."""
    bas, haut = ax.get_ylim()
    ax.set_ylim(bas, haut + 0.4 * (haut - bas))
    ax.legend(loc="upper right", ncol=ncol)


def _fenetre(t, duree_ms, debut=0.5):
    masque = (t >= debut) & (t < debut + duree_ms / 1000)
    return masque, (t[masque] - debut) * 1000


def figure_echantillons():
    """Un son grave et un son aigu, puis un zoom qui montre les échantillons."""
    t = np.arange(int(0.01 * FS)) / FS
    grave, aigu = np.sin(2 * np.pi * 100 * t), np.sin(2 * np.pi * 1000 * t)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(LARGEUR, 6))
    ax1.plot(t * 1000, grave, color=BLEU, lw=2, label="Grave : 100 Hz")
    ax1.plot(t * 1000, aigu, color=VIOLET, lw=1.2, label="Aigu : 1 000 Hz")
    ax1.set(title="Grave = oscillation lente, aigu = oscillation rapide", xlabel="Temps (ms)", ylabel="Amplitude")
    _legende_en_haut(ax1)
    zoom = t < 0.001
    ax2.plot(t[zoom] * 1000, aigu[zoom], color=VIOLET, lw=1, alpha=0.5, label="Le son")
    ax2.plot(t[zoom] * 1000, aigu[zoom], "o", color=VIOLET, ms=4, label="Les échantillons")
    ax2.set(title="Zoom sur 1 ms : un signal numérique est une suite de points", xlabel="Temps (ms)", ylabel="Amplitude")
    _legende_en_haut(ax2)
    fig.tight_layout()
    plt.show()


def tracer_signal(t, sinusoides, x, coupures, zone):
    """Le signal de test : dans le temps (zoom 20 ms) et en spectre."""
    masque, t_ms = _fenetre(t, 20)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(LARGEUR, 7))
    for (nom, s), couleur in zip(sinusoides.items(), COULEURS_NOTES):
        ax1.plot(t_ms, s[masque], color=couleur, lw=1, alpha=0.6, label=nom)
    ax1.plot(t_ms, x[masque], color=NUIT, lw=1.8, label="Somme = signal de test")
    ax1.set(title="Le signal de test dans le temps (zoom sur 20 ms)", xlabel="Temps (ms)", ylabel="Amplitude")
    _legende_en_haut(ax1)
    f, db = spectre_db(x)
    ax2.plot(f[1:], db[1:], color=NUIT, lw=1.4, label="Spectre")
    ax2.axvspan(*zone, color=OR, alpha=0.1, label="Zone à garder")
    _coupures(ax2, coupures)
    _axe_frequences(ax2)
    ax2.set(title="Le spectre du signal de test : un pic par note", ylabel="Amplitude (dB)", ylim=(-80, 0))
    ax2.legend(loc="upper right")
    fig.tight_layout()
    plt.show()


def tracer_avant_apres(t, x, cible, nom_cible, sorties, duree_ms, titre):
    """Avant / après filtrage dans le temps. `sorties` : liste de (signal, couleur, étiquette)."""
    masque, t_ms = _fenetre(t, duree_ms)
    fig, ax = plt.subplots(figsize=(LARGEUR, 4))
    ax.plot(t_ms, x[masque], color=GRIS, lw=1, label="Avant")
    ax.plot(t_ms, cible[masque], color=NUIT, lw=1.2, ls=":", label=f"Objectif : {nom_cible}")
    for signal, couleur, etiquette in sorties:
        ax.plot(t_ms, signal[masque], color=couleur, lw=2, label=etiquette)
    ax.set(title=titre, xlabel="Temps (ms)", ylabel="Amplitude")
    _legende_en_haut(ax)
    fig.tight_layout()
    plt.show()


def tracer_spectres(x, sorties, notes, coupures):
    """Spectres avant / après filtrage."""
    fig, ax = plt.subplots(figsize=(LARGEUR, 4))
    f, db = spectre_db(x)
    ax.plot(f[1:], db[1:], color=GRIS, lw=1.2, label="Avant")
    for signal, couleur, etiquette in sorties:
        ax.plot(f[1:], spectre_db(signal)[1][1:], color=couleur, lw=1.2, label=etiquette)
    _coupures(ax, coupures)
    _axe_frequences(ax)
    ax.set(title="Spectres avant / après", ylabel="Amplitude (dB)", ylim=(-110, 0))
    ax.legend(loc="lower left")
    fig.tight_layout()
    plt.show()


def tableau_notes(x, sorties, notes):
    """Ce que chaque filtre a fait à chaque note, en dB (0 = inchangée, −20 = divisée par 10)."""
    lignes = []
    for nom, (f, A) in notes.items():
        ligne = {"Note": nom}
        for signal, _, etiquette in sorties:
            ligne[etiquette] = en_db(amplitude_a(signal, f) / amplitude_a(x, f))
        lignes.append(ligne)
    return pd.DataFrame(lignes).set_index("Note").style.format("{:+.1f} dB")


def tracer_reponses(courbes, coupures, ideal):
    """Réponses en fréquence mesurées. `courbes` : liste de (fréquences, gains, couleur, étiquette)."""
    fig, ax = plt.subplots(figsize=(LARGEUR, 4.2))
    ax.plot(*ideal, color=GRIS, lw=2.5, alpha=0.6, label="Filtre idéal (impossible)")
    for frequences, gains, couleur, etiquette in courbes:
        ax.plot(frequences, en_db(np.maximum(gains, 1e-6)), "-o", color=couleur, lw=1.8, ms=3, label=etiquette)
    ax.axhline(-3, color=NUIT, ls=":", lw=1, label="−3 dB")
    _coupures(ax, coupures)
    _axe_frequences(ax)
    ax.set(title="Réponse en fréquence : ce que le filtre laisse passer", ylabel="Gain (dB)", ylim=(-80, 5))
    ax.legend(loc="lower right")
    fig.tight_layout()
    plt.show()


def tracer_egalisation(t, x, x_eq, morceaux, notes, coupures, titre_apres, duree_ms=20):
    """Deux figures : (1) séparation et signal avant / après dans le temps, (2) spectres avant / après."""
    masque, t_ms = _fenetre(t, duree_ms)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(LARGEUR, 6.5))
    ax1.plot(t_ms, x[masque], color=GRIS, lw=1.2, label="Signal de test")
    for signal, couleur, etiquette in morceaux:
        ax1.plot(t_ms, signal[masque], color=couleur, lw=1.6, label=etiquette)
    ax1.set(title="1. Séparer les bandes", xlabel="Temps (ms)", ylabel="Amplitude")
    _legende_en_haut(ax1, ncol=4)
    ax2.plot(t_ms, x[masque], color=GRIS, lw=1.6, label="Avant")
    ax2.plot(t_ms, x_eq[masque], color=BLEU, lw=1.8, label=f"Après : {titre_apres}")
    ax2.axhline(1, color=ROUGE, ls="--", lw=1)
    ax2.axhline(-1, color=ROUGE, ls="--", lw=1, label="Limite ±1")
    ax2.set(title="2. Le signal avant / après le gain", xlabel="Temps (ms)", ylabel="Amplitude")
    _legende_en_haut(ax2, ncol=3)
    fig.tight_layout()
    plt.show()

    fig, ax = plt.subplots(figsize=(LARGEUR, 4))
    f, db = spectre_db(x)
    ax.plot(f[1:], db[1:], color=GRIS, lw=1.4, label="Avant")
    ax.plot(f[1:], spectre_db(x_eq)[1][1:], color=BLEU, lw=1.4, label="Après")
    for nom, (freq, A) in notes.items():
        variation = en_db(amplitude_a(x_eq, freq) / amplitude_a(x, freq))
        ax.annotate(f"{variation:+.1f} dB", (freq, en_db(amplitude_a(x_eq, freq))), xytext=(0, 8),
                    textcoords="offset points", ha="center", color=BLEU, fontweight="bold")
    _coupures(ax, coupures)
    _axe_frequences(ax)
    ax.set(title="3. Les spectres avant / après", ylabel="Amplitude (dB)", ylim=(-110, 12))
    ax.legend(loc="lower left")
    fig.tight_layout()
    plt.show()


def tableau_gains(x, x_eq, notes, voulus):
    """Gain voulu et gain obtenu pour chaque note."""
    lignes = [{"Note": nom, "Gain voulu": voulus[nom], "Gain obtenu": en_db(amplitude_a(x_eq, f) / amplitude_a(x, f))}
              for nom, (f, A) in notes.items()]
    return pd.DataFrame(lignes).set_index("Note").style.format("{:+.1f} dB")
