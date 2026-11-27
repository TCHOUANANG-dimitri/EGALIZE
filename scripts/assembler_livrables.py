"""Rassemble tous les livrables du projet dans le dossier livrable/.

    python scripts/assembler_livrables.py

À lancer après scripts/generer_versions.py et scripts/generer_rapport.py.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
LIVRABLE = RACINE / "livrable"
RAPPORT = "Rapport_Projet2_Egaliseur_audio"

DOSSIERS = {
    "01_Rapport": [RACINE / "rapport" / f"{RAPPORT}.docx", RACINE / "rapport" / f"{RAPPORT}.pdf"],
    "02_Donnees_brutes": [RACINE / "donnees" / "originales" / "Techno_music_001.wav",
                          RACINE / "donnees" / "originales" / "Techno_music_001_extrait_0-20s.wav"],
    "03_Versions_egalisees": sorted((RACINE / "donnees" / "egalisees").glob("Techno_extrait_version_*.wav")),
    "04_Graphiques": sorted((RACINE / "rapport" / "figures").glob("*.png")),
    "05_Parametres_et_indicateurs": [RACINE / "rapport" / "indicateurs.csv"],
}
CODE = ["streamlit_app.py", "requirements.txt", "README.md", "lancer_egalize.bat", ".streamlit",
        "egaliseur", "scripts", "tests"]
PARAMETRES = [
    {"Version": "Version 1", "Coupure graves/médiums (Hz)": 250, "Coupure médiums/aigus (Hz)": 4000,
     "Gain graves (dB)": 6, "Gain médiums (dB)": 0, "Gain aigus (dB)": -1, "Abaissement de niveau (dB)": 0},
    {"Version": "Version 2", "Coupure graves/médiums (Hz)": 250, "Coupure médiums/aigus (Hz)": 4000,
     "Gain graves (dB)": 0, "Gain médiums (dB)": 8, "Gain aigus (dB)": 2, "Abaissement de niveau (dB)": -2.27},
    {"Version": "Version 3", "Coupure graves/médiums (Hz)": 250, "Coupure médiums/aigus (Hz)": 4000,
     "Gain graves (dB)": 2, "Gain médiums (dB)": -1, "Gain aigus (dB)": 10, "Abaissement de niveau (dB)": 0},
]


def main() -> None:
    if LIVRABLE.exists():
        shutil.rmtree(LIVRABLE)
    for dossier, fichiers in DOSSIERS.items():
        cible = LIVRABLE / dossier
        cible.mkdir(parents=True)
        for fichier in fichiers:
            if not fichier.exists():
                raise FileNotFoundError(f"Livrable manquant : {fichier}")
            shutil.copy2(fichier, cible / fichier.name)

    with (LIVRABLE / "05_Parametres_et_indicateurs" / "frequences_de_coupure_et_gains.csv").open(
            "w", newline="", encoding="utf-8-sig") as sortie:
        ecrivain = csv.DictWriter(sortie, fieldnames=list(PARAMETRES[0]), delimiter=";")
        ecrivain.writeheader()
        ecrivain.writerows(PARAMETRES)

    code = LIVRABLE / "06_Code_source"
    code.mkdir()
    ignorer = shutil.ignore_patterns("__pycache__", "*.pyc", ".ipynb_checkpoints")
    for element in CODE:
        source = RACINE / element
        if source.is_dir():
            shutil.copytree(source, code / element, ignore=ignorer)
        else:
            shutil.copy2(source, code / element)

    for dossier in sorted(LIVRABLE.iterdir()):
        fichiers = [f for f in dossier.rglob("*") if f.is_file()]
        taille = sum(f.stat().st_size for f in fichiers) / 1e6
        print(f"{dossier.name:<32} {len(fichiers):>3} fichiers  {taille:7.1f} Mo")


if __name__ == "__main__":
    main()
