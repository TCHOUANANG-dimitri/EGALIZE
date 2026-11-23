"""Navigation entre les pages : registre des pages, liens précédent/suivant,
barre de contexte commune aux étapes 2 à 5."""

from __future__ import annotations

import streamlit as st

from ..dsp_backend import BAND_NAMES
from ..pipeline import BAND_LABELS
from . import etat, ui
from .charts import format_gain, format_hz
from .formatage import fr_number

ORDER = ("piste", "extrait", "frequences", "egaliseur", "resultat")
TOTAL_STEPS = len(ORDER)

# Rempli à chaque exécution par streamlit_app.py, avant d'afficher la page.
PAGES: dict[str, st.Page] = {}


def register(pages: dict[str, st.Page]) -> None:
    PAGES.clear()
    PAGES.update(pages)


def nav_footer(current: str) -> None:
    """Boutons « étape précédente » et « étape suivante » en bas de page."""
    index = ORDER.index(current)
    left, _, right = st.columns([1, 1.2, 1], vertical_alignment="center")
    if index > 0 and ORDER[index - 1] in PAGES:
        with left, st.container(key="nav_prev"):
            page = PAGES[ORDER[index - 1]]
            st.page_link(page, label=f"Précédent : {page.title.split('· ')[-1]}", icon=":material/arrow_back:")
    if index + 1 < len(ORDER) and ORDER[index + 1] in PAGES:
        with right, st.container(key="nav_next", horizontal_alignment="right"):
            page = PAGES[ORDER[index + 1]]
            st.page_link(
                page,
                label=f"Suivant : {page.title.split('· ')[-1]}",
                icon=":material/arrow_forward:",
                icon_position="right",
            )


def require_track() -> etat.Track | None:
    """Renvoie la piste chargée, ou affiche une invitation à en importer une."""
    track, _ = etat.load_track()
    if track is None:
        st.info("Aucune piste n'est chargée pour l'instant. Commencez par importer un fichier WAV.", icon=":material/info:")
        if "piste" in PAGES:
            st.page_link(PAGES["piste"], label="Aller à l'étape 1 : importer une piste", icon=":material/upload_file:")
    return track


def context_bar(track: etat.Track, excerpt: etat.Excerpt) -> None:
    low, high = etat.current_cutoffs(track)
    gains = etat.current_gains()
    st.html(
        ui.context_bar(
            [
                ("♫", track.name),
                ("Extrait", f"{fr_number(excerpt.start)} → {fr_number(excerpt.end)} s"),
                ("Coupures", f"{format_hz(low)} · {format_hz(high)}"),
                ("Gains", " · ".join(f"{BAND_LABELS[n][0]} {format_gain(gains[n])}" for n in BAND_NAMES)),
            ]
        )
    )
