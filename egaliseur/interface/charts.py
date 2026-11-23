"""Graphiques Plotly de l'interface.

Règle du sujet : chaque graphique a un titre, des axes nommés avec leurs
unités et une légende lorsque plusieurs éléments sont superposés.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import plotly.graph_objects as go

from ..dsp_backend import BAND_NAMES
from ..pipeline import BAND_LABELS

BAND_COLORS = {"bass": "#1f5bff", "mid": "#d39b1e", "treble": "#7c5cff"}
INK = "#0b1a33"
MUTED = "#5b6b85"
GRID = "rgba(11, 26, 51, 0.08)"
PLOT_BG = "#fafbff"
GOLD = "#c58c12"
BLUE = "#1f5bff"
DANGER = "#e5484d"

PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}

_FREQ_TICKS = (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000)


def format_hz(value: float) -> str:
    """250 -> « 250 Hz », 4000 -> « 4 kHz », 31.5 -> « 31,5 Hz »."""
    if value >= 1000:
        text = f"{value / 1000:.2f}".rstrip("0").rstrip(".")
        return f"{text.replace('.', ',')} kHz"
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text.replace('.', ',')} Hz"


def format_gain(gain_db: float) -> str:
    if gain_db == 0:
        return "0 dB"
    sign = "+" if gain_db > 0 else "−"
    return f"{sign}{abs(gain_db):g} dB"


def _rgba(hex_color: str, alpha: float) -> str:
    red, green, blue = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _base_figure(title: str, x_title: str, y_title: str, height: int) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        title={
            "text": title,
            "x": 0,
            "xanchor": "left",
            "y": 0.98,
            "yanchor": "top",
            "yref": "container",
            "font": {"size": 14, "color": INK},
        },
        height=height,
        margin={"l": 64, "r": 18, "t": 74, "b": 52},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PLOT_BG,
        font={"family": "DM Sans, Segoe UI, sans-serif", "color": MUTED, "size": 12},
        separators=", ",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 11.5},
        },
        hoverlabel={"bgcolor": "#ffffff", "bordercolor": "#dfe6f3", "font": {"color": INK}},
        hovermode="x unified",
    )
    figure.update_xaxes(
        title={"text": x_title, "standoff": 8},
        gridcolor=GRID,
        linecolor=GRID,
        zeroline=False,
        ticks="outside",
        tickcolor=GRID,
    )
    figure.update_yaxes(
        title={"text": y_title, "standoff": 6},
        gridcolor=GRID,
        linecolor=GRID,
        zeroline=False,
    )
    return figure


def _log_frequency_axis(figure: go.Figure, nyquist: float) -> None:
    ticks = [tick for tick in _FREQ_TICKS if tick <= nyquist]
    figure.update_xaxes(
        type="log",
        range=[np.log10(20), np.log10(nyquist)],
        tickvals=ticks,
        ticktext=[format_hz(tick).replace(" Hz", "").replace(" kHz", "k") for tick in ticks],
    )


def _band_zones(
    figure: go.Figure, low: float, high: float, nyquist: float, with_legend: bool = True
) -> None:
    """Colorie les trois zones de fréquences et trace les fréquences de coupure."""
    zones = {"bass": (1.0, low), "mid": (low, high), "treble": (high, nyquist)}
    for name, (start, stop) in zones.items():
        figure.add_vrect(
            x0=start,
            x1=stop,
            fillcolor=BAND_COLORS[name],
            opacity=0.09,
            line_width=0,
            layer="below",
        )
        if with_legend:
            # Trace vide : sert uniquement d'entrée de légende pour la zone colorée.
            figure.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    marker={"symbol": "square", "size": 11, "color": _rgba(BAND_COLORS[name], 0.6)},
                    name=f"Zone {BAND_LABELS[name].lower()}",
                    hoverinfo="skip",
                )
            )
    for cutoff in (low, high):
        figure.add_shape(
            type="line",
            x0=cutoff,
            x1=cutoff,
            y0=0,
            y1=1,
            yref="paper",
            line={"color": GOLD, "width": 1.4, "dash": "dash"},
        )
        # Sur un axe logarithmique, la position x d'une annotation s'exprime en log10.
        figure.add_annotation(
            x=np.log10(cutoff),
            y=0.995,
            yref="paper",
            yanchor="top",
            xanchor="left",
            xshift=4,
            text=f"<b>{format_hz(cutoff)}</b>",
            showarrow=False,
            font={"color": GOLD, "size": 11},
            bgcolor="rgba(255, 255, 255, 0.9)",
        )


def spectrum_figure(
    frequencies: np.ndarray,
    levels_db: np.ndarray,
    low: float,
    high: float,
    nyquist: float,
    *,
    after_levels_db: np.ndarray | None = None,
    title: str = "Spectre de l'extrait et zones de fréquences",
    height: int = 400,
    zone_legend: bool = True,
) -> go.Figure:
    figure = _base_figure(title, "Fréquence (Hz)", "Niveau (dB/Hz)", height)
    _band_zones(figure, low, high, nyquist, with_legend=zone_legend)
    positive = frequencies > 0
    shown = [levels_db[positive]]
    figure.add_trace(
        go.Scatter(
            x=frequencies[positive],
            y=levels_db[positive],
            mode="lines",
            name="Original" if after_levels_db is not None else "Spectre",
            line={"color": INK if after_levels_db is None else _rgba(INK, 0.4), "width": 1.3},
            hovertemplate="%{y:.1f} dB/Hz<extra>Original</extra>",
        )
    )
    if after_levels_db is not None:
        shown.append(after_levels_db[positive])
        figure.add_trace(
            go.Scatter(
                x=frequencies[positive],
                y=after_levels_db[positive],
                mode="lines",
                name="Après égalisation",
                line={"color": GOLD, "width": 1.5},
                hovertemplate="%{y:.1f} dB/Hz<extra>Égalisé</extra>",
            )
        )
    _log_frequency_axis(figure, nyquist)
    values = np.concatenate(shown)
    top = float(np.max(values))
    floor = max(float(np.percentile(values, 1)), top - 110)
    figure.update_yaxes(range=[floor - 3, top + 6])
    figure.update_xaxes(hoverformat=".0f")
    return figure


def band_spectra_figure(
    frequencies: np.ndarray,
    original_db: np.ndarray,
    bands_db: Mapping[str, np.ndarray],
    low: float,
    high: float,
    nyquist: float,
    title: str = "Spectre de l'original et des trois bandes",
    height: int = 420,
) -> go.Figure:
    """Spectre de l'original et de chaque bande séparée, en couleurs."""
    figure = _base_figure(title, "Fréquence (Hz)", "Niveau (dB/Hz)", height)
    _band_zones(figure, low, high, nyquist, with_legend=False)
    positive = frequencies > 0
    figure.add_trace(
        go.Scatter(
            x=frequencies[positive],
            y=original_db[positive],
            mode="lines",
            name="Original",
            line={"color": _rgba(INK, 0.28), "width": 1},
        )
    )
    for name in BAND_NAMES:
        figure.add_trace(
            go.Scatter(
                x=frequencies[positive],
                y=bands_db[name][positive],
                mode="lines",
                name=BAND_LABELS[name],
                line={"color": BAND_COLORS[name], "width": 1.5},
            )
        )
    _log_frequency_axis(figure, nyquist)
    top = float(np.max(original_db[positive]))
    figure.update_yaxes(range=[top - 110, top + 6])
    return figure


def gain_template_figure(
    low: float, high: float, nyquist: float, gains_db: Mapping[str, float]
) -> go.Figure:
    """Gabarit idéal : le gain que l'on souhaite appliquer à chaque fréquence."""
    figure = _base_figure(
        "Gabarit visé : gain souhaité selon la fréquence",
        "Fréquence (Hz, échelle logarithmique)",
        "Gain (dB)",
        300,
    )
    segments = {"bass": (20.0, low), "mid": (low, high), "treble": (high, nyquist)}
    for name, (start, stop) in segments.items():
        gain = gains_db[name]
        figure.add_trace(
            go.Scatter(
                x=[start, stop],
                y=[gain, gain],
                mode="lines",
                line={"color": BAND_COLORS[name], "width": 3},
                fill="tozeroy",
                fillcolor=_rgba(BAND_COLORS[name], 0.16),
                name=f"{BAND_LABELS[name]} : {format_gain(gain)}",
                hovertemplate=f"{BAND_LABELS[name]} : {format_gain(gain)}<extra></extra>",
            )
        )
    for cutoff, left, right in ((low, "bass", "mid"), (high, "mid", "treble")):
        figure.add_shape(
            type="line",
            x0=cutoff,
            x1=cutoff,
            y0=gains_db[left],
            y1=gains_db[right],
            line={"color": MUTED, "width": 1.2, "dash": "dot"},
        )
    figure.add_hline(y=0, line={"color": MUTED, "width": 1}, opacity=0.5)
    _log_frequency_axis(figure, nyquist)
    figure.update_yaxes(range=[-13.5, 13.5], tickvals=list(range(-12, 13, 3)))
    figure.update_layout(hovermode="closest")
    return figure


def overview_figure(
    times: np.ndarray,
    minimums: np.ndarray,
    maximums: np.ndarray,
    excerpt_start: float,
    excerpt_end: float,
) -> go.Figure:
    figure = _base_figure(
        "Vue d'ensemble du fichier — extrait sélectionné en doré",
        "Temps (s)",
        "Amplitude",
        230,
    )
    _envelope_traces(figure, times, minimums, maximums, BLUE, "Signal complet")
    figure.add_vrect(
        x0=excerpt_start,
        x1=excerpt_end,
        fillcolor=GOLD,
        opacity=0.22,
        line={"color": GOLD, "width": 2},
        layer="above",
    )
    figure.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker={"symbol": "square", "size": 11, "color": _rgba(GOLD, 0.45)},
            name="Extrait analysé",
        )
    )
    figure.update_yaxes(range=[-1.05, 1.05], tickvals=[-1, -0.5, 0, 0.5, 1])
    figure.update_xaxes(range=[0, float(times[-1]) if len(times) else 1])
    figure.update_layout(margin={"t": 70, "b": 46}, hovermode=False)
    return figure


def waveform_figure(
    times: np.ndarray,
    minimums: np.ndarray,
    maximums: np.ndarray,
    *,
    after: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> go.Figure:
    figure = _base_figure(
        "Forme d'onde de l'extrait (domaine temporel)",
        "Temps dans l'extrait (s)",
        "Amplitude (1 = pleine échelle)",
        340,
    )
    _envelope_traces(figure, times, minimums, maximums, BLUE, "Original")
    if after is not None:
        _envelope_traces(figure, *after, GOLD, "Après égalisation")
    for level in (-1, 1):
        figure.add_hline(y=level, line={"color": DANGER, "width": 1, "dash": "dash"}, opacity=0.7)
    figure.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            line={"color": DANGER, "width": 1, "dash": "dash"},
            name="Limite d'écrêtage (0 dBFS)",
        )
    )
    peak = max(1.0, float(np.max(np.abs(maximums))), float(np.max(np.abs(minimums))))
    figure.update_yaxes(range=[-peak * 1.08, peak * 1.08])
    figure.update_layout(hovermode=False)
    return figure


def _envelope_traces(
    figure: go.Figure,
    times: np.ndarray,
    minimums: np.ndarray,
    maximums: np.ndarray,
    color: str,
    name: str,
) -> None:
    figure.add_trace(
        go.Scatter(
            x=times,
            y=maximums,
            mode="lines",
            line={"color": color, "width": 0.6},
            legendgroup=name,
            showlegend=False,
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=times,
            y=minimums,
            mode="lines",
            line={"color": color, "width": 0.6},
            fill="tonexty",
            fillcolor=_rgba(color, 0.45),
            legendgroup=name,
            name=name,
            hoverinfo="skip",
        )
    )


def band_detail_figure(
    frequencies: np.ndarray,
    before_db: np.ndarray,
    after_db: np.ndarray,
    name: str,
    low: float,
    high: float,
    nyquist: float,
) -> go.Figure:
    """Spectre d'une bande avant et après son gain."""
    color = BAND_COLORS[name]
    figure = _base_figure(f"Spectre — {BAND_LABELS[name]}", "Fréquence (Hz)", "Niveau (dB/Hz)", 340)
    _band_zones(figure, low, high, nyquist, with_legend=False)
    positive = frequencies > 0
    for levels, label, style in (
        (before_db, "Avant gain", {"color": _rgba(color, 0.45), "width": 1.2, "dash": "dot"}),
        (after_db, "Après gain", {"color": color, "width": 1.6}),
    ):
        figure.add_trace(go.Scatter(x=frequencies[positive], y=levels[positive], mode="lines", name=label, line=style))
    _log_frequency_axis(figure, nyquist)
    top = float(max(np.max(before_db[positive]), np.max(after_db[positive])))
    figure.update_yaxes(range=[top - 100, top + 6])
    return figure


def compare_waveform_figure(
    before: tuple[np.ndarray, np.ndarray, np.ndarray],
    after: tuple[np.ndarray, np.ndarray, np.ndarray],
    title: str,
    labels: tuple[str, str],
    color: str = BLUE,
) -> go.Figure:
    """Formes d'onde superposées (enveloppes min/max) avant et après."""
    figure = _base_figure(title, "Temps (s)", "Amplitude", 340)
    _envelope_traces(figure, *before, "#9aa6bb", labels[0])
    _envelope_traces(figure, *after, color, labels[1])
    for level in (-1, 1):
        figure.add_hline(y=level, line={"color": DANGER, "width": 1, "dash": "dash"}, opacity=0.6)
    peak = max(1.0, *(float(np.max(np.abs(values))) for values in (*before[1:], *after[1:])))
    figure.update_yaxes(range=[-peak * 1.08, peak * 1.08])
    figure.update_layout(hovermode=False)
    return figure
