"""Étape 1 — Importer la piste et relever ses caractéristiques."""

from __future__ import annotations

import streamlit as st

from ..interface import etat, navigation, ui
from ..interface.charts import BAND_COLORS
from ..interface.formatage import describe_dtype, explain_wav_warning, fr_duration, fr_int, fr_number


def render() -> None:
    track, error = etat.load_track()
    if track is None:
        _render_welcome(error)
        return

    st.html(
        ui.page_head(
            1,
            navigation.TOTAL_STEPS,
            "SOURCE AUDIO",
            "Votre piste",
            "Les caractéristiques du fichier sont relevées automatiquement. L'original n'est jamais "
            "modifié : l'application travaille sur une copie en mémoire.",
        )
    )
    bits, dtype_text = describe_dtype(track.audio.source_dtype)
    mode = "mono" if track.channels == 1 else "stéréo"
    top = st.columns([4, 1], vertical_alignment="center")
    with top[0]:
        st.html(ui.track_card(track.name, f"WAV · {bits} · {mode} · original conservé intact"))
    with top[1]:
        st.button("Changer de piste", on_click=etat.clear_source, icon=":material/swap_horiz:", width="stretch")

    st.html(
        ui.stat_grid(
            [
                ("ÉCHANTILLONNAGE", f"{fr_int(track.sample_rate)} Hz", "fs : échantillons par seconde"),
                ("CANAUX", f"{track.channels} · {mode}", "voies enregistrées"),
                ("DURÉE", fr_duration(track.duration), f"{fr_number(track.duration, 2)} s au total"),
                ("RÉSOLUTION", bits, dtype_text),
                ("ÉCHANTILLONS", fr_int(track.audio.samples.shape[0]), "par canal"),
                ("NYQUIST", f"{fr_int(int(track.nyquist))} Hz", "fréquence max. = fs / 2"),
            ]
        )
    )
    for message in track.audio.warnings:
        st.warning(f"**Avertissement à la lecture :** {explain_wav_warning(message)}", icon=":material/info:")
    navigation.nav_footer("piste")


def _render_welcome(error: str | None) -> None:
    st.html(ui.hero())
    if error:
        st.error(f"Impossible d'utiliser ce fichier : {error}. Choisissez-en un autre.", icon=":material/error:")
    columns = st.columns([1.7, 1], gap="medium")
    with columns[0]:
        widget = f"uploader_{st.session_state.uploader_n}"
        st.file_uploader(
            "Importer un fichier WAV",
            type=["wav"],
            key=widget,
            on_change=etat.on_upload,
            args=(widget,),
            help="WAV mono ou stéréo, d'au moins 10 secondes.",
        )
    with columns[1], st.container(key="card_example"):
        st.html(ui.card_title("Pas de fichier sous la main ?", "Essayez avec la piste fournie avec le projet."))
        st.button(
            f"Utiliser {etat.EXAMPLE_FILE.name}",
            on_click=etat.use_example,
            icon=":material/library_music:",
            type="primary",
            width="stretch",
            disabled=not etat.EXAMPLE_FILE.exists(),
        )
    st.html(ui.subhead("LES TROIS BANDES DE L'ÉGALISEUR"))
    st.html(
        ui.explain_bands(
            [
                ("Graves", "≈ 20 à 250 Hz", "Le poids du son : grosse caisse, ligne de basse, fondamentales graves.", BAND_COLORS["bass"]),
                ("Médiums", "≈ 250 Hz à 4 kHz", "L'essentiel de la voix et des instruments : présence, clarté.", BAND_COLORS["mid"]),
                ("Aigus", "≈ 4 kHz à fs/2", "La brillance : cymbales, souffle, consonnes sifflantes, détails.", BAND_COLORS["treble"]),
            ]
        )
    )
    st.html(ui.subhead("LE PARCOURS EN 5 ÉTAPES"))
    st.html(
        ui.flow(
            [
                ("1 · PISTE", "Une piste WAV ; ses caractéristiques sont relevées automatiquement."),
                ("2 · EXTRAIT", "Un passage de 10 à 30 s, à écouter et visualiser."),
                ("3 · FRÉQUENCES", "Le spectre et les frontières entre les trois bandes."),
                ("4 · ÉGALISEUR", "Un gain de −12 à +12 dB par bande."),
                ("5 · RÉSULTAT", "Écoute avant/après, spectres comparés et export."),
            ]
        )
    )
