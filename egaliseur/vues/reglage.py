"""Étape 4 — Régler le gain de chaque bande."""

from __future__ import annotations

import streamlit as st

from ..dsp_backend import BAND_NAMES
from ..interface import charts, etat, navigation, ui
from ..interface.charts import BAND_COLORS, PLOTLY_CONFIG, format_gain, format_hz
from ..interface.formatage import fr_number
from ..pipeline import BAND_LABELS
from ..signal_analysis import GAIN_LIMIT_DB, gain_db_to_factor

BAND_TAGLINES = {
    "bass": "Poids et profondeur — grosse caisse, basse",
    "mid": "Présence et clarté — voix, guitares, caisse claire",
    "treble": "Brillance et détails — cymbales, souffle, sifflantes",
}
PRESETS = {
    "Neutre": (0, 0, 0),
    "Basses renforcées": (6, 0, -2),
    "Voix en avant": (-4, 4, 1),
    "Brillance": (-2, 0, 6),
    "Effet radio": (-12, 3, -12),
}


def render() -> None:
    track = navigation.require_track()
    if track is None:
        return
    excerpt = etat.current_excerpt(track)
    low, high = (float(value) for value in etat.current_cutoffs(track))
    processing = etat.current_processing(track, excerpt)
    result = processing.result if processing else None

    st.html(
        ui.page_head(
            4,
            navigation.TOTAL_STEPS,
            "RÉGLAGE DES NIVEAUX",
            "Régler l'égaliseur",
            f"Choisissez le gain de chaque bande, de −{GAIN_LIMIT_DB} à +{GAIN_LIMIT_DB} dB par pas de 1 dB. "
            "Partez d'un préréglage ou réglez librement.",
        )
    )
    navigation.context_bar(track, excerpt)
    if processing and processing.error:
        st.error(f"Le traitement a échoué : {processing.error}", icon=":material/error:")

    gains = etat.current_gains()
    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
        st.markdown("**Préréglages**")
        for name, values in PRESETS.items():
            st.button(
                name,
                key=f"preset_{name}",
                on_click=etat.apply_preset,
                args=(values,),
                type="primary" if tuple(gains.values()) == values else "secondary",
            )

    ranges = {"bass": f"< {format_hz(low)}", "mid": f"{format_hz(low)} – {format_hz(high)}", "treble": f"> {format_hz(high)}"}
    for column, name in zip(st.columns(3, gap="medium"), BAND_NAMES):
        with column, st.container(key=f"band_{name}"):
            gain = gains[name]
            st.html(ui.band_head(BAND_LABELS[name], BAND_TAGLINES[name], ranges[name], BAND_COLORS[name]))
            st.html(ui.gain_readout(format_gain(gain), f"amplitude × {fr_number(gain_db_to_factor(gain), 2)}", BAND_COLORS[name]))
            st.select_slider(
                f"Gain {BAND_LABELS[name].lower()}",
                options=list(range(-GAIN_LIMIT_DB, GAIN_LIMIT_DB + 1)),
                format_func=format_gain,
                label_visibility="collapsed",
                **etat.bound(f"gain_{name}"),
            )
            if result is None:
                st.html('<div class="band-status">🔒 Écoute de la bande seule : disponible avec les filtres</div>')
            elif result["band_wavs"][name] is None:
                st.caption("Bande trop forte pour l'écoute (> 0 dBFS) : baissez son gain.")
            else:
                st.caption("Écouter la bande seule (après gain)")
                st.audio(result["band_wavs"][name], format="audio/wav")

    lower = st.columns([1.75, 1], gap="medium")
    with lower[0], st.container(key="card_template"):
        st.plotly_chart(
            charts.gain_template_figure(low, high, track.nyquist, gains),
            config=PLOTLY_CONFIG,
            theme=None,
            key="template_chart",
        )
    with lower[1]:
        _level_meter(excerpt.analysis["stats"], gains, result)
        with st.expander("Comprendre les décibels", icon=":material/lightbulb:"):
            st.markdown(
                """
- Un gain **G** en dB multiplie l'amplitude par **10^(G/20)** :
  +6 dB ≈ ×2, −6 dB ≈ ×0,5, +12 dB ≈ ×4, 0 dB = inchangé.
- Le **gabarit** ci-contre est idéal : il change de gain d'un coup à la fréquence de coupure.
  Un vrai filtre passe progressivement d'une bande à l'autre ; c'est ce que l'étude du
  **passe-bas** va nous montrer.
- **Écrêtage** : un échantillon ne peut pas dépasser ±1 (0 dBFS). Au-delà, il est tronqué,
  ce qui produit une distorsion audible.
"""
            )
    navigation.nav_footer("egaliseur")


def _level_meter(stats, gains: dict[str, int], result: dict | None) -> None:
    def position(dbfs: float) -> float:
        return (dbfs + 60) / 60

    if result is not None:
        peak = result["stats"].peak_dbfs
        foot = f"Crête réelle du signal recombiné. Valeur efficace : {fr_number(result['stats'].rms_dbfs)} dBFS."
        if result["attenuation_db"] < 0:
            foot += (
                f"<br><b>Niveau abaissé de {fr_number(abs(result['attenuation_db']))} dB</b> pour éviter "
                f"l'écrêtage (crête avant correction : {fr_number(result['raw_peak_dbfs'])} dBFS). À signaler dans le rapport."
            )
        st.html(ui.level_meter("Crête après égalisation", f"{fr_number(peak)} dBFS", position(peak), foot, peak > 0))
        return

    boost = max(0, max(gains.values()))
    estimate = stats.peak_dbfs + boost
    if boost == 0:
        foot = (
            f"Marge avant écrêtage : <b>{fr_number(-stats.peak_dbfs)} dB</b>. Aucun gain positif : "
            "pas d'augmentation de niveau prévue."
        )
    elif estimate > 0:
        foot = (
            f"Avec <b>{format_gain(boost)}</b> sur une bande, la crête pourrait atteindre <b>≈ {fr_number(estimate)} dBFS</b> : "
            "écrêtage probable. Il faudra baisser les gains ou abaisser le niveau de sortie (et le signaler)."
        )
    else:
        foot = f"Avec {format_gain(boost)}, crête estimée ≈ {fr_number(estimate)} dBFS : la marge reste suffisante."
    foot += "<br><span style='opacity:.75'>Estimation simple : crête actuelle + plus fort gain positif.</span>"
    st.html(
        ui.level_meter(
            "Crête de l'extrait (original)", f"{fr_number(stats.peak_dbfs)} dBFS", position(estimate), foot, estimate > 0
        )
    )
