"""Mesures sur le signal, utilisées par l'interface.

Ce module ne contient AUCUN filtre : il se contente d'observer le signal
(enveloppe pour l'affichage, niveaux en dBFS, répartition de l'énergie dans le
spectre). Le découpage en bandes relève du contrat `dsp_backend.DSPBackend`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .dsp_backend import BAND_NAMES

GAIN_LIMIT_DB = 12

# Fréquences normalisées par tiers d'octave (ISO 266). Elles servent de valeurs
# proposées pour les fréquences de coupure : ce sont des repères standard,
# faciles à justifier dans un rapport.
THIRD_OCTAVE_HZ = (
    20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
    800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
    12500, 16000, 20000,
)


@dataclass(frozen=True)
class LevelStats:
    peak: float
    peak_dbfs: float
    rms_dbfs: float


def to_dbfs(value: float) -> float:
    """Convertit une amplitude (1.0 = pleine échelle) en dBFS."""
    return 20 * float(np.log10(max(value, 1e-12)))


def gain_db_to_factor(gain_db: float) -> float:
    """Facteur multiplicatif d'amplitude correspondant à un gain en dB."""
    return 10 ** (gain_db / 20)


def level_stats(samples: np.ndarray) -> LevelStats:
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples))))
    return LevelStats(peak=peak, peak_dbfs=to_dbfs(peak), rms_dbfs=to_dbfs(rms))


def waveform_envelope(
    samples: np.ndarray, sample_rate: int, points: int = 1500
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Enveloppe min/max du signal, pour tracer des millions d'échantillons en ~1500 points.

    Chaque point résume un paquet d'échantillons consécutifs par sa valeur
    minimale et maximale (tous canaux confondus), ce qui préserve les crêtes.
    """
    frames = samples if samples.ndim == 2 else samples[:, np.newaxis]
    count = frames.shape[0]
    points = max(1, min(points, count))
    bucket = count // points
    blocks = frames[: bucket * points].reshape(points, bucket, frames.shape[1])
    minimums = blocks.min(axis=(1, 2))
    maximums = blocks.max(axis=(1, 2))
    times = (np.arange(points) * bucket + bucket / 2) / sample_rate
    return times, minimums, maximums


def band_masks(
    frequencies: np.ndarray, low_cutoff_hz: float, high_cutoff_hz: float
) -> dict[str, np.ndarray]:
    positive = frequencies > 0
    return {
        "bass": positive & (frequencies < low_cutoff_hz),
        "mid": (frequencies >= low_cutoff_hz) & (frequencies < high_cutoff_hz),
        "treble": frequencies >= high_cutoff_hz,
    }


def band_energy_shares(
    frequencies: np.ndarray,
    levels_db: np.ndarray,
    low_cutoff_hz: float,
    high_cutoff_hz: float,
) -> dict[str, float]:
    """Part de la puissance du spectre située dans chaque zone de fréquences.

    Simple lecture du spectre (somme de la densité spectrale par zone) : cela
    n'isole pas les bandes, cela indique seulement où se trouve l'énergie.
    """
    power = 10 ** (levels_db / 10)
    masks = band_masks(frequencies, low_cutoff_hz, high_cutoff_hz)
    total = float(np.sum(power[frequencies > 0]))
    if total <= 0:
        return {name: 0.0 for name in BAND_NAMES}
    return {name: float(np.sum(power[masks[name]])) / total for name in BAND_NAMES}


def default_cutoffs(sample_rate: int) -> tuple[float, float]:
    """Coupures par défaut (250 Hz et 4 kHz), ramenées sous Nyquist si besoin."""
    options = cutoff_options(sample_rate)
    if len(options) < 2:
        raise ValueError("Fréquence d'échantillonnage trop basse pour définir trois bandes.")
    high_target = min(4000.0, sample_rate * 0.4)
    high = min(options, key=lambda value: abs(value - high_target))
    low_target = min(250.0, high / 2)
    low_options = [value for value in options if value < high]
    low = min(low_options, key=lambda value: abs(value - low_target))
    return low, high


def cutoff_options(sample_rate: int) -> list[float]:
    nyquist = sample_rate / 2
    return [value for value in THIRD_OCTAVE_HZ if value < nyquist]
