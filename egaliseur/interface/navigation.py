"""Navigation entre les pages : registre des pages et liens précédent / suivant."""

from __future__ import annotations

import streamlit as st

from . import etat

ORDER = ("fichier", "bandes", "recombinaison")
TOTAL_STEPS = len(ORDER)

# Rempli à chaque exécution par streamlit_app.py, avant d'afficher la page.
PAGES: dict[str, st.Page] = {}


def register(pages: dict[str, st.Page]) -> None:
    PAGES.clear()
    PAGES.update(pages)


def _short(page: st.Page) -> str:
    return page.title.split("· ")[-1]


def nav_footer(current: str) -> None:
    index = ORDER.index(current)
    left, _, right = st.columns([1, 1.2, 1], vertical_alignment="center")
    if index > 0 and ORDER[index - 1] in PAGES:
        with left, st.container(key="nav_prev"):
            page = PAGES[ORDER[index - 1]]
            st.page_link(page, label=_short(page), icon=":material/arrow_back:")
    if index + 1 < len(ORDER) and ORDER[index + 1] in PAGES:
        with right, st.container(key="nav_next", horizontal_alignment="right"):
            page = PAGES[ORDER[index + 1]]
            st.page_link(page, label=_short(page), icon=":material/arrow_forward:", icon_position="right")


def require_track() -> etat.Track | None:
    """Renvoie la piste chargée, ou propose d'en importer une."""
    track, _ = etat.load_track()
    if track is None and "fichier" in PAGES:
        st.page_link(PAGES["fichier"], label="Importer un fichier", icon=":material/upload_file:")
    return track
