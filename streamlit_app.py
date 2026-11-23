"""EGALIZE — Égaliseur audio trois bandes (Projet 2), application Streamlit.

Lancer depuis ce dossier :  streamlit run streamlit_app.py

Pages : egaliseur/vues/ · Filtres : egaliseur/filtres.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from egaliseur.interface import etat, navigation, ui
from egaliseur.vues import bandes, fichier, recombinaison

ASSETS = Path(__file__).resolve().parent / "egaliseur" / "interface" / "assets"


def main() -> None:
    st.set_page_config(page_title="EGALIZE", page_icon=":material/graphic_eq:", layout="wide")
    ui.inject_css()
    etat.init_state()
    st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icone.svg"), size="large")

    track, _ = etat.load_track()
    done = ":material/check_circle:"
    pages = {
        "fichier": st.Page(fichier.render, title="1 · Fichier", icon=done if track else ":material/upload_file:", url_path="fichier", default=True),
        "bandes": st.Page(bandes.render, title="2 · Bandes", icon=":material/tune:", url_path="bandes"),
        "recombinaison": st.Page(recombinaison.render, title="3 · Recombinaison", icon=":material/merge:", url_path="recombinaison"),
    }
    navigation.register(pages)
    st.navigation(list(pages.values())).run()


main()
