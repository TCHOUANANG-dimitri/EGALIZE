"""Étape 2 — Choisir l'extrait de 10 à 30 s et l'observer dans le domaine temporel."""

from __future__ import annotations

import streamlit as st

from ..interface import charts, etat, navigation, ui
from ..interface.charts import PLOTLY_CONFIG
from ..interface.formatage import fr_number


def render() -> None:
    track = navigation.require_track()
    if track is None:
        return
    excerpt = etat.current_excerpt(track)

    st.html(
        ui.page_head(
            2,
            navigation.TOTAL_STEPS,
            "DOMAINE TEMPOREL",
            "Choisir l'extrait",
            "Le sujet demande un passage de 10 à 30 secondes. Choisissez-en un représentatif : "
            "avec des basses, des voix ou des cymbales selon ce que vous voulez entendre changer.",
        )
    )
    navigation.context_bar(track, excerpt)

    longest = etat.max_excerpt(track.duration)
    with st.container(key="card_selection"):
        controls = st.columns(2, gap="large")
        with controls[0]:
            if longest > etat.MIN_EXCERPT_S:
                st.slider(
                    "Durée de l'extrait",
                    min_value=etat.MIN_EXCERPT_S,
                    max_value=longest,
                    step=1,
                    format="%d s",
                    **etat.bound("excerpt_duration"),
                )
            else:
                st.markdown(f"**Durée de l'extrait :** {etat.MIN_EXCERPT_S} s (fichier court)")
        with controls[1]:
            latest = etat.latest_start(track, excerpt.duration)
            if latest > 0:
                st.slider(
                    "Début de l'extrait",
                    min_value=0.0,
                    max_value=latest,
                    step=0.5,
                    format="%.1f s",
                    **etat.bound("excerpt_start"),
                )
            else:
                st.markdown("**Début :** 0 s")

        times, minimums, maximums = etat.file_envelope(track.key, track.audio.samples, track.sample_rate)
        st.plotly_chart(
            charts.overview_figure(times, minimums, maximums, excerpt.start, excerpt.end),
            config=PLOTLY_CONFIG,
            theme=None,
            key="overview_chart",
        )
        listen = st.columns([1, 2.2], vertical_alignment="center")
        with listen[0]:
            st.markdown(f"**Écouter l'extrait** · {fr_number(excerpt.start)} s → {fr_number(excerpt.end)} s")
            st.caption("Lecture au niveau réel, sans normalisation.")
        with listen[1]:
            st.audio(excerpt.analysis["wav"], format="audio/wav")

    with st.container(key="card_waveform"):
        st.plotly_chart(
            charts.waveform_figure(*excerpt.analysis["envelope"]),
            config=PLOTLY_CONFIG,
            theme=None,
            key="waveform_chart",
        )
        stats = excerpt.analysis["stats"]
        st.caption(
            f"Crête : {fr_number(stats.peak_dbfs)} dBFS · valeur efficace : {fr_number(stats.rms_dbfs)} dBFS. "
            "Les pointillés rouges marquent la limite numérique (±1, soit 0 dBFS) au-delà de laquelle le signal écrête."
        )
    navigation.nav_footer("extrait")
