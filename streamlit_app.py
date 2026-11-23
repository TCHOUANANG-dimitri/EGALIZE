"""EGALIZE — Égaliseur audio numérique (Projet 2), application Streamlit multipage.

Lancer l'application depuis ce dossier :

    streamlit run streamlit_app.py

Ce fichier ne fait que monter l'application : thème, navigation entre les cinq
étapes et barre latérale. Le contenu des pages se trouve dans `egaliseur/vues/`,
et les filtres (à écrire) dans `egaliseur/filtres.py`.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from egaliseur.interface import etat, navigation, ui
from egaliseur.vues import extrait, frequences, piste, reglage, resultat

ASSETS = Path(__file__).resolve().parent / "egaliseur" / "interface" / "assets"
DONE = ":material/check_circle:"


def build_pages(loaded: bool, connected: bool) -> dict[str, st.Page]:
    """Les cinq étapes ; l'icône indique où l'on en est (✓ = étape faite)."""
    return {
        "piste": st.Page(piste.render, title="1 · Piste", icon=DONE if loaded else ":material/upload_file:", url_path="piste", default=True),
        "extrait": st.Page(extrait.render, title="2 · Extrait", icon=DONE if loaded else ":material/content_cut:", url_path="extrait"),
        "frequences": st.Page(frequences.render, title="3 · Fréquences", icon=DONE if loaded else ":material/graphic_eq:", url_path="frequences"),
        "egaliseur": st.Page(reglage.render, title="4 · Égaliseur", icon=DONE if loaded and connected else ":material/tune:", url_path="egaliseur"),
        "resultat": st.Page(resultat.render, title="5 · Résultat", icon=DONE if loaded and connected else ":material/lock:", url_path="resultat"),
    }


def render_sidebar(loaded: bool, connected: bool) -> None:
    versions = len(st.session_state.versions)
    ready = loaded and connected
    checks = [
        (loaded, "Extrait de 10 à 30 s choisi"),
        (loaded, "Fréquence d'échantillonnage et canaux relevés"),
        (loaded, "Signal et spectre affichés"),
        (loaded, "Trois bandes et fréquences de coupure"),
        (connected, "Filtres implémentés"),
        (ready, "Gains appliqués, bandes recombinées"),
        (ready, "Spectres avant / après comparés"),
        (versions >= 2, f"Deux versions enregistrées ({min(versions, 2)}/2)"),
        (ready, "Écrêtage surveillé, normalisation signalée"),
    ]
    with st.sidebar:
        st.html(ui.side_label("MOTEUR DE FILTRAGE"))
        st.html(ui.dsp_status(connected))
        st.html(ui.side_label("CAHIER DES CHARGES · PROJET 2"))
        st.html(ui.checklist(checks))
        st.html(ui.side_note("Le fichier original n'est jamais modifié : l'application lit une copie en mémoire et n'exporte que de nouveaux fichiers."))


def main() -> None:
    st.set_page_config(page_title="EGALIZE — Égaliseur audio", page_icon=":material/graphic_eq:", layout="wide")
    ui.inject_css()
    etat.init_state()
    st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icone.svg"), size="large")

    track, _ = etat.load_track()
    loaded, connected = track is not None, etat.backend() is not None
    pages = build_pages(loaded, connected)
    navigation.register(pages)
    current = st.navigation({"Parcours": list(pages.values())})
    current.run()

    render_sidebar(loaded, connected)
    st.html(ui.footer())


main()
