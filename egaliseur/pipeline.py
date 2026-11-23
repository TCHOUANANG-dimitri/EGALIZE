"""Enchaînement des étapes de l'égaliseur autour du contrat `DSPBackend`.

Ce module n'implémente pas les filtres : il appelle les trois fonctions du
backend (séparer, appliquer les gains, recombiner) et vérifie que ce qu'elles
renvoient est cohérent avant de l'afficher ou de l'exporter.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from .dsp_backend import BAND_NAMES, DSPBackend

BAND_LABELS = {"bass": "Graves", "mid": "Médiums", "treble": "Aigus"}


def validate_bands(
    bands: Mapping[str, np.ndarray], expected_shape: tuple[int, ...]
) -> dict[str, np.ndarray]:
    missing = [BAND_LABELS[name] for name in BAND_NAMES if name not in bands]
    if missing:
        raise ValueError(f"Le traitement n'a pas fourni ces bandes : {', '.join(missing)}.")
    checked: dict[str, np.ndarray] = {}
    for name in BAND_NAMES:
        band = np.asarray(bands[name], dtype=np.float64)
        if band.shape != expected_shape:
            raise ValueError(
                f"La bande {BAND_LABELS[name]} a la forme {band.shape}, "
                f"alors que l'extrait a la forme {expected_shape}."
            )
        if not np.all(np.isfinite(band)):
            raise ValueError(f"La bande {BAND_LABELS[name]} contient des valeurs non finies.")
        checked[name] = band
    return checked


def validate_output(samples: np.ndarray, expected_shape: tuple[int, ...]) -> np.ndarray:
    output = np.asarray(samples, dtype=np.float64)
    if output.shape != expected_shape:
        raise ValueError("Le signal recombiné n'a pas la même forme que l'extrait.")
    if not np.all(np.isfinite(output)):
        raise ValueError("Le signal recombiné contient des valeurs non finies.")
    return output


def split(
    backend: DSPBackend,
    clip: np.ndarray,
    sample_rate: int,
    low_cutoff_hz: float,
    high_cutoff_hz: float,
) -> dict[str, np.ndarray]:
    bands = backend.split_bands(clip, sample_rate, low_cutoff_hz, high_cutoff_hz)
    return validate_bands(bands, clip.shape)


def equalize(
    backend: DSPBackend,
    raw_bands: Mapping[str, np.ndarray],
    gains_db: Mapping[str, float],
    expected_shape: tuple[int, ...],
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Applique les gains puis recombine. Renvoie (bandes traitées, signal final)."""
    processed = validate_bands(backend.apply_gains(raw_bands, gains_db), expected_shape)
    output = validate_output(backend.recombine_bands(processed), expected_shape)
    return processed, output
