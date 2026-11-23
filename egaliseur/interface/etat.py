"""État partagé entre les pages et accès aux données (mis en cache).

Streamlit efface l'état d'un widget dès que l'on quitte la page qui l'affiche.
Les valeurs à conserver d'une page à l'autre (extrait, coupures, gains…) sont
donc rangées sous des clés « canoniques » de `st.session_state`, distinctes des
clés des widgets. Chaque widget est recréé à partir de cette valeur et la
recopie dès qu'on le modifie (voir `bound`).
"""

from __future__ import annotations

import importlib
import inspect
import string
from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import streamlit as st

from ..audio_io import AudioFile, extract_segment, read_wav, spectrum_db, wav_bytes_for_playback
from ..dsp_backend import BAND_NAMES, DSPBackend
from ..pipeline import equalize, split
from ..signal_analysis import cutoff_options, default_cutoffs, level_stats, to_dbfs, waveform_envelope

PROJECT_DIR = Path(__file__).resolve().parents[2]
EXAMPLE_FILE = PROJECT_DIR / "donnees" / "originales" / "Techno_music_001.wav"
MIN_EXCERPT_S, MAX_EXCERPT_S = 10, 30
OUTPUT_CEILING_DBFS = -1.0

_DEFAULTS = {
    "source": None,
    "uploader_n": 0,
    "loaded_key": None,
    "versions": [],
    "excerpt_start": 0.0,
    "excerpt_duration": 20,
    "cutoffs": None,
    "protect_clip": True,
    "widget_gen": {},
    **{f"gain_{name}": 0 for name in BAND_NAMES},
}


def init_state() -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(value)


# ---------------------------------------------------------------------------
# Liaison widgets <-> valeurs canoniques
# ---------------------------------------------------------------------------
def widget_key(name: str) -> str:
    return f"w_{name}_{st.session_state.widget_gen.get(name, 0)}"


def set_value(name: str, value) -> None:
    """Change une valeur canonique et force la recréation du widget associé."""
    st.session_state[name] = value
    st.session_state.widget_gen[name] = st.session_state.widget_gen.get(name, 0) + 1


def sync(name: str, key: str) -> None:
    st.session_state[name] = st.session_state[key]


def bound(name: str) -> dict:
    """Paramètres à passer à un widget pour le lier à la valeur canonique `name`."""
    key = widget_key(name)
    return {"key": key, "value": st.session_state[name], "on_change": sync, "args": (name, key)}


# ---------------------------------------------------------------------------
# Piste audio
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Track:
    audio: AudioFile
    name: str
    key: str

    @property
    def sample_rate(self) -> int:
        return self.audio.sample_rate

    @property
    def duration(self) -> float:
        return self.audio.samples.shape[0] / self.audio.sample_rate

    @property
    def channels(self) -> int:
        return 1 if self.audio.samples.ndim == 1 else self.audio.samples.shape[1]

    @property
    def nyquist(self) -> float:
        return self.audio.sample_rate / 2


@st.cache_resource(max_entries=2, show_spinner=False)
def _load_audio(source_key: str, _source: dict) -> AudioFile:
    # Les paramètres préfixés par « _ » ne servent pas de clé de cache.
    if "data" in _source:
        return read_wav(BytesIO(_source["data"]))
    return read_wav(_source["path"])


def load_track() -> tuple[Track | None, str | None]:
    """Renvoie (piste, None), (None, message d'erreur) ou (None, None) si rien n'est importé."""
    source = st.session_state.source
    if source is None:
        return None, None
    try:
        with st.spinner(f"Lecture de {source['name']}…"):
            audio = _load_audio(source["key"], source)
        duration = audio.samples.shape[0] / audio.sample_rate
        if duration < MIN_EXCERPT_S:
            raise ValueError(
                f"le fichier dure {duration:.1f} s, or le sujet demande au moins {MIN_EXCERPT_S} s".replace(".", ",")
            )
        default_cutoffs(audio.sample_rate)
    except (OSError, ValueError) as error:
        return None, str(error)
    track = Track(audio=audio, name=source["name"], key=source["key"])
    if st.session_state.loaded_key != track.key:
        _reset_for(track)
    return track, None


def _reset_for(track: Track) -> None:
    set_value("excerpt_duration", int(min(20, max_excerpt(track.duration))))
    set_value("excerpt_start", 0.0)
    set_value("cutoffs", default_cutoffs(track.sample_rate))
    st.session_state.loaded_key = track.key


def on_upload(widget: str) -> None:
    uploaded = st.session_state.get(widget)
    if uploaded is None:
        return
    file_id = getattr(uploaded, "file_id", None) or f"{uploaded.name}:{uploaded.size}"
    st.session_state.source = {"name": uploaded.name, "key": f"import:{file_id}", "data": uploaded.getvalue()}


def use_example() -> None:
    st.session_state.source = {
        "name": EXAMPLE_FILE.name,
        "key": f"exemple:{EXAMPLE_FILE.stat().st_mtime}",
        "path": EXAMPLE_FILE,
    }


def clear_source() -> None:
    st.session_state.source = None
    st.session_state.loaded_key = None
    st.session_state.uploader_n += 1


# ---------------------------------------------------------------------------
# Extrait analysé
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Excerpt:
    clip: np.ndarray
    start: float
    duration: float
    analysis: dict

    @property
    def end(self) -> float:
        return self.start + self.duration


def max_excerpt(duration: float) -> int:
    return int(min(MAX_EXCERPT_S, np.floor(duration)))


def latest_start(track: Track, excerpt_duration: float) -> float:
    return float(np.floor((track.duration - excerpt_duration) * 2) / 2)


@st.cache_data(max_entries=12, show_spinner=False)
def _excerpt_analysis(source_key: str, start: float, duration: float, _clip: np.ndarray, sample_rate: int) -> dict:
    frequencies, levels = spectrum_db(_clip, sample_rate)
    return {
        "frequencies": frequencies,
        "levels": levels,
        "envelope": waveform_envelope(_clip, sample_rate, points=1500),
        "stats": level_stats(_clip),
        "wav": wav_bytes_for_playback(_clip, sample_rate),
    }


@st.cache_data(max_entries=4, show_spinner=False)
def file_envelope(source_key: str, _samples: np.ndarray, sample_rate: int):
    return waveform_envelope(_samples, sample_rate, points=1600)


def current_excerpt(track: Track) -> Excerpt:
    duration = int(min(max(int(st.session_state.excerpt_duration), MIN_EXCERPT_S), max_excerpt(track.duration)))
    if duration != st.session_state.excerpt_duration:
        set_value("excerpt_duration", duration)
    start = float(min(max(float(st.session_state.excerpt_start), 0.0), max(latest_start(track, duration), 0.0)))
    if start != st.session_state.excerpt_start:
        set_value("excerpt_start", start)
    clip = extract_segment(track.audio.samples, track.sample_rate, start, duration)
    analysis = _excerpt_analysis(track.key, start, float(duration), clip, track.sample_rate)
    return Excerpt(clip=clip, start=start, duration=float(duration), analysis=analysis)


# ---------------------------------------------------------------------------
# Coupures et gains
# ---------------------------------------------------------------------------
def current_cutoffs(track: Track) -> tuple:
    """Couple (coupure basse, coupure haute), tel que proposé par le curseur."""
    options = cutoff_options(track.sample_rate)
    cutoffs = st.session_state.cutoffs
    if cutoffs is None or not set(cutoffs) <= set(options) or cutoffs[0] >= cutoffs[1]:
        cutoffs = default_cutoffs(track.sample_rate)
        set_value("cutoffs", cutoffs)
    return tuple(cutoffs)


def on_cutoffs_change(key: str, options: list) -> None:
    """Recopie la valeur du curseur ; empêche les deux poignées d'être confondues."""
    low, high = st.session_state[key]
    if low != high:
        st.session_state.cutoffs = (low, high)
        return
    index = options.index(low)  # bande des médiums vide : on écarte les poignées
    set_value(
        "cutoffs",
        (options[index], options[index + 1]) if index + 1 < len(options) else (options[index - 1], options[index]),
    )


def current_gains() -> dict[str, int]:
    return {name: int(st.session_state[f"gain_{name}"]) for name in BAND_NAMES}


def apply_preset(values: tuple[int, int, int]) -> None:
    for name, value in zip(BAND_NAMES, values):
        set_value(f"gain_{name}", value)


# ---------------------------------------------------------------------------
# Traitement (actif seulement quand des filtres sont branchés)
# ---------------------------------------------------------------------------
def backend() -> DSPBackend | None:
    # Importé à chaque appel : une modification de filtres.py est prise en compte
    # sans redémarrer l'application.
    return importlib.import_module("egaliseur.filtres").BACKEND


def _fingerprint(dsp: DSPBackend) -> str:
    """Identifie la version du code des filtres, pour recalculer si on le modifie."""
    module = inspect.getmodule(type(dsp))
    path = getattr(module, "__file__", None)
    return f"{type(dsp).__qualname__}:{Path(path).stat().st_mtime if path else 0}"


@st.cache_resource(max_entries=2, show_spinner=False)
def _bands(source_key, start, duration, low, high, fingerprint, _dsp, _clip, sample_rate):
    bands = split(_dsp, _clip, sample_rate, low, high)
    spectra = {name: spectrum_db(band, sample_rate)[1] for name, band in bands.items()}
    return bands, spectra


@st.cache_resource(max_entries=4, show_spinner=False)
def _result(source_key, start, duration, low, high, gains, protect, fingerprint, _dsp, _bands, _shape, sample_rate):
    processed, output = equalize(_dsp, _bands, dict(zip(BAND_NAMES, gains)), _shape)
    raw_peak = float(np.max(np.abs(output)))
    attenuation_db = 0.0
    if protect and raw_peak > 1.0:
        factor = 10 ** (OUTPUT_CEILING_DBFS / 20) / raw_peak
        output = output * factor
        attenuation_db = to_dbfs(factor)

    def playable(signal: np.ndarray) -> bytes | None:
        try:
            return wav_bytes_for_playback(signal, sample_rate)
        except ValueError:  # dépasse 0 dBFS : refus d'écouter un signal écrêté
            return None

    return {
        "output": output,
        "raw_peak_dbfs": to_dbfs(raw_peak),
        "attenuation_db": attenuation_db,
        "stats": level_stats(output),
        "levels": spectrum_db(output, sample_rate)[1],
        "envelope": waveform_envelope(output, sample_rate, points=1500),
        "wav": playable(output),
        "band_wavs": {name: playable(band) for name, band in processed.items()},
    }


@dataclass(frozen=True)
class Processing:
    band_spectra: dict | None
    result: dict | None
    error: str | None


def current_processing(track: Track, excerpt: Excerpt) -> Processing | None:
    """Résultat de l'égalisation, ou None si aucun filtre n'est branché."""
    dsp = backend()
    if dsp is None:
        return None
    low, high = (float(value) for value in current_cutoffs(track))
    try:
        fingerprint = _fingerprint(dsp)
        with st.spinner("Égalisation en cours…"):
            bands, spectra = _bands(
                track.key, excerpt.start, excerpt.duration, low, high, fingerprint, dsp, excerpt.clip, track.sample_rate
            )
            result = _result(
                track.key, excerpt.start, excerpt.duration, low, high, tuple(current_gains().values()),
                bool(st.session_state.protect_clip), fingerprint, dsp, bands, excerpt.clip.shape, track.sample_rate,
            )
    except (NotImplementedError, ValueError, RuntimeError) as error:
        return Processing(band_spectra=None, result=None, error=str(error))
    return Processing(band_spectra=spectra, result=result, error=None)


# ---------------------------------------------------------------------------
# Versions enregistrées
# ---------------------------------------------------------------------------
def save_version(record: dict) -> None:
    letter = string.ascii_uppercase[len(st.session_state.versions) % 26]
    st.session_state.versions.append({"Version": f"Version {letter}", **record})


def clear_versions() -> None:
    st.session_state.versions = []
