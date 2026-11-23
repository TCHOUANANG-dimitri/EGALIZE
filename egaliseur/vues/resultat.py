"""Étape 5 — Écouter, comparer avant/après, exporter et enregistrer les versions."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from ..audio_io import export_audio_bytes
from ..dsp_backend import BAND_NAMES
from ..interface import charts, etat, navigation, ui
from ..interface.charts import PLOTLY_CONFIG, format_gain
from ..interface.formatage import fr_number
from ..pipeline import BAND_LABELS

MIME_TYPES = {"WAV": "audio/wav", "FLAC": "audio/flac", "MP3": "audio/mpeg"}


def render() -> None:
    track = navigation.require_track()
    if track is None:
        return
    excerpt = etat.current_excerpt(track)
    low, high = (float(value) for value in etat.current_cutoffs(track))
    gains = etat.current_gains()
    processing = etat.current_processing(track, excerpt)

    st.html(
        ui.page_head(
            5,
            navigation.TOTAL_STEPS,
            "RÉSULTAT",
            "Écouter, comparer et exporter",
            "Recombinez les bandes, comparez avant/après à l'oreille et sur le spectre, "
            "puis enregistrez au moins deux versions égalisées.",
        )
    )
    navigation.context_bar(track, excerpt)
    gains_text = " · ".join(f"{BAND_LABELS[n]} {format_gain(gains[n])}" for n in BAND_NAMES)

    if processing is None or processing.error:
        if processing is not None:
            st.error(f"Le traitement a échoué : {processing.error}", icon=":material/error:")
        st.html(
            ui.locked_card(
                "Les filtres ne sont pas encore branchés",
                "<p>Toutes les étapes précédentes fonctionnent déjà : il ne manque que le traitement "
                "lui-même. Il s'écrira dans <code>egaliseur/filtres.py</code> et devra fournir les trois "
                "fonctions décrites dans <code>egaliseur/dsp_backend.py</code> :</p><ol>"
                "<li><code>split_bands</code> — séparer l'extrait en trois signaux : "
                "<b>passe-bas</b> → graves, <b>passe-bande</b> → médiums, <b>passe-haut</b> → aigus ;</li>"
                "<li><code>apply_gains</code> — appliquer à chaque bande le gain choisi ;</li>"
                "<li><code>recombine_bands</code> — additionner les trois bandes pour obtenir le signal final.</li>"
                "</ol><p style='margin-top:8px'>Cette page affichera alors l'écoute avant/après, "
                "la comparaison des spectres et l'export.</p>",
            )
        )
        players = st.columns(2, gap="medium")
        with players[0], st.container(key="card_original"):
            st.html(ui.card_title("Original", "Extrait au niveau réel"))
            st.audio(excerpt.analysis["wav"], format="audio/wav")
        with players[1], st.container(key="card_equalized"):
            st.html(ui.card_title("Version égalisée", gains_text))
            st.html(ui.placeholder("🔒 Disponible quand les filtres seront branchés"))
    else:
        _render_result(track, excerpt, processing, low, high, gains, gains_text)

    _render_versions(excerpt, low, high, gains, processing.result if processing else None)
    navigation.nav_footer("resultat")


def _render_result(track, excerpt, processing, low, high, gains, gains_text) -> None:
    result = processing.result
    players = st.columns(2, gap="medium")
    with players[0], st.container(key="card_original"):
        st.html(ui.card_title("Original", "Extrait au niveau réel"))
        st.audio(excerpt.analysis["wav"], format="audio/wav")
    with players[1], st.container(key="card_equalized"):
        st.html(ui.card_title("Version égalisée", gains_text))
        if result["wav"] is None:
            st.error("La sortie dépasse 0 dBFS : baissez les gains ou activez l'abaissement automatique.")
        else:
            st.audio(result["wav"], format="audio/wav")
    st.toggle(
        f"Abaisser automatiquement le niveau si la sortie dépasse 0 dBFS (crête ramenée à {fr_number(etat.OUTPUT_CEILING_DBFS)} dBFS)",
        help="Le sujet demande de signaler toute normalisation : l'abaissement appliqué est affiché et enregistré avec la version.",
        **etat.bound("protect_clip"),
    )
    if result["attenuation_db"] < 0:
        st.info(
            f"Niveau abaissé de **{fr_number(abs(result['attenuation_db']))} dB** pour éviter l'écrêtage "
            f"(crête avant correction : {fr_number(result['raw_peak_dbfs'])} dBFS). À signaler dans le rapport.",
            icon=":material/volume_down:",
        )

    frequencies = excerpt.analysis["frequencies"]
    with st.container(key="card_compare"):
        tabs = st.tabs([":material/compare: Spectres avant / après", ":material/stacked_line_chart: Spectre de chaque bande", ":material/graphic_eq: Formes d'onde"])
        with tabs[0]:
            st.plotly_chart(
                charts.spectrum_figure(
                    frequencies, excerpt.analysis["levels"], low, high, track.nyquist,
                    after_levels_db=result["levels"], title="Spectre avant / après égalisation",
                ),
                config=PLOTLY_CONFIG, theme=None, key="compare_chart",
            )
        with tabs[1]:
            st.plotly_chart(
                charts.band_spectra_figure(frequencies, excerpt.analysis["levels"], processing.band_spectra, low, high, track.nyquist),
                config=PLOTLY_CONFIG, theme=None, key="bands_chart",
            )
            st.caption(
                "Chaque bande devrait occuper sa zone. Observez la pente autour des fréquences de coupure : "
                "c'est la signature du filtre utilisé."
            )
        with tabs[2]:
            st.plotly_chart(
                charts.waveform_figure(*excerpt.analysis["envelope"], after=result["envelope"]),
                config=PLOTLY_CONFIG, theme=None, key="waveforms_chart",
            )

    formats = ["WAV"] + (["FLAC", "MP3"] if shutil.which("ffmpeg") else [])
    output = result["output"]
    with st.container(key="card_export"):
        columns = st.columns([1, 2.4], vertical_alignment="bottom")
        with columns[0]:
            output_format = st.selectbox(
                "Format d'export", formats, help="FLAC et MP3 nécessitent FFmpeg." if len(formats) == 1 else None
            )
        tag = "_".join(f"{BAND_LABELS[n][0]}{gains[n]:+d}" for n in BAND_NAMES)
        with columns[1]:
            st.download_button(
                "Exporter la version égalisée",
                data=lambda: export_audio_bytes(output, track.sample_rate, output_format),
                file_name=f"{Path(track.name).stem}_egalise_{tag}.{output_format.lower()}",
                mime=MIME_TYPES[output_format],
                icon=":material/download:",
                type="primary",
                width="stretch",
                disabled=result["stats"].peak > 1.0,
            )
        st.caption("Rangez les fichiers exportés dans donnees/egalisees/ ; l'original reste dans donnees/originales/.")


def _render_versions(excerpt, low, high, gains, result) -> None:
    with st.container(key="card_versions"):
        head = st.columns([2.2, 1], vertical_alignment="center")
        with head[0]:
            st.html(
                ui.card_title(
                    "Versions enregistrées",
                    "Le sujet demande au moins deux versions égalisées, avec leurs fréquences de coupure et "
                    "leurs gains. Enregistrez chaque réglage pour le retrouver dans votre rapport.",
                )
            )
        record = {
            "Extrait (s)": f"{fr_number(excerpt.start)} → {fr_number(excerpt.end)}",
            "Coupure graves/médiums (Hz)": low,
            "Coupure médiums/aigus (Hz)": high,
            **{f"Gain {BAND_LABELS[n].lower()} (dB)": gains[n] for n in BAND_NAMES},
            "Abaissement de niveau (dB)": round(result["attenuation_db"], 2) if result else None,
        }
        with head[1]:
            st.button("Enregistrer ce réglage", on_click=etat.save_version, args=(record,), icon=":material/bookmark_add:", width="stretch")
        versions = st.session_state.versions
        if versions:
            table = pd.DataFrame(versions)
            st.dataframe(table, hide_index=True, width="stretch")
            actions = st.columns([1, 1, 2])
            with actions[0]:
                st.download_button(
                    "Télécharger (CSV)",
                    data=table.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                    file_name="reglages_egaliseur.csv",
                    mime="text/csv",
                    icon=":material/table:",
                    width="stretch",
                )
            with actions[1]:
                st.button("Tout effacer", on_click=etat.clear_versions, icon=":material/delete:", width="stretch")
