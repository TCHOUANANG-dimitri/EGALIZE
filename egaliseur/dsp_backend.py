from __future__ import annotations

from typing import Mapping, Protocol

import numpy as np


BAND_NAMES = ("bass", "mid", "treble")


class DSPBackend(Protocol):
    def split_bands(
        self,
        samples: np.ndarray,
        sample_rate: int,
        low_cutoff_hz: float,
        high_cutoff_hz: float,
    ) -> Mapping[str, np.ndarray]:
        """Return the unmodified bass, midrange, and treble signals."""
        ...

    def apply_gains(
        self,
        bands: Mapping[str, np.ndarray],
        gains_db: Mapping[str, float],
    ) -> Mapping[str, np.ndarray]:
        """Apply the requested gains to each band and return the resulting bands."""
        ...

    def recombine_bands(self, bands: Mapping[str, np.ndarray]) -> np.ndarray:
        """Recombine the three processed bands into a mono or stereo signal."""
        ...
