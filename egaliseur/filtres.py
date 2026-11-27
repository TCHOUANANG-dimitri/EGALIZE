"""Filtres de l'égaliseur, construits uniquement à partir d'un passe-bas élémentaire :
le lissage exponentiel.

    graves  = passe_bas(x, coupure basse)
    médiums = passe_bas(x, coupure haute) - passe_bas(x, coupure basse)
    aigus   = x - passe_bas(x, coupure haute)

Par construction, graves + médiums + aigus = x : avec des gains de 0 dB, le
signal recombiné est identique à l'original.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
from scipy.signal import lfilter

from .dsp_backend import BAND_NAMES, DSPBackend

# Le filtre est appliqué deux fois (aller puis retour), ce qui atténue deux fois.
# On décale la fréquence de réglage pour conserver -3 dB exactement à la coupure :
# 1 / (1 + (fc/f0)^2) = 1/sqrt(2)  <=>  f0 = fc / sqrt(sqrt(2) - 1).
CORRECTION_ALLER_RETOUR = 1 / np.sqrt(np.sqrt(2) - 1)


def lissage_exponentiel(x: np.ndarray, fc: float, fs: int) -> np.ndarray:
    """y[n] = y[n-1] + alpha * (x[n] - y[n-1]), avec alpha = 1 - exp(-2 pi fc / fs).

    `lfilter` exécute exactement cette récurrence (écrite y[n] = alpha x[n] + (1 - alpha) y[n-1]),
    mais beaucoup plus vite qu'une boucle Python.
    """
    alpha = 1 - np.exp(-2 * np.pi * fc / fs)
    return lfilter([alpha], [1, -(1 - alpha)], x, axis=0)


def passe_bas(x: np.ndarray, fc: float, fs: int) -> np.ndarray:
    """Lissage aller puis retour : le retard de l'aller est compensé par le retour (déphasage nul)."""
    f0 = fc * CORRECTION_ALLER_RETOUR
    aller = lissage_exponentiel(x, f0, fs)
    return lissage_exponentiel(aller[::-1], f0, fs)[::-1]


class EgaliseurLissage:
    """Égaliseur trois bandes respectant le contrat `DSPBackend`."""

    def split_bands(self, samples, sample_rate, low_cutoff_hz, high_cutoff_hz):
        sous_basse = passe_bas(samples, low_cutoff_hz, sample_rate)
        sous_haute = passe_bas(samples, high_cutoff_hz, sample_rate)
        return {"bass": sous_basse, "mid": sous_haute - sous_basse, "treble": samples - sous_haute}

    def apply_gains(self, bands: Mapping[str, np.ndarray], gains_db: Mapping[str, float]):
        return {name: bands[name] * 10 ** (gains_db[name] / 20) for name in BAND_NAMES}

    def recombine_bands(self, bands: Mapping[str, np.ndarray]) -> np.ndarray:
        return bands["bass"] + bands["mid"] + bands["treble"]


BACKEND: DSPBackend | None = EgaliseurLissage()
