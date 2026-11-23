"""Page 3 — recombiner les trois bandes, comparer avec l'original, écouter, exporter."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import streamlit as st

from ..audio_io import export_audio_bytes
from ..dsp_backend import BAND_NAMES
from ..interface import charts, etat, navigation, ui
from ..interface.charts import PLOTLY_CONFIG, format_gain
from ..interface.formatage import fr_number
from ..pipeline import BAND_LABELS


def render() -> None:
    track = navigation.require_track()
    if track is None:
        return
    excerpt = etat.current_excerpt(track)
    try:
        _, output = etat.equalized(track, excerpt)
    except (NotImplementedError, ValueError, RuntimeError) as error:
        st.error(f"Recombinaison impossible : {error}")
        return

    st.html(ui.page_head(3, navigation.TOTAL_STEPS, "Recombinaison"))
    gains = etat.current_gains()
    low, high = (float(value) for value in etat.current_cutoffs(track))
    original = etat.analyse(track, excerpt, "original", excerpt.clip)
    result = etat.analyse(track, excerpt, "recombine", output, tuple(gains.values()))

    head = st.columns([4, 1], vertical_alignment="center")
    with head[0]:
        st.html(ui.track_line("Gains", " · ".join(f"{BAND_LABELS[n]} {format_gain(gains[n])}" for n in BAND_NAMES)))
    with head[1]:
        st.button("Tout à 0 dB", on_click=etat.reset_gains, icon=":material/restart_alt:", width="stretch")

    with st.container(key="card_listen"):
        players = st.columns(2, gap="medium")
        with players[0]:
            st.html(ui.label("Original"))
            st.audio(original["wav"], format="audio/wav")
        with players[1]:
            st.html(ui.label("Recombiné"))
            st.audio(result["wav"], format="audio/wav")
            if result["attenuation_db"] < 0:
                st.html(ui.note(f"Niveau abaissé de {fr_number(abs(result['attenuation_db']))} dB pour éviter l'écrêtage."))

    graphs = st.columns(2, gap="medium")
    with graphs[0]:
        st.plotly_chart(
            charts.spectrum_figure(
                original["frequencies"], original["levels"], low, high, track.nyquist,
                after_levels_db=result["levels"], title="Spectre avant / après", height=360, zone_legend=False,
            ),
            config=PLOTLY_CONFIG,
            theme=None,
            key="result_spectrum",
        )
    with graphs[1]:
        st.plotly_chart(
            charts.compare_waveform_figure(original["envelope"], result["envelope"], "Forme d'onde avant / après", ("Original", "Recombiné")),
            config=PLOTLY_CONFIG,
            theme=None,
            key="result_waveform",
        )

    # Export : même niveau que l'écoute (abaissé seulement si le signal écrêterait).
    peak = float(np.max(np.abs(output)))
    exported = output * (10 ** (etat.CEILING_DBFS / 20) / peak) if peak > 1.0 else output
    tag = "_".join(f"{BAND_LABELS[n][0]}{gains[n]:+d}" for n in BAND_NAMES)
    st.download_button(
        "Exporter en WAV",
        data=lambda: export_audio_bytes(exported, track.sample_rate, "WAV"),
        file_name=f"{Path(track.name).stem}_egalise_{tag}.wav",
        mime="audio/wav",
        icon=":material/download:",
        type="primary",
    )
    navigation.nav_footer("recombinaison")
