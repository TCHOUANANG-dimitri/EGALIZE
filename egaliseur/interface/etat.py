"""État partagé entre les pages et calculs mis en cache.

Streamlit efface l'état d'un widget dès que l'on quitte sa page. Les valeurs à
conserver (extrait, coupures, gains, bande affichée) sont donc rangées sous des
clés « canoniques » de `st.session_state`, distinctes des clés des widgets
(voir `bound`).
"""

from __future__ import annotations

import importlib
import inspect
from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import streamlit as st

from ..audio_io import AudioFile, extract_segment, read_wav, spectrum_db, wav_bytes_for_playback
from ..dsp_backend import BAND_NAMES, DSPBackend
from ..pipeline import equalize, split
from ..signal_analysis import cutoff_options, default_cutoffs, to_dbfs, waveform_envelope

PROJECT_DIR = Path(__file__).resolve().parents[2]
EXAMPLE_FILE = PROJECT_DIR / "donnees" / "originales" / "Techno_music_001_extrait_0-20s.wav"
MIN_EXCERPT_S, MAX_EXCERPT_S = 10, 30
CEILING_DBFS = -1.0

_DEFAULTS = {
    "source": None,
    "uploader_n": 0,
    "loaded_key": None,
    "excerpt_start": 0.0,
    "excerpt_duration": 20,
    "cutoffs": None,
    "band": "bass",
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
            raise ValueError(f"le fichier doit durer au moins {MIN_EXCERPT_S} s")
        default_cutoffs(audio.sample_rate)
    except (OSError, ValueError) as error:
        return None, str(error)
    track = Track(audio=audio, name=source["name"], key=source["key"])
    if st.session_state.loaded_key != track.key:
        set_value("excerpt_duration", int(min(20, max_excerpt(track.duration))))
        set_value("excerpt_start", 0.0)
        set_value("cutoffs", default_cutoffs(track.sample_rate))
        st.session_state.loaded_key = track.key
    return track, None


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
# Analyse d'un signal (spectre, forme d'onde, écoute) — mise en cache
# ---------------------------------------------------------------------------
def playable(signal: np.ndarray, sample_rate: int) -> tuple[bytes, float]:
    """WAV pour l'écoute. Si le signal dépasse 0 dBFS, il est abaissé à -1 dBFS
    (renvoie l'abaissement en dB, 0 sinon) pour ne jamais écouter un signal écrêté."""
    peak = float(np.max(np.abs(signal)))
    attenuation_db = 0.0
    if peak > 1.0:
        factor = 10 ** (CEILING_DBFS / 20) / peak
        signal = signal * factor
        attenuation_db = to_dbfs(factor)
    return wav_bytes_for_playback(signal, sample_rate), attenuation_db


@st.cache_data(max_entries=40, show_spinner=False)
def _analyse(cache_key: tuple, _signal: np.ndarray, sample_rate: int) -> dict:
    frequencies, levels = spectrum_db(_signal, sample_rate)
    wav, attenuation_db = playable(_signal, sample_rate)
    return {
        "frequencies": frequencies,
        "levels": levels,
        "envelope": waveform_envelope(_signal, sample_rate, points=1200),
        "peak_dbfs": to_dbfs(float(np.max(np.abs(_signal)))),
        "wav": wav,
        "attenuation_db": attenuation_db,
    }


# ---------------------------------------------------------------------------
# Extrait
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Excerpt:
    clip: np.ndarray
    start: float
    duration: float
    key: tuple

    @property
    def end(self) -> float:
        return self.start + self.duration


def max_excerpt(duration: float) -> int:
    return int(min(MAX_EXCERPT_S, np.floor(duration)))


def latest_start(track: Track, excerpt_duration: float) -> float:
    return float(np.floor((track.duration - excerpt_duration) * 2) / 2)


def current_excerpt(track: Track) -> Excerpt:
    duration = int(min(max(int(st.session_state.excerpt_duration), MIN_EXCERPT_S), max_excerpt(track.duration)))
    if duration != st.session_state.excerpt_duration:
        set_value("excerpt_duration", duration)
    start = float(min(max(float(st.session_state.excerpt_start), 0.0), max(latest_start(track, duration), 0.0)))
    if start != st.session_state.excerpt_start:
        set_value("excerpt_start", start)
    clip = extract_segment(track.audio.samples, track.sample_rate, start, duration)
    return Excerpt(clip=clip, start=start, duration=float(duration), key=(track.key, start, float(duration)))


def analyse(track: Track, excerpt: Excerpt, label: str, signal: np.ndarray, *extra) -> dict:
    """Analyse mise en cache d'un signal dérivé de l'extrait (identifié par `label` et `extra`)."""
    cache_key = (*excerpt.key, current_cutoffs(track), _fingerprint(), label, *extra)
    return _analyse(cache_key, signal, track.sample_rate)


# ---------------------------------------------------------------------------
# Coupures et gains
# ---------------------------------------------------------------------------
def current_cutoffs(track: Track) -> tuple:
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
    index = options.index(low)
    set_value(
        "cutoffs",
        (options[index], options[index + 1]) if index + 1 < len(options) else (options[index - 1], options[index]),
    )


def current_gains() -> dict[str, int]:
    return {name: int(st.session_state[f"gain_{name}"]) for name in BAND_NAMES}


def reset_gains() -> None:
    for name in BAND_NAMES:
        set_value(f"gain_{name}", 0)


# ---------------------------------------------------------------------------
# Filtrage (egaliseur/filtres.py)
# ---------------------------------------------------------------------------
def backend() -> DSPBackend | None:
    # Importé à chaque appel : une modification de filtres.py est prise en compte sans redémarrer.
    return importlib.import_module("egaliseur.filtres").BACKEND


def _fingerprint() -> str:
    dsp = backend()
    if dsp is None:
        return "aucun"
    path = getattr(inspect.getmodule(type(dsp)), "__file__", None)
    return f"{type(dsp).__qualname__}:{Path(path).stat().st_mtime if path else 0}"


@st.cache_resource(max_entries=2, show_spinner=False)
def _bands(excerpt_key, low, high, fingerprint, _dsp, _clip, sample_rate):
    return split(_dsp, _clip, sample_rate, low, high)


@st.cache_resource(max_entries=4, show_spinner=False)
def _equalized(excerpt_key, low, high, gains, fingerprint, _dsp, _bands, _shape):
    return equalize(_dsp, _bands, dict(zip(BAND_NAMES, gains)), _shape)


def bands(track: Track, excerpt: Excerpt) -> dict[str, np.ndarray]:
    """Les trois bandes de l'extrait, avant gain."""
    dsp = backend()
    if dsp is None:
        raise RuntimeError("aucun filtre n'est branché dans egaliseur/filtres.py")
    low, high = (float(value) for value in current_cutoffs(track))
    with st.spinner("Séparation des bandes…"):
        return _bands(excerpt.key, low, high, _fingerprint(), dsp, excerpt.clip, track.sample_rate)


def equalized(track: Track, excerpt: Excerpt) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """(bandes après gain, signal recombiné)."""
    raw = bands(track, excerpt)
    low, high = (float(value) for value in current_cutoffs(track))
    gains = tuple(current_gains().values())
    return _equalized(excerpt.key, low, high, gains, _fingerprint(), backend(), raw, excerpt.clip.shape)
