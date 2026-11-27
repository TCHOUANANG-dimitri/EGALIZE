"""Produit les données du rendu : l'extrait brut et les versions égalisées.

    python scripts/generer_versions.py

1. Extrait les 20 premières secondes de donnees/originales/Techno_music_001.wav, sans aucune
   modification des échantillons (même format, même résolution), dans un fichier séparé.
2. Calcule les trois versions égalisées avec les filtres de l'application (egaliseur/filtres.py),
   coupures 250 Hz et 4 kHz.
3. Exporte chaque version en WAV dans donnees/egalisees/ et écrit un tableau d'indicateurs
   (rapport/indicateurs.csv). Si une version dépasse 0 dBFS, son niveau est abaissé à -1 dBFS
   et l'abaissement est noté dans le tableau.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from egaliseur.audio_io import export_audio, read_wav, spectrum_db  # noqa: E402
from egaliseur.filtres import BACKEND  # noqa: E402
from egaliseur.signal_analysis import band_energy_shares, level_stats, to_dbfs  # noqa: E402

SOURCE = RACINE / "donnees" / "originales" / "Techno_music_001.wav"
EXTRAIT = RACINE / "donnees" / "originales" / "Techno_music_001_extrait_0-20s.wav"
SORTIES = RACINE / "donnees" / "egalisees"
INDICATEURS = RACINE / "rapport" / "indicateurs.csv"
DUREE_S = 20
COUPURE_BASSE, COUPURE_HAUTE = 250.0, 4000.0
PLAFOND_DBFS = -1.0

VERSIONS = {
    "version_1": {"bass": 6, "mid": 0, "treble": -1},
    "version_2": {"bass": 0, "mid": 8, "treble": 2},
    "version_3": {"bass": 2, "mid": -1, "treble": 10},
}
NOMS = {"bass": "graves", "mid": "médiums", "treble": "aigus"}


def puissance_par_zone(signal: np.ndarray, fs: int) -> dict[str, float]:
    """Puissance (somme du spectre) dans chaque zone de fréquences."""
    frequences, niveaux = spectrum_db(signal, fs)
    puissance = 10 ** (niveaux / 10)
    zones = {
        "bass": (frequences > 0) & (frequences < COUPURE_BASSE),
        "mid": (frequences >= COUPURE_BASSE) & (frequences < COUPURE_HAUTE),
        "treble": frequences >= COUPURE_HAUTE,
    }
    return {nom: float(np.sum(puissance[masque])) for nom, masque in zones.items()}


def main() -> None:
    # 1. Extrait brut : on copie les échantillons tels quels (aucune conversion)
    fs, brut = wavfile.read(SOURCE)
    extrait_brut = brut[: DUREE_S * fs]
    wavfile.write(EXTRAIT, fs, extrait_brut)
    print(f"Extrait : {EXTRAIT.name} — {fs} Hz, {extrait_brut.shape[1] if extrait_brut.ndim == 2 else 1} canaux, "
          f"{extrait_brut.dtype}, {extrait_brut.shape[0]} échantillons")

    # 2. Versions égalisées
    x = read_wav(EXTRAIT).samples
    bandes = BACKEND.split_bands(x, fs, COUPURE_BASSE, COUPURE_HAUTE)
    stats_x = level_stats(x)
    zones_x = puissance_par_zone(x, fs)
    parts_x = band_energy_shares(*spectrum_db(x, fs), COUPURE_BASSE, COUPURE_HAUTE)

    SORTIES.mkdir(parents=True, exist_ok=True)
    INDICATEURS.parent.mkdir(parents=True, exist_ok=True)
    lignes = [{
        "Version": "original", **{f"Gain {NOMS[n]} (dB)": 0 for n in NOMS},
        "Crête avant correction (dBFS)": round(stats_x.peak_dbfs, 2), "Abaissement (dB)": 0.0,
        "Crête finale (dBFS)": round(stats_x.peak_dbfs, 2), "Valeur efficace (dBFS)": round(stats_x.rms_dbfs, 2),
        **{f"Variation {NOMS[n]} (dB)": 0.0 for n in NOMS},
        **{f"Part {NOMS[n]} (%)": round(100 * parts_x[n], 1) for n in NOMS},
        "Fichier": EXTRAIT.name,
    }]
    for nom, gains in VERSIONS.items():
        sortie = BACKEND.recombine_bands(BACKEND.apply_gains(bandes, gains))
        crete = float(np.max(np.abs(sortie)))
        abaissement = 0.0
        if crete > 1.0:                       # évite l'écrêtage : on ramène la crête à -1 dBFS
            facteur = 10 ** (PLAFOND_DBFS / 20) / crete
            sortie = sortie * facteur
            abaissement = to_dbfs(facteur)
        nom_fichier = f"Techno_extrait_{nom}_G{gains['bass']:+d}_M{gains['mid']:+d}_A{gains['treble']:+d}"
        chemin = export_audio(sortie, fs, SORTIES / nom_fichier, "WAV")
        stats = level_stats(sortie)
        zones = puissance_par_zone(sortie, fs)
        parts = band_energy_shares(*spectrum_db(sortie, fs), COUPURE_BASSE, COUPURE_HAUTE)
        lignes.append({
            "Version": nom, **{f"Gain {NOMS[n]} (dB)": gains[n] for n in NOMS},
            "Crête avant correction (dBFS)": round(to_dbfs(crete), 2), "Abaissement (dB)": round(abaissement, 2),
            "Crête finale (dBFS)": round(stats.peak_dbfs, 2), "Valeur efficace (dBFS)": round(stats.rms_dbfs, 2),
            **{f"Variation {NOMS[n]} (dB)": round(10 * np.log10(zones[n] / zones_x[n]), 2) for n in NOMS},
            **{f"Part {NOMS[n]} (%)": round(100 * parts[n], 1) for n in NOMS},
            "Fichier": chemin.name,
        })
        print(f"{nom} : crête {to_dbfs(crete):+.2f} dBFS, abaissement {abaissement:.2f} dB -> {chemin.name}")

    with INDICATEURS.open("w", newline="", encoding="utf-8-sig") as fichier:
        ecrivain = csv.DictWriter(fichier, fieldnames=list(lignes[0]), delimiter=";")
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
    print(f"Indicateurs : {INDICATEURS}")


if __name__ == "__main__":
    main()
