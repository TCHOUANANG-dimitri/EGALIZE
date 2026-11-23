"""Page 2 — pour chaque bande : écouter, régler le gain, réécouter, visualiser."""

from __future__ import annotations

import streamlit as st

from ..dsp_backend import BAND_NAMES
from ..interface import charts, etat, navigation, ui
from ..interface.charts import BAND_COLORS, PLOTLY_CONFIG, format_gain, format_hz
from ..interface.formatage import fr_number
from ..pipeline import BAND_LABELS
from ..signal_analysis import GAIN_LIMIT_DB


def render() -> None:
    track = navigation.require_track()
    if track is None:
        return
    excerpt = etat.current_excerpt(track)
    try:
        raw = etat.bands(track, excerpt)
        processed, _ = etat.equalized(track, excerpt)
    except (NotImplementedError, ValueError, RuntimeError) as error:
        st.error(f"Séparation impossible : {error}")
        return

    st.html(ui.page_head(2, navigation.TOTAL_STEPS, "Bandes"))
    gains = etat.current_gains()
    key = etat.widget_key("band")
    st.segmented_control(
        "Bande",
        BAND_NAMES,
        format_func=lambda n: f"{BAND_LABELS[n]}   {format_gain(gains[n])}",
        default=st.session_state.band,
        key=key,
        on_change=etat.sync,
        args=("band", key),
        required=True,
        label_visibility="collapsed",
        width="stretch",
    )
    name = st.session_state.band
    low, high = (float(value) for value in etat.current_cutoffs(track))
    ranges = {"bass": f"< {format_hz(low)}", "mid": f"{format_hz(low)} – {format_hz(high)}", "treble": f"> {format_hz(high)}"}

    before = etat.analyse(track, excerpt, f"bande:{name}", raw[name])
    after = etat.analyse(track, excerpt, f"bande:{name}:gain", processed[name], gains[name])

    with st.container(key=f"band_{name}"):
        head = st.columns([3, 1], vertical_alignment="bottom")
        with head[0]:
            st.html(ui.band_range(BAND_LABELS[name], ranges[name]))
        with head[1]:
            st.number_input(
                "Gain (dB)",
                min_value=-GAIN_LIMIT_DB,
                max_value=GAIN_LIMIT_DB,
                step=1,
                **etat.bound(f"gain_{name}"),
            )
        players = st.columns(2, gap="medium")
        with players[0]:
            st.html(ui.label("Avant gain"))
            st.audio(before["wav"], format="audio/wav")
        with players[1]:
            st.html(ui.label(f"Après gain ({format_gain(gains[name])})"))
            st.audio(after["wav"], format="audio/wav")
            if after["attenuation_db"] < 0:
                st.html(ui.note(f"Écoute abaissée de {fr_number(abs(after['attenuation_db']))} dB pour éviter l'écrêtage."))

        graphs = st.columns(2, gap="medium")
        with graphs[0]:
            st.plotly_chart(
                charts.band_detail_figure(before["frequencies"], before["levels"], after["levels"], name, low, high, track.nyquist),
                config=PLOTLY_CONFIG,
                theme=None,
                key="detail_spectrum",
            )
        with graphs[1]:
            st.plotly_chart(
                charts.compare_waveform_figure(
                    before["envelope"], after["envelope"], f"Forme d'onde — {BAND_LABELS[name]}",
                    ("Avant gain", "Après gain"), BAND_COLORS[name],
                ),
                config=PLOTLY_CONFIG,
                theme=None,
                key="detail_waveform",
            )
    navigation.nav_footer("bandes")
