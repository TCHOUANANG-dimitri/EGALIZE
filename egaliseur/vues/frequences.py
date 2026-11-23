"""Étape 3 — Explorer le spectre et fixer les fréquences de coupure."""

from __future__ import annotations

import streamlit as st

from ..dsp_backend import BAND_NAMES
from ..interface import charts, etat, navigation, ui
from ..interface.charts import BAND_COLORS, PLOTLY_CONFIG, format_hz
from ..interface.formatage import fr_int, fr_number
from ..pipeline import BAND_LABELS
from ..signal_analysis import band_energy_shares, cutoff_options


def render() -> None:
    track = navigation.require_track()
    if track is None:
        return
    excerpt = etat.current_excerpt(track)
    cutoffs = etat.current_cutoffs(track)

    st.html(
        ui.page_head(
            3,
            navigation.TOTAL_STEPS,
            "DOMAINE FRÉQUENTIEL",
            "Explorer les fréquences",
            "Le spectre indique quelles fréquences composent l'extrait. Déplacez les deux poignées "
            "pour fixer les frontières entre graves, médiums et aigus.",
        )
    )
    navigation.context_bar(track, excerpt)

    options = cutoff_options(track.sample_rate)
    with st.container(key="card_spectrum"):
        key = etat.widget_key("cutoffs")
        # `value` est un couple : c'est lui qui fait du curseur un curseur à deux poignées.
        st.select_slider(
            "Fréquences de coupure (graves | médiums | aigus)",
            options=options,
            value=cutoffs,
            format_func=format_hz,
            key=key,
            on_change=etat.on_cutoffs_change,
            args=(key, options),
            help="Valeurs normalisées par tiers d'octave (ISO 266), toujours sous la fréquence de Nyquist.",
        )
        low, high = (float(value) for value in cutoffs)
        frequencies, levels = excerpt.analysis["frequencies"], excerpt.analysis["levels"]
        st.plotly_chart(
            charts.spectrum_figure(frequencies, levels, low, high, track.nyquist),
            config=PLOTLY_CONFIG,
            theme=None,
            key="spectrum_chart",
        )
        shares = band_energy_shares(frequencies, levels, low, high)
        ranges = {
            "bass": f"0 – {format_hz(low)}",
            "mid": f"{format_hz(low)} – {format_hz(high)}",
            "treble": f"{format_hz(high)} – {format_hz(track.nyquist)}",
        }
        st.html(
            ui.band_strip(
                [ui.BandSummary(BAND_LABELS[n], BAND_COLORS[n], ranges[n], shares[n]) for n in BAND_NAMES]
            )
        )

    resolution = track.sample_rate / 8192  # tranches de Welch de 8 192 échantillons (audio_io.spectrum_db)
    with st.expander("Comprendre ce graphique", icon=":material/lightbulb:"):
        st.markdown(
            f"""
- **Spectre** : il décompose l'extrait en sinusoïdes et indique la puissance présente autour de
  chaque fréquence. Il est estimé par la méthode de Welch (moyenne de FFT calculées sur des tranches
  de 8 192 échantillons), d'où une résolution d'environ **{fr_number(resolution)} Hz**.
- **Échelle logarithmique** : chaque octave (doublement de fréquence) occupe la même largeur,
  comme notre oreille la perçoit. 20 → 40 Hz prend autant de place que 10 → 20 kHz.
- **dB/Hz** : la puissance est exprimée en décibels. +10 dB signifie une puissance multipliée par 10.
- **Nyquist ({fr_int(int(track.nyquist))} Hz)** : la moitié de la fréquence d'échantillonnage. Aucune
  fréquence au-delà ne peut être représentée dans le fichier ; le spectre s'arrête donc là.
- **Pourcentages** : part de la puissance du spectre située dans chaque zone. C'est une simple lecture
  du spectre : les bandes ne sont pas encore séparées.
"""
        )
    navigation.nav_footer("frequences")
