"""Page 1 — importer le fichier, écouter l'extrait, voir le spectre et les trois bandes."""

from __future__ import annotations

import streamlit as st

from ..dsp_backend import BAND_NAMES
from ..interface import charts, etat, navigation, ui
from ..interface.charts import PLOTLY_CONFIG, format_hz
from ..interface.formatage import fr_duration, fr_int
from ..signal_analysis import cutoff_options


def render() -> None:
    track, error = etat.load_track()
    if track is None:
        _render_import(error)
        return

    st.html(ui.page_head(1, navigation.TOTAL_STEPS, "Fichier"))
    mode = "mono" if track.channels == 1 else "stéréo"
    top = st.columns([5, 1], vertical_alignment="center")
    with top[0]:
        st.html(ui.track_line(track.name, f"{fr_int(track.sample_rate)} Hz · {mode} · {fr_duration(track.duration)}"))
    with top[1]:
        st.button("Changer", on_click=etat.clear_source, icon=":material/swap_horiz:", width="stretch")

    excerpt = etat.current_excerpt(track)
    original = etat.analyse(track, excerpt, "original", excerpt.clip)
    longest = etat.max_excerpt(track.duration)
    latest = etat.latest_start(track, excerpt.duration)
    with st.container(key="card_excerpt"):
        sliders = st.columns(2, gap="large")
        with sliders[0]:
            if latest > 0:
                st.slider("Début (s)", min_value=0.0, max_value=latest, step=0.5, format="%.1f", **etat.bound("excerpt_start"))
        with sliders[1]:
            if longest > etat.MIN_EXCERPT_S:
                st.slider("Durée (s)", min_value=etat.MIN_EXCERPT_S, max_value=longest, step=1, **etat.bound("excerpt_duration"))
        st.html(ui.label("Signal complet"))
        st.audio(original["wav"], format="audio/wav")

    with st.container(key="card_spectrum"):
        options = cutoff_options(track.sample_rate)
        key = etat.widget_key("cutoffs")
        st.select_slider(
            "Coupures",
            options=options,
            value=etat.current_cutoffs(track),
            format_func=format_hz,
            key=key,
            on_change=etat.on_cutoffs_change,
            args=(key, options),
        )
        low, high = (float(value) for value in etat.current_cutoffs(track))
        try:
            bands = etat.bands(track, excerpt)
        except (NotImplementedError, ValueError, RuntimeError) as error:
            st.error(f"Séparation impossible : {error}")
            return
        bands_db = {name: etat.analyse(track, excerpt, f"bande:{name}", bands[name])["levels"] for name in BAND_NAMES}
        st.plotly_chart(
            charts.band_spectra_figure(original["frequencies"], original["levels"], bands_db, low, high, track.nyquist),
            config=PLOTLY_CONFIG,
            theme=None,
            key="bands_chart",
        )
    navigation.nav_footer("fichier")


def _render_import(error: str | None) -> None:
    st.html(ui.hero())
    if error:
        st.error(f"Fichier inutilisable : {error}.")
    widget = f"uploader_{st.session_state.uploader_n}"
    st.file_uploader("Fichier WAV", type=["wav"], key=widget, on_change=etat.on_upload, args=(widget,))
    if etat.EXAMPLE_FILE.exists():
        st.button("Utiliser le fichier d'exemple", on_click=etat.use_example, icon=":material/library_music:")
