import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from egaliseur.audio_io import export_audio, extract_segment, read_wav, spectrum_db


class AudioIoTests(unittest.TestCase):
    def test_extract_segment_keeps_requested_duration_and_rejects_out_of_range(self) -> None:
        samples = np.zeros(40_000, dtype=np.float64)
        segment = extract_segment(samples, 1000, 2, 10)
        self.assertEqual(segment.shape[0], 10_000)
        with self.assertRaises(ValueError):
            extract_segment(samples, 1000, 0, 9)

    def test_read_wav_reports_sample_rate_and_channels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.wav"
            samples = np.zeros((12_000, 2), dtype=np.int16)
            wavfile.write(path, 12_000, samples)

            audio = read_wav(path)

        self.assertEqual(audio.sample_rate, 12_000)
        self.assertEqual(audio.samples.shape, (12_000, 2))
        self.assertEqual(audio.source_dtype, "int16")

    def test_read_wav_reports_truncated_payload_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.wav"
            wavfile.write(path, 8000, np.zeros(100, dtype=np.int16))
            path.write_bytes(path.read_bytes()[:-2])

            audio = read_wav(path)

        self.assertTrue(any("EOF prematurely" in warning for warning in audio.warnings))

    def test_spectrum_finds_tone_frequency(self) -> None:
        sample_rate = 8000
        time = np.arange(sample_rate) / sample_rate
        samples = np.sin(2 * np.pi * 440 * time)

        frequencies, levels = spectrum_db(samples, sample_rate)

        self.assertAlmostEqual(float(frequencies[np.argmax(levels)]), 440, delta=1)

    def test_export_wav_preserves_sample_rate_and_refuses_clipping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "result"
            samples = np.full(1000, 0.25, dtype=np.float64)
            output = export_audio(samples, 8000, destination, "WAV")
            sample_rate, written = wavfile.read(output)

            self.assertEqual(sample_rate, 8000)
            self.assertEqual(written.dtype, np.int32)
            with self.assertRaises(ValueError):
                export_audio(np.array([1.1]), 8000, destination, "WAV")


if __name__ == "__main__":
    unittest.main()
