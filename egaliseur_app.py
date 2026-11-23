from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Mapping

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.io import wavfile

from audio_io import export_audio, extract_segment, read_wav, spectrum_db
from dsp_backend import BAND_NAMES, DSPBackend

try:
    import winsound
except ImportError:
    winsound = None


BAND_LABELS = {
    "bass": "Graves",
    "mid": "Médiums",
    "treble": "Aigus",
}
BAND_COLORS = {
    "bass": "#3973ac",
    "mid": "#db9d31",
    "treble": "#4b9b70",
}
GAIN_LIMIT_DB = 12


class AudioEqualizerApp:
    def __init__(self, root: tk.Tk, backend: DSPBackend | None = None) -> None:
        self.root = root
        self.backend = backend
        self.audio_path: Path | None = None
        self.samples: np.ndarray | None = None
        self.sample_rate: int | None = None
        self.source_dtype = ""
        self.clip: np.ndarray | None = None
        self.raw_bands: Mapping[str, np.ndarray] | None = None
        self.processed_bands: Mapping[str, np.ndarray] | None = None
        self.active_cutoffs: tuple[float, float] | None = None
        self.gains_db = {name: 0.0 for name in BAND_NAMES}
        self.playback_path: Path | None = None
        self.cutoff_low_var = tk.StringVar(value="250")
        self.cutoff_high_var = tk.StringVar(value="4000")
        self.segment_start_var = tk.StringVar(value="0")
        self.segment_duration_var = tk.StringVar(value="20")
        self.export_format_var = tk.StringVar(value="WAV")
        self.status_var = tk.StringVar(value="Importez un fichier WAV pour commencer.")
        self.metadata_var = tk.StringVar(value="Aucun fichier chargé.")
        self.gain_vars = {
            name: tk.StringVar(value="0 dB") for name in BAND_NAMES
        }

        self.root.title("Égaliseur audio numérique — Projet 2")
        self.root.geometry("1180x900")
        self.root.minsize(900, 700)
        self._build_interface()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build_interface(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            outer,
            text="Égaliseur audio numérique",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="Importez un WAV, visualisez son spectre, puis écoutez et exportez les résultats.",
        ).pack(anchor=tk.W, pady=(0, 10))

        file_row = ttk.Frame(outer)
        file_row.pack(fill=tk.X, pady=4)
        ttk.Button(file_row, text="Importer un WAV…", command=self._import_wav).pack(
            side=tk.LEFT
        )
        ttk.Label(
            file_row,
            textvariable=self.metadata_var,
            wraplength=900,
        ).pack(side=tk.LEFT, padx=12)

        settings = ttk.LabelFrame(outer, text="Extrait et séparations fréquentielles", padding=8)
        settings.pack(fill=tk.X, pady=5)

        ttk.Label(settings, text="Début (s) :").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.segment_start_var, width=8).grid(
            row=0, column=1, padx=(4, 12)
        )
        ttk.Label(settings, text="Durée (10–30 s) :").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.segment_duration_var, width=8).grid(
            row=0, column=3, padx=(4, 12)
        )
        ttk.Button(settings, text="Mettre à jour l'extrait", command=self._update_segment).grid(
            row=0, column=4, padx=(0, 16)
        )
        ttk.Label(settings, text="Coupure graves/médiums (Hz) :").grid(
            row=0, column=5, sticky=tk.W
        )
        ttk.Entry(settings, textvariable=self.cutoff_low_var, width=8).grid(
            row=0, column=6, padx=(4, 12)
        )
        ttk.Label(settings, text="Coupure médiums/aigus (Hz) :").grid(
            row=0, column=7, sticky=tk.W
        )
        ttk.Entry(settings, textvariable=self.cutoff_high_var, width=8).grid(
            row=0, column=8, padx=(4, 8)
        )
        ttk.Button(settings, text="Actualiser le graphe", command=self._refresh_spectrum).grid(
            row=0, column=9
        )

        controls = ttk.Frame(outer)
        controls.pack(fill=tk.X, pady=5)
        self.original_button = ttk.Button(
            controls, text="Écouter l'extrait original", command=self._play_original, state=tk.DISABLED
        )
        self.original_button.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="Arrêter", command=self._stop_audio).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        self.split_button = ttk.Button(
            controls, text="Séparer les bandes", command=self._split_bands, state=tk.DISABLED
        )
        self.split_button.pack(side=tk.LEFT, padx=(0, 12))

        gain_frame = ttk.LabelFrame(outer, text="Gain par bande (dB)", padding=8)
        gain_frame.pack(fill=tk.X, pady=4)
        self.band_play_buttons: dict[str, ttk.Button] = {}
        self.gain_buttons: list[ttk.Button] = []
        for column, name in enumerate(BAND_NAMES):
            card = ttk.Frame(gain_frame, padding=(8, 2))
            card.grid(row=0, column=column, sticky=tk.W, padx=14)
            ttk.Label(card, text=BAND_LABELS[name], font=("Segoe UI", 10, "bold")).pack(
                side=tk.LEFT, padx=(0, 8)
            )
            decrease = ttk.Button(
                card, text="−", width=3, command=lambda band=name: self._change_gain(band, -1)
            )
            decrease.pack(side=tk.LEFT)
            ttk.Label(card, textvariable=self.gain_vars[name], width=6, anchor=tk.CENTER).pack(
                side=tk.LEFT
            )
            increase = ttk.Button(
                card, text="+", width=3, command=lambda band=name: self._change_gain(band, 1)
            )
            increase.pack(side=tk.LEFT)
            self.gain_buttons.extend((decrease, increase))
            play_button = ttk.Button(
                card,
                text=f"Écouter {BAND_LABELS[name].lower()}",
                command=lambda band=name: self._play_band(band),
                state=tk.DISABLED,
            )
            play_button.pack(side=tk.LEFT, padx=(8, 0))
            self.band_play_buttons[name] = play_button

        output_row = ttk.Frame(outer)
        output_row.pack(fill=tk.X, pady=5)
        self.final_play_button = ttk.Button(
            output_row, text="Écouter le signal recombiné", command=self._play_final, state=tk.DISABLED
        )
        self.final_play_button.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(output_row, text="Format d'export :").pack(side=tk.LEFT)
        ttk.Combobox(
            output_row,
            textvariable=self.export_format_var,
            values=("WAV", "FLAC", "MP3"),
            state="readonly",
            width=8,
        ).pack(side=tk.LEFT, padx=5)
        self.export_button = ttk.Button(
            output_row, text="Exporter le signal recombiné…", command=self._export, state=tk.DISABLED
        )
        self.export_button.pack(side=tk.LEFT, padx=8)

        plot_frame = ttk.Frame(outer)
        plot_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.figure = Figure(figsize=(10, 7), dpi=95, constrained_layout=True)
        grid = self.figure.add_gridspec(4, 1, height_ratios=(2.0, 1.0, 1.0, 1.0))
        self.spectrum_axis = self.figure.add_subplot(grid[0])
        self.band_axes = [
            self.figure.add_subplot(grid[index]) for index in range(1, 4)
        ]
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_empty_band_axes()

        ttk.Label(
            outer,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=4,
        ).pack(fill=tk.X, pady=(6, 0))

    def _import_wav(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choisir un fichier audio WAV",
            filetypes=(("Fichiers WAV", "*.wav"),),
        )
        if not filename:
            return
        try:
            audio = read_wav(filename)
            if audio.samples.shape[0] < audio.sample_rate * 10:
                raise ValueError("Le fichier doit durer au moins 10 secondes pour le projet.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Import impossible", str(exc), parent=self.root)
            return

        self._stop_audio()
        self.audio_path = Path(filename)
        self.samples = audio.samples
        self.sample_rate = audio.sample_rate
        self.source_dtype = audio.source_dtype
        self.raw_bands = None
        self.processed_bands = None
        self.active_cutoffs = None
        self.gains_db = {name: 0.0 for name in BAND_NAMES}
        for name in BAND_NAMES:
            self.gain_vars[name].set("0 dB")

        channels = 1 if audio.samples.ndim == 1 else audio.samples.shape[1]
        duration = audio.samples.shape[0] / audio.sample_rate
        self.metadata_var.set(
            f"{self.audio_path.name} — {audio.sample_rate} Hz, "
            f"{channels} canal/canaux, {duration:.2f} s, données {audio.source_dtype}"
        )
        default_high = min(4000.0, audio.sample_rate * 0.4)
        default_low = min(250.0, default_high / 2)
        self.cutoff_low_var.set(f"{default_low:g}")
        self.cutoff_high_var.set(f"{default_high:g}")
        self.segment_start_var.set("0")
        self.segment_duration_var.set(f"{min(20.0, duration):g}")

        try:
            self._update_segment(show_success=False)
        except ValueError as exc:
            messagebox.showerror("Extrait invalide", str(exc), parent=self.root)
            return

        self.original_button.configure(state=tk.NORMAL)
        self._set_backend_controls()
        if audio.warnings:
            self.status_var.set(
                f"Fichier chargé avec avertissement WAV : {audio.warnings[0]}"
            )
        else:
            self.status_var.set("Fichier chargé. Les données originales restent inchangées.")

    def _update_segment(self, show_success: bool = True) -> None:
        if self.samples is None or self.sample_rate is None:
            messagebox.showinfo("Aucun fichier", "Importez d'abord un fichier WAV.", parent=self.root)
            return
        try:
            start = float(self.segment_start_var.get())
            duration = float(self.segment_duration_var.get())
            segment = extract_segment(self.samples, self.sample_rate, start, duration)
        except ValueError as exc:
            messagebox.showerror("Extrait invalide", str(exc), parent=self.root)
            return
        self.clip = segment
        self.raw_bands = None
        self.processed_bands = None
        self.active_cutoffs = None
        self._draw_empty_band_axes()
        self._set_backend_controls()
        self._refresh_spectrum()
        if show_success:
            self.status_var.set(f"Extrait mis à jour : {start:g} s à {start + duration:g} s.")

    def _get_cutoffs(self) -> tuple[float, float]:
        if self.sample_rate is None:
            raise ValueError("Importez d'abord un fichier WAV.")
        try:
            low = float(self.cutoff_low_var.get())
            high = float(self.cutoff_high_var.get())
        except ValueError as exc:
            raise ValueError("Les fréquences de coupure doivent être numériques.") from exc
        nyquist = self.sample_rate / 2
        if not 0 < low < high < nyquist:
            raise ValueError(
                f"Les coupures doivent respecter 0 < graves/médiums < médiums/aigus "
                f"< {nyquist:g} Hz (fréquence de Nyquist)."
            )
        return low, high

    def _refresh_spectrum(self) -> None:
        if self.clip is None or self.sample_rate is None:
            return
        try:
            low, high = self._get_cutoffs()
        except ValueError as exc:
            messagebox.showerror("Fréquences invalides", str(exc), parent=self.root)
            return

        if self.active_cutoffs != (low, high):
            self.raw_bands = None
            self.processed_bands = None
            self.active_cutoffs = (low, high)
            self._draw_empty_band_axes()
            self._set_backend_controls()

        frequencies, levels = spectrum_db(self.clip, self.sample_rate)
        positive = frequencies > 0
        nyquist = self.sample_rate / 2
        axis = self.spectrum_axis
        axis.clear()
        axis.plot(frequencies[positive], levels[positive], color="#243b53", linewidth=0.9)
        axis.axvspan(1, low, color=BAND_COLORS["bass"], alpha=0.12, label="Graves")
        axis.axvspan(low, high, color=BAND_COLORS["mid"], alpha=0.12, label="Médiums")
        axis.axvspan(high, nyquist, color=BAND_COLORS["treble"], alpha=0.12, label="Aigus")
        axis.axvline(low, color=BAND_COLORS["bass"], linestyle="--", linewidth=1)
        axis.axvline(high, color=BAND_COLORS["treble"], linestyle="--", linewidth=1)
        axis.set_xscale("log")
        axis.set_xlim(max(1, frequencies[positive][0]), nyquist)
        axis.set_xlabel("Fréquence (Hz)")
        axis.set_ylabel("Densité spectrale (dB/Hz)")
        axis.set_title("Spectre de l'extrait — zones de fréquences")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend(loc="upper right", ncol=3, fontsize=8)
        self.canvas.draw_idle()

    def _split_bands(self) -> None:
        if self.backend is None:
            self._show_backend_missing()
            return
        if self.clip is None or self.sample_rate is None:
            return
        try:
            low, high = self._get_cutoffs()
            self._refresh_spectrum()
            bands = self.backend.split_bands(self.clip, self.sample_rate, low, high)
            self._validate_bands(bands)
            self.raw_bands = bands
            self._refresh_processed_bands()
        except (NotImplementedError, ValueError, RuntimeError, OSError) as exc:
            messagebox.showerror("Séparation impossible", str(exc), parent=self.root)

    def _validate_bands(self, bands: Mapping[str, np.ndarray]) -> None:
        missing = [name for name in BAND_NAMES if name not in bands]
        if missing:
            raise ValueError(f"Le traitement n'a pas fourni ces bandes : {', '.join(missing)}.")
        expected_shape = self.clip.shape if self.clip is not None else None
        for name in BAND_NAMES:
            band = np.asarray(bands[name])
            if band.shape != expected_shape:
                raise ValueError(f"La bande {BAND_LABELS[name]} n'a pas la forme attendue.")
            if not np.all(np.isfinite(band)):
                raise ValueError(f"La bande {BAND_LABELS[name]} contient des valeurs non finies.")

    def _refresh_processed_bands(self) -> None:
        if self.backend is None or self.raw_bands is None:
            return
        self.processed_bands = None
        self._set_backend_controls()
        try:
            processed = self.backend.apply_gains(self.raw_bands, self.gains_db)
            self._validate_bands(processed)
        except (NotImplementedError, ValueError, RuntimeError, OSError) as exc:
            messagebox.showerror("Application du gain impossible", str(exc), parent=self.root)
            return
        self.processed_bands = processed
        self._plot_bands(processed)
        self._set_backend_controls()
        self.status_var.set("Bandes prêtes. Vous pouvez les écouter ou les recombiner.")

    def _change_gain(self, band: str, increment: int) -> None:
        new_gain = self.gains_db[band] + increment
        if not -GAIN_LIMIT_DB <= new_gain <= GAIN_LIMIT_DB:
            self.status_var.set(f"Le gain est limité à ±{GAIN_LIMIT_DB} dB.")
            return
        self.gains_db[band] = new_gain
        self.gain_vars[band].set(f"{new_gain:+g} dB" if new_gain else "0 dB")
        if self.raw_bands is not None:
            self._refresh_processed_bands()
        elif self.backend is None:
            self.status_var.set(
                "Valeur de gain mémorisée dans l'interface ; le traitement DSP reste à connecter."
            )
        else:
            self.status_var.set("Gain mémorisé. Séparez les bandes pour écouter le résultat.")

    def _plot_bands(self, bands: Mapping[str, np.ndarray]) -> None:
        if self.clip is None or self.sample_rate is None:
            return
        time = np.arange(self.clip.shape[0]) / self.sample_rate
        stride = max(1, len(time) // 5000)
        for axis, name in zip(self.band_axes, BAND_NAMES):
            values = np.asarray(bands[name])
            if values.ndim == 2:
                values = np.mean(values, axis=1)
            axis.clear()
            axis.plot(time[::stride], values[::stride], color=BAND_COLORS[name], linewidth=0.8)
            axis.set_title(f"{BAND_LABELS[name]} — forme d'onde", loc="left", fontsize=9)
            axis.set_ylabel("Amplitude")
            axis.grid(True, alpha=0.25)
        self.band_axes[-1].set_xlabel("Temps (s)")
        self.canvas.draw_idle()

    def _draw_empty_band_axes(self) -> None:
        for axis, name in zip(self.band_axes, BAND_NAMES):
            axis.clear()
            axis.set_title(f"{BAND_LABELS[name]} — forme d'onde", loc="left", fontsize=9)
            axis.text(
                0.5,
                0.5,
                "En attente de la séparation des bandes",
                transform=axis.transAxes,
                ha="center",
                va="center",
                color="#6b7280",
            )
            axis.set_yticks([])
            axis.set_xticks([])
        self.canvas.draw_idle()

    def _set_backend_controls(self) -> None:
        has_clip = self.clip is not None
        ready = self.backend is not None and has_clip
        self.split_button.configure(state=tk.NORMAL if has_clip else tk.DISABLED)
        bands_ready = ready and self.processed_bands is not None
        for button in self.band_play_buttons.values():
            button.configure(state=tk.NORMAL if bands_ready else tk.DISABLED)
        self.final_play_button.configure(state=tk.NORMAL if bands_ready else tk.DISABLED)
        self.export_button.configure(state=tk.NORMAL if bands_ready else tk.DISABLED)

    def _show_backend_missing(self) -> None:
        messagebox.showinfo(
            "Traitement DSP à connecter",
            "Les fonctions de filtrage, d'application des gains et de recombinaison "
            "restent à implémenter par votre groupe. Consultez dsp_backend.py et le README.",
            parent=self.root,
        )

    def _play_original(self) -> None:
        if self.clip is None or self.sample_rate is None:
            return
        self._play_samples(self.clip, "extrait original")

    def _play_band(self, band: str) -> None:
        if self.processed_bands is None:
            return
        self._play_samples(self.processed_bands[band], BAND_LABELS[band].lower())

    def _play_final(self) -> None:
        if self.backend is None or self.processed_bands is None:
            return
        try:
            samples = self.backend.recombine_bands(self.processed_bands)
            self._validate_output(samples)
        except (NotImplementedError, ValueError, RuntimeError, OSError) as exc:
            messagebox.showerror("Recombinaison impossible", str(exc), parent=self.root)
            return
        self._play_samples(samples, "signal recombiné")

    def _validate_output(self, samples: np.ndarray) -> None:
        if self.clip is None or samples.shape != self.clip.shape:
            raise ValueError("Le signal recombiné n'a pas la forme attendue.")
        if not np.all(np.isfinite(samples)):
            raise ValueError("Le signal recombiné contient des valeurs non finies.")

    def _play_samples(self, samples: np.ndarray, description: str) -> None:
        if winsound is None:
            messagebox.showerror(
                "Lecture indisponible",
                "La lecture intégrée de cette application nécessite Windows.",
                parent=self.root,
            )
            return
        if self.sample_rate is None:
            return
        if not np.all(np.isfinite(samples)) or float(np.max(np.abs(samples))) > 1.0:
            messagebox.showerror(
                "Lecture impossible",
                "Le signal dépasse le niveau numérique maximal. Réduisez les gains avant l'écoute.",
                parent=self.root,
            )
            return
        self._stop_audio()
        with tempfile.NamedTemporaryFile(prefix="egaliseur_", suffix=".wav", delete=False) as file:
            temporary_path = Path(file.name)
        try:
            pcm = np.rint(samples * 32_767).astype(np.int16)
            wavfile.write(str(temporary_path), self.sample_rate, pcm)
            winsound.PlaySound(
                str(temporary_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
        except (OSError, RuntimeError) as exc:
            temporary_path.unlink(missing_ok=True)
            messagebox.showerror("Lecture impossible", str(exc), parent=self.root)
            return
        self.playback_path = temporary_path
        duration_ms = int(samples.shape[0] / self.sample_rate * 1000) + 1000
        self.root.after(duration_ms, lambda path=temporary_path: self._cleanup_playback(path))
        self.status_var.set(f"Lecture : {description}.")

    def _stop_audio(self) -> None:
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
        if self.playback_path is not None:
            self.playback_path.unlink(missing_ok=True)
            self.playback_path = None
        self.status_var.set("Lecture arrêtée.")

    def _cleanup_playback(self, path: Path) -> None:
        if self.playback_path == path:
            path.unlink(missing_ok=True)
            self.playback_path = None

    def _export(self) -> None:
        if self.backend is None or self.processed_bands is None or self.sample_rate is None:
            return
        format_name = self.export_format_var.get()
        filename = filedialog.asksaveasfilename(
            title="Exporter le signal recombiné",
            defaultextension=f".{format_name.lower()}",
            filetypes=((f"{format_name} (*.{format_name.lower()})", f"*.{format_name.lower()}"),),
        )
        if not filename:
            return
        try:
            samples = self.backend.recombine_bands(self.processed_bands)
            self._validate_output(samples)
            saved_path = export_audio(samples, self.sample_rate, filename, format_name)
        except (NotImplementedError, OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("Export impossible", str(exc), parent=self.root)
            return
        self.status_var.set(f"Fichier exporté : {saved_path}")
        messagebox.showinfo("Export terminé", f"Fichier créé :\n{saved_path}", parent=self.root)

    def _close(self) -> None:
        self._stop_audio()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = AudioEqualizerApp(root, backend=None)
    root.mainloop()


if __name__ == "__main__":
    main()
