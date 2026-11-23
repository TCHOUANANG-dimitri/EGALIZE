from __future__ import annotations

import shutil
import subprocess
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.io.wavfile import WavFileWarning
from scipy.signal import welch


@dataclass(frozen=True)
class AudioFile:
    sample_rate: int
    samples: np.ndarray
    source_dtype: str
    warnings: tuple[str, ...] = ()


def samples_to_float(samples: np.ndarray) -> np.ndarray:
    if np.issubdtype(samples.dtype, np.integer):
        limits = np.iinfo(samples.dtype)
        if np.issubdtype(samples.dtype, np.unsignedinteger):
            midpoint = (limits.max + 1) / 2
            result = (samples.astype(np.float64) - midpoint) / midpoint
        else:
            result = samples.astype(np.float64) / (limits.max + 1)
    elif np.issubdtype(samples.dtype, np.floating):
        result = samples.astype(np.float64)
    else:
        raise ValueError(f"Format d'échantillons non pris en charge : {samples.dtype}")

    if not np.all(np.isfinite(result)):
        raise ValueError("Le fichier audio contient des valeurs non finies.")
    return result


def read_wav(path: str | Path) -> AudioFile:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", WavFileWarning)
        sample_rate, samples = wavfile.read(str(path))
    if sample_rate <= 0:
        raise ValueError("La fréquence d'échantillonnage du fichier est invalide.")
    if samples.ndim not in (1, 2):
        raise ValueError("Seuls les fichiers mono ou stéréo sont pris en charge.")
    if samples.shape[0] == 0:
        raise ValueError("Le fichier audio ne contient aucun échantillon.")
    return AudioFile(
        sample_rate=sample_rate,
        samples=samples_to_float(samples),
        source_dtype=str(samples.dtype),
        warnings=tuple(str(warning.message) for warning in caught),
    )


def extract_segment(
    samples: np.ndarray,
    sample_rate: int,
    start_seconds: float,
    duration_seconds: float,
) -> np.ndarray:
    if not np.isfinite(start_seconds) or start_seconds < 0:
        raise ValueError("Le début de l'extrait doit être un nombre positif ou nul.")
    if not np.isfinite(duration_seconds) or not 10 <= duration_seconds <= 30:
        raise ValueError("La durée de l'extrait doit être comprise entre 10 et 30 secondes.")

    start = int(round(start_seconds * sample_rate))
    end = start + int(round(duration_seconds * sample_rate))
    if end > samples.shape[0]:
        raise ValueError("L'extrait demandé dépasse la durée du fichier audio.")
    return samples[start:end].copy()


def spectrum_db(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    frequencies, power = welch(
        samples,
        fs=sample_rate,
        nperseg=min(8192, samples.shape[0]),
        axis=0,
    )
    if power.ndim == 2:
        power = np.mean(power, axis=1)
    decibels = 10 * np.log10(np.maximum(power, np.finfo(np.float64).tiny))
    return frequencies, decibels


def _validate_export_samples(samples: np.ndarray) -> None:
    if samples.ndim not in (1, 2) or samples.shape[0] == 0:
        raise ValueError("Le signal à exporter doit être mono ou stéréo et non vide.")
    if not np.issubdtype(samples.dtype, np.number) or not np.all(np.isfinite(samples)):
        raise ValueError("Le signal contient des valeurs non valides.")
    peak = float(np.max(np.abs(samples)))
    if peak > 1.0:
        raise ValueError(
            f"Le signal dépasse le niveau maximal (crête = {peak:.3f}). "
            "Réduisez les gains avant l'export ; aucune normalisation automatique n'est appliquée."
        )


def _write_pcm32_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    pcm = np.rint(np.clip(samples, -1.0, 1.0) * 2_147_483_647).astype(np.int32)
    wavfile.write(str(path), sample_rate, pcm)


def export_audio(
    samples: np.ndarray,
    sample_rate: int,
    destination: str | Path,
    output_format: str,
) -> Path:
    _validate_export_samples(samples)
    if sample_rate <= 0:
        raise ValueError("La fréquence d'échantillonnage doit être positive.")

    extensions = {"wav": ".wav", "flac": ".flac", "mp3": ".mp3"}
    format_name = output_format.lower()
    if format_name not in extensions:
        raise ValueError(f"Format d'export non pris en charge : {output_format}")
    target = Path(destination).with_suffix(extensions[format_name])

    if format_name == "wav":
        _write_pcm32_wav(target, samples, sample_rate)
        return target

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "L'export FLAC et MP3 nécessite FFmpeg. Installez-le ou exportez en WAV."
        )

    with tempfile.TemporaryDirectory(prefix="egaliseur_") as temporary_directory:
        temporary_wav = Path(temporary_directory) / "audio_temporaire.wav"
        _write_pcm32_wav(temporary_wav, samples, sample_rate)
        command = [ffmpeg, "-y", "-v", "error", "-i", str(temporary_wav)]
        if format_name == "flac":
            command.extend(["-c:a", "flac"])
        else:
            command.extend(["-c:a", "libmp3lame", "-q:a", "2"])
        command.append(str(target))
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or "Erreur inconnue de FFmpeg."
            raise RuntimeError(f"Échec de l'export {format_name.upper()} : {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("L'export audio a dépassé le délai autorisé.") from exc
    return target
