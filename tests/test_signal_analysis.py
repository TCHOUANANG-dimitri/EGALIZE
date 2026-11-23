import io
import unittest

import numpy as np
from scipy.io import wavfile

from egaliseur.audio_io import read_wav, spectrum_db, wav_bytes_for_playback
from egaliseur.pipeline import equalize, split, validate_bands
from egaliseur.signal_analysis import (
    band_energy_shares,
    cutoff_options,
    default_cutoffs,
    gain_db_to_factor,
    level_stats,
    waveform_envelope,
)


class PassThroughBackend:
    """Faux backend de test : il ne filtre pas, il vérifie seulement l'enchaînement."""

    def split_bands(self, samples, sample_rate, low_cutoff_hz, high_cutoff_hz):
        return {"bass": samples.copy(), "mid": np.zeros_like(samples), "treble": np.zeros_like(samples)}

    def apply_gains(self, bands, gains_db):
        return {name: band * gain_db_to_factor(gains_db[name]) for name, band in bands.items()}

    def recombine_bands(self, bands):
        return sum(bands.values())


class SignalAnalysisTests(unittest.TestCase):
    def test_envelope_keeps_extremes_across_channels(self) -> None:
        samples = np.zeros((10_000, 2))
        samples[1234, 1] = 0.9
        samples[8000, 0] = -0.7
        times, minimums, maximums = waveform_envelope(samples, 1000, points=100)
        self.assertEqual(times.shape, (100,))
        self.assertAlmostEqual(float(maximums.max()), 0.9)
        self.assertAlmostEqual(float(minimums.min()), -0.7)

    def test_level_stats_of_half_scale_sine(self) -> None:
        time = np.arange(48_000) / 48_000
        stats = level_stats(0.5 * np.sin(2 * np.pi * 1000 * time))
        self.assertAlmostEqual(stats.peak_dbfs, -6.02, delta=0.05)
        self.assertAlmostEqual(stats.rms_dbfs, -9.03, delta=0.05)

    def test_energy_of_low_tone_is_in_bass_zone(self) -> None:
        sample_rate = 44_100
        time = np.arange(sample_rate * 2) / sample_rate
        frequencies, levels = spectrum_db(np.sin(2 * np.pi * 100 * time), sample_rate)
        shares = band_energy_shares(frequencies, levels, 250, 4000)
        self.assertGreater(shares["bass"], 0.99)
        self.assertAlmostEqual(sum(shares.values()), 1.0, places=6)

    def test_default_cutoffs_stay_below_nyquist(self) -> None:
        self.assertEqual(default_cutoffs(44_100), (250, 4000))
        low, high = default_cutoffs(8_000)
        self.assertLess(low, high)
        self.assertLess(high, 4_000)
        self.assertTrue(all(value < 4_000 for value in cutoff_options(8_000)))

    def test_gain_factor(self) -> None:
        self.assertAlmostEqual(gain_db_to_factor(6), 1.995, places=3)
        self.assertAlmostEqual(gain_db_to_factor(0), 1.0)


class PlaybackAndPipelineTests(unittest.TestCase):
    def test_playback_bytes_are_not_normalized(self) -> None:
        data = wav_bytes_for_playback(np.full(100, 0.25), 8000)
        sample_rate, written = wavfile.read(io.BytesIO(data))
        self.assertEqual(sample_rate, 8000)
        self.assertEqual(written.dtype, np.int16)
        self.assertAlmostEqual(int(written[0]), 8192, delta=1)
        with self.assertRaises(ValueError):
            wav_bytes_for_playback(np.array([1.2]), 8000)

    def test_read_wav_accepts_in_memory_file(self) -> None:
        buffer = io.BytesIO()
        wavfile.write(buffer, 16_000, np.zeros((1600, 2), dtype=np.int16))
        audio = read_wav(io.BytesIO(buffer.getvalue()))
        self.assertEqual(audio.sample_rate, 16_000)
        self.assertEqual(audio.samples.shape, (1600, 2))

    def test_pipeline_chains_backend_and_checks_shapes(self) -> None:
        clip = np.random.default_rng(0).uniform(-0.1, 0.1, size=(1000, 2))
        backend = PassThroughBackend()
        bands = split(backend, clip, 8000, 250, 2000)
        processed, output = equalize(backend, bands, {"bass": 6, "mid": 0, "treble": 0}, clip.shape)
        np.testing.assert_allclose(output, clip * gain_db_to_factor(6))
        with self.assertRaises(ValueError):
            validate_bands({"bass": clip, "mid": clip}, clip.shape)
        with self.assertRaises(ValueError):
            validate_bands({"bass": clip, "mid": clip, "treble": clip[:10]}, clip.shape)


if __name__ == "__main__":
    unittest.main()
