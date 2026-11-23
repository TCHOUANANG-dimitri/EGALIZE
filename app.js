"use strict";

(() => {
  const $ = (selector) => document.querySelector(selector);
  const elements = {
    file: $("#audio-file"),
    dropzone: $("#dropzone"),
    dropTitle: $("#drop-title"),
    dropCaption: $("#drop-caption"),
    fileError: $("#file-error"),
    trackPanel: $("#track-panel"),
    trackName: $("#track-name"),
    trackSubtitle: $("#track-subtitle"),
    sampleRate: $("#sample-rate"),
    channelCount: $("#channel-count"),
    duration: $("#track-duration"),
    bitDepth: $("#bit-depth"),
    removeFile: $("#remove-file"),
    playOriginal: $("#play-original"),
    canvas: $("#spectrum-canvas"),
    emptyChart: $("#empty-chart"),
    lowCutoff: $("#low-cutoff"),
    highCutoff: $("#high-cutoff"),
    excerptStart: $("#excerpt-start"),
    excerptDuration: $("#excerpt-duration"),
    applyExcerpt: $("#apply-excerpt"),
    cutoffHelp: $("#cutoff-help"),
    resetCutoffs: $("#reset-cutoffs"),
    bassRange: $("#bass-range"),
    midRange: $("#mid-range"),
    trebleRange: $("#treble-range"),
    toast: $("#toast"),
    exportButton: $("#export-button"),
    splitBands: $("#split-bands"),
  };

  const state = {
    file: null,
    buffer: null,
    clip: null,
    sourceSampleRate: null,
    clipStart: 0,
    clipDuration: 0,
    gains: { bass: 0, mid: 0, treble: 0 },
    context: null,
    playback: null,
    toastTimer: null,
    resizeObserver: null,
  };

  function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.remove("hidden");
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(() => elements.toast.classList.add("hidden"), 3400);
  }

  function formatDuration(seconds) {
    const whole = Math.floor(seconds);
    const minutes = Math.floor(whole / 60);
    return `${String(minutes).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
  }

  function formatHz(value) {
    return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(value);
  }

  function readWavMetadata(arrayBuffer) {
    const view = new DataView(arrayBuffer);
    if (view.byteLength < 12
      || view.getUint32(0, false) !== 0x52494646
      || view.getUint32(8, false) !== 0x57415645) {
      throw new Error("Ce fichier ne contient pas un en-tête WAV reconnu.");
    }

    let format = null;
    for (let offset = 12; offset + 8 <= view.byteLength;) {
      const chunkId = view.getUint32(offset, false);
      const chunkSize = view.getUint32(offset + 4, true);
      const body = offset + 8;
      if (chunkId === 0x666d7420 && chunkSize >= 16 && body + 16 <= view.byteLength) {
        format = {
          encoding: view.getUint16(body, true),
          channels: view.getUint16(body + 2, true),
          sampleRate: view.getUint32(body + 4, true),
          bitsPerSample: view.getUint16(body + 14, true),
        };
        break;
      }
      if (chunkId === 0x64617461) break;
      const next = body + chunkSize + (chunkSize % 2);
      if (next <= offset || next > view.byteLength) break;
      offset = next;
    }

    if (!format || !format.sampleRate || !format.channels) {
      throw new Error("Impossible de lire les caractéristiques de l’en-tête WAV.");
    }
    return format;
  }

  function setError(message) {
    elements.fileError.textContent = message;
    elements.fileError.classList.toggle("hidden", !message);
  }

  function getCanvasContext() {
    const rect = elements.canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(rect.width * ratio));
    const height = Math.max(1, Math.round(rect.height * ratio));
    if (elements.canvas.width !== width || elements.canvas.height !== height) {
      elements.canvas.width = width;
      elements.canvas.height = height;
    }
    const context = elements.canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { context, width: rect.width, height: rect.height };
  }

  function validateCutoffs(showMessage = false) {
    if (!state.buffer) return false;
    const low = Number(elements.lowCutoff.value);
    const high = Number(elements.highCutoff.value);
    const nyquist = state.buffer.sampleRate / 2;
    const valid = Number.isFinite(low) && Number.isFinite(high) && low > 0 && low < high && high < nyquist;
    elements.cutoffHelp.classList.toggle("invalid", !valid);
    elements.cutoffHelp.textContent = valid
      ? `Points de séparation indicatifs. La fréquence de Nyquist de ce fichier est ${formatHz(nyquist)} Hz.`
      : `Entrez deux fréquences telles que 0 < graves/médiums < médiums/aigus < ${formatHz(nyquist)} Hz.`;
    if (showMessage && !valid) showToast("Vérifiez les deux fréquences de coupure avant de poursuivre.");
    if (valid) updateBandRanges();
    return valid;
  }

  function updateBandRanges() {
    if (!state.buffer) return;
    const nyquist = state.buffer.sampleRate / 2;
    const low = Number(elements.lowCutoff.value);
    const high = Number(elements.highCutoff.value);
    elements.bassRange.textContent = `20 — ${formatHz(low)} Hz`;
    elements.midRange.textContent = `${formatHz(low)} — ${formatHz(high)} Hz`;
    elements.trebleRange.textContent = `${formatHz(high)} — ${formatHz(nyquist)} Hz`;
  }

  function logFrequencyX(frequency, width, padding) {
    const minFrequency = 20;
    const maxFrequency = state.buffer.sampleRate / 2;
    const bounded = Math.min(maxFrequency, Math.max(minFrequency, frequency));
    return padding.left + (Math.log(bounded / minFrequency) / Math.log(maxFrequency / minFrequency)) * (width - padding.left - padding.right);
  }

  function drawSpectrum() {
    if (!state.buffer) return;
    const { context: ctx, width, height } = getCanvasContext();
    const ratio = window.devicePixelRatio || 1;
    const padding = { top: 14, right: 13, bottom: 28, left: 36 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const sampleRate = state.buffer.sampleRate;
    const nyquist = sampleRate / 2;
    const low = Number(elements.lowCutoff.value);
    const high = Number(elements.highCutoff.value);
    const valid = validateCutoffs();

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#17273c";
    ctx.fillRect(0, 0, width, height);

    const bandStops = [
      { from: 20, to: valid ? low : 250, color: "74,145,255" },
      { from: valid ? low : 250, to: valid ? high : 4000, color: "220,170,85" },
      { from: valid ? high : 4000, to: nyquist, color: "142,122,255" },
    ];
    bandStops.forEach((band) => {
      const start = logFrequencyX(band.from, width, padding);
      const end = logFrequencyX(band.to, width, padding);
      ctx.fillStyle = `rgba(${band.color}, .11)`;
      ctx.fillRect(start, padding.top, Math.max(0, end - start), plotHeight);
    });

    ctx.font = "9px 'DM Mono', monospace";
    ctx.textAlign = "right";
    [0, -20, -40, -60].forEach((db) => {
      const y = padding.top + ((-db) / 70) * plotHeight;
      ctx.strokeStyle = "#394e68";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.fillStyle = "#a9bad0";
      ctx.fillText(`${db}`, padding.left - 7, y + 3);
    });

    const bins = state.spectrum;
    if (bins && bins.length) {
      ctx.beginPath();
      let fillStarted = false;
      bins.forEach((value, index) => {
        const frequency = (index / bins.length) * nyquist;
        if (frequency < 20) return;
        const x = logFrequencyX(frequency, width, padding);
        const normalized = Math.min(1, Math.max(0, (value + 70) / 70));
        const y = padding.top + (1 - normalized) * plotHeight;
        if (!fillStarted) {
          ctx.moveTo(x, y);
          fillStarted = true;
        } else ctx.lineTo(x, y);
      });
      ctx.lineTo(width - padding.right, padding.top + plotHeight);
      ctx.lineTo(padding.left, padding.top + plotHeight);
      ctx.closePath();
      const fill = ctx.createLinearGradient(0, padding.top, 0, padding.top + plotHeight);
      fill.addColorStop(0, "rgba(77, 145, 255, .29)");
      fill.addColorStop(1, "rgba(77, 145, 255, .015)");
      ctx.fillStyle = fill;
      ctx.fill();

      ctx.beginPath();
      let lineStarted = false;
      bins.forEach((value, index) => {
        const frequency = (index / bins.length) * nyquist;
        if (frequency < 20) return;
        const x = logFrequencyX(frequency, width, padding);
        const normalized = Math.min(1, Math.max(0, (value + 70) / 70));
        const y = padding.top + (1 - normalized) * plotHeight;
        if (!lineStarted) {
          ctx.moveTo(x, y);
          lineStarted = true;
        } else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = "#76aaff";
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }

    [low, high].forEach((cutoff, index) => {
      if (!valid) return;
      const x = logFrequencyX(cutoff, width, padding);
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = index === 0 ? "#65a0ff" : "#dfb366";
      ctx.beginPath();
      ctx.moveTo(x, padding.top);
      ctx.lineTo(x, padding.top + plotHeight);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    const ticks = [20, 100, 1000, 10000, nyquist].filter((value, index, list) => value <= nyquist && list.indexOf(value) === index);
    ticks.forEach((value) => {
      const x = logFrequencyX(value, width, padding);
      ctx.strokeStyle = "#61758f";
      ctx.beginPath();
      ctx.moveTo(x, height - padding.bottom + 1);
      ctx.lineTo(x, height - padding.bottom + 4);
      ctx.stroke();
      ctx.fillStyle = "#bdcadd";
      ctx.font = "8px 'DM Mono', monospace";
      ctx.textAlign = x < padding.left + 24 ? "left" : x > width - padding.right - 28 ? "right" : "center";
      const label = value >= 1000
        ? `${Number((value / 1000).toFixed(value % 1000 ? 1 : 0))}k`
        : String(value);
      ctx.fillText(label, x, height - 7);
    });
    elements.emptyChart.classList.add("hidden");
  }

  function calculateSpectrum(buffer) {
    const fftSize = 32768;
    const source = buffer.getChannelData(0);
    const count = Math.min(source.length, fftSize);
    const start = Math.max(0, Math.floor((source.length - count) / 2));
    const real = new Float64Array(fftSize);
    const imaginary = new Float64Array(fftSize);
    let mean = 0;
    for (let i = 0; i < count; i += 1) mean += source[start + i];
    mean /= count || 1;
    for (let i = 0; i < count; i += 1) {
      const hann = count > 1 ? 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (count - 1)) : 1;
      real[i] = (source[start + i] - mean) * hann;
    }

    for (let i = 1, j = 0; i < fftSize; i += 1) {
      let bit = fftSize >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) {
        [real[i], real[j]] = [real[j], real[i]];
        [imaginary[i], imaginary[j]] = [imaginary[j], imaginary[i]];
      }
    }

    for (let size = 2; size <= fftSize; size <<= 1) {
      const angle = (-2 * Math.PI) / size;
      const stepReal = Math.cos(angle);
      const stepImaginary = Math.sin(angle);
      const half = size >> 1;
      for (let offset = 0; offset < fftSize; offset += size) {
        let twiddleReal = 1;
        let twiddleImaginary = 0;
        for (let j = 0; j < half; j += 1) {
          const even = offset + j;
          const odd = even + half;
          const oddReal = real[odd] * twiddleReal - imaginary[odd] * twiddleImaginary;
          const oddImaginary = real[odd] * twiddleImaginary + imaginary[odd] * twiddleReal;
          real[odd] = real[even] - oddReal;
          imaginary[odd] = imaginary[even] - oddImaginary;
          real[even] += oddReal;
          imaginary[even] += oddImaginary;
          const nextReal = twiddleReal * stepReal - twiddleImaginary * stepImaginary;
          twiddleImaginary = twiddleReal * stepImaginary + twiddleImaginary * stepReal;
          twiddleReal = nextReal;
        }
      }
    }

    const result = new Float32Array(fftSize / 2);
    const normalization = Math.max(1, count);
    for (let i = 0; i < result.length; i += 1) {
      const magnitude = Math.hypot(real[i], imaginary[i]) / normalization;
      result[i] = Math.max(-100, 20 * Math.log10(Math.max(magnitude, 1e-8)));
    }
    return result;
  }

  function applyExcerpt(showMessage = true) {
    if (!state.buffer || !state.context) return false;
    const start = Number(elements.excerptStart.value);
    const duration = Number(elements.excerptDuration.value);
    const valid = Number.isFinite(start)
      && Number.isFinite(duration)
      && start >= 0
      && duration >= 10
      && duration <= 30
      && start + duration <= state.buffer.duration;
    if (!valid) {
      if (showMessage) {
        showToast(`Choisissez un extrait de 10 à 30 s situé dans les ${formatDuration(state.buffer.duration)} du fichier.`);
      }
      return false;
    }

    stopPlayback();
    const firstSample = Math.round(start * state.buffer.sampleRate);
    const frameCount = Math.round(duration * state.buffer.sampleRate);
    const clip = state.context.createBuffer(
      state.buffer.numberOfChannels,
      frameCount,
      state.buffer.sampleRate,
    );
    for (let channel = 0; channel < state.buffer.numberOfChannels; channel += 1) {
      const source = state.buffer.getChannelData(channel).subarray(firstSample, firstSample + frameCount);
      clip.copyToChannel(source, channel);
    }
    state.clip = clip;
    state.clipStart = start;
    state.clipDuration = duration;
    state.spectrum = calculateSpectrum(clip);
    drawSpectrum();
    return true;
  }

  function updateGainDisplay(band) {
    const value = state.gains[band];
    const output = $(`#${band}-gain`);
    output.innerHTML = `${value > 0 ? "+" : ""}${value} <small>dB</small>`;
    const card = $(`[data-band-card="${band}"]`);
    if (card) card.dataset.gain = String(value);
  }

  async function loadFile(file) {
    setError("");
    if (!file) return;
    if (!/\.wav$/i.test(file.name) && file.type !== "audio/wav" && file.type !== "audio/x-wav") {
      setError("Choisissez un fichier WAV. Les autres formats ne sont pas pris en charge pour le moment.");
      return;
    }
    try {
      const bytes = await file.arrayBuffer();
      const wav = readWavMetadata(bytes);
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) throw new Error("Votre navigateur ne prend pas en charge l’analyse audio Web.");
      stopPlayback();
      if (state.context && state.context.sampleRate !== wav.sampleRate) {
        await state.context.close();
        state.context = null;
      }
      state.context = state.context || new AudioContextClass({ sampleRate: wav.sampleRate });
      if (state.context.state === "suspended") await state.context.resume();
      const decoded = await state.context.decodeAudioData(bytes.slice(0));
      if (decoded.numberOfChannels > 2) throw new Error("Seuls les fichiers mono ou stéréo sont pris en charge.");
      if (decoded.duration < 10) throw new Error("Le fichier doit durer au moins 10 secondes.");

      stopPlayback();
      state.file = file;
      state.buffer = decoded;
      state.sourceSampleRate = wav.sampleRate;
      elements.dropTitle.textContent = "Fichier importé";
      elements.dropCaption.textContent = "Choisissez un autre fichier en cliquant ici";
      elements.trackName.textContent = file.name;
      elements.trackSubtitle.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} Mo · audio d’origine conservé`;
      elements.sampleRate.textContent = `${formatHz(wav.sampleRate)} Hz`;
      elements.channelCount.textContent = wav.channels === 1 ? "Mono" : wav.channels === 2 ? "Stéréo" : `${wav.channels} canaux`;
      elements.duration.textContent = formatDuration(decoded.duration);
      elements.bitDepth.textContent = `${wav.bitsPerSample}-bit`;
      elements.trackPanel.classList.remove("hidden");
      elements.playOriginal.disabled = false;
      elements.applyExcerpt.disabled = false;
      elements.splitBands.disabled = false;
      elements.excerptStart.value = "0";
      elements.excerptDuration.value = String(Math.min(20, Math.floor(decoded.duration)));
      const nyquist = decoded.sampleRate / 2;
      const defaultHigh = Math.min(4000, Math.floor(nyquist * 0.8));
      const defaultLow = Math.min(250, Math.floor(defaultHigh / 2));
      elements.lowCutoff.value = String(defaultLow);
      elements.highCutoff.value = String(defaultHigh);
      state.gains = { bass: 0, mid: 0, treble: 0 };
      Object.keys(state.gains).forEach(updateGainDisplay);
      updateBandRanges();
      applyExcerpt(false);
      showToast("Fichier chargé. Votre audio original n’a pas été modifié.");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Impossible de lire ce fichier audio.");
      elements.trackPanel.classList.add("hidden");
      elements.playOriginal.disabled = true;
      state.buffer = null;
      state.spectrum = null;
      drawEmptySpectrum();
    }
  }

  function drawEmptySpectrum() {
    const rect = elements.canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    elements.canvas.width = Math.max(1, Math.round(rect.width * ratio));
    elements.canvas.height = Math.max(1, Math.round(rect.height * ratio));
    const ctx = elements.canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    elements.emptyChart.classList.remove("hidden");
  }

  function stopPlayback() {
    if (state.playback) {
      try { state.playback.stop(); } catch { /* Playback may already have ended. */ }
      state.playback.disconnect();
      state.playback = null;
    }
    elements.playOriginal.innerHTML = '<span class="play-mini" aria-hidden="true">▶</span> Écouter l’original';
  }

  async function playOriginal() {
    if (!state.clip || !state.context) return;
    if (state.playback) {
      stopPlayback();
      return;
    }
    try {
      if (state.context.state === "suspended") await state.context.resume();
      const source = state.context.createBufferSource();
      source.buffer = state.clip;
      source.connect(state.context.destination);
      source.onended = () => {
        if (state.playback === source) stopPlayback();
      };
      source.start();
      state.playback = source;
      elements.playOriginal.innerHTML = '<span class="play-mini" aria-hidden="true">■</span> Arrêter la lecture';
    } catch (error) {
      showToast(error instanceof Error ? error.message : "La lecture n’a pas pu démarrer.");
    }
  }

  function clearFile() {
    stopPlayback();
    state.file = null;
    state.buffer = null;
    state.clip = null;
    state.spectrum = null;
    elements.file.value = "";
    elements.dropTitle.textContent = "Déposez votre fichier ici";
    elements.dropCaption.innerHTML = 'ou <span class="browse-link">parcourez vos fichiers</span> · WAV uniquement';
    elements.trackPanel.classList.add("hidden");
    elements.playOriginal.disabled = true;
    elements.applyExcerpt.disabled = true;
    elements.splitBands.disabled = true;
    elements.cutoffHelp.textContent = "Les fréquences de coupure sont des points de départ. Elles doivent rester sous la fréquence de Nyquist.";
    elements.cutoffHelp.classList.remove("invalid");
    setError("");
    drawEmptySpectrum();
  }

  elements.file.addEventListener("change", (event) => loadFile(event.target.files?.[0]));
  elements.dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      elements.file.click();
    }
  });
  ["dragenter", "dragover"].forEach((name) => elements.dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    elements.dropzone.classList.add("drag-over");
  }));
  ["dragleave", "drop"].forEach((name) => elements.dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    elements.dropzone.classList.remove("drag-over");
  }));
  elements.dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (file) loadFile(file);
  });
  elements.removeFile.addEventListener("click", clearFile);
  elements.playOriginal.addEventListener("click", playOriginal);
  elements.applyExcerpt.addEventListener("click", () => {
    if (applyExcerpt()) showToast("Extrait mis à jour. Le spectre correspond maintenant à cette sélection.");
  });
  elements.splitBands.addEventListener("click", () => {
    if (!validateCutoffs(true)) return;
    showToast("Les fréquences de coupure sont prêtes. Connectez maintenant vos filtres pour séparer les bandes.");
  });
  [elements.lowCutoff, elements.highCutoff].forEach((input) => input.addEventListener("input", () => {
    if (state.buffer) {
      validateCutoffs();
      drawSpectrum();
    }
  }));
  elements.resetCutoffs.addEventListener("click", () => {
    if (!state.buffer) {
      elements.lowCutoff.value = "250";
      elements.highCutoff.value = "4000";
      return;
    }
    const nyquist = state.buffer.sampleRate / 2;
    const high = Math.min(4000, Math.floor(nyquist * 0.8));
    elements.lowCutoff.value = String(Math.min(250, Math.floor(high / 2)));
    elements.highCutoff.value = String(high);
    drawSpectrum();
  });
  document.querySelectorAll(".gain-button").forEach((button) => button.addEventListener("click", () => {
    const band = button.dataset.band;
    const next = state.gains[band] + Number(button.dataset.step);
    if (next < -12 || next > 12) return;
    state.gains[band] = next;
    updateGainDisplay(band);
    showToast(`${band === "bass" ? "Graves" : band === "mid" ? "Médiums" : "Aigus"} : ${next > 0 ? "+" : ""}${next} dB · filtre à connecter`);
  }));
  document.querySelectorAll(".listen-band").forEach((button) => button.addEventListener("click", () => {
    showToast("L’écoute de cette bande sera disponible après l’implémentation du filtre correspondant.");
  }));
  elements.exportButton.addEventListener("click", () => {
    showToast("Connectez la recombinaison des bandes pour exporter le mix.");
  });

  if ("ResizeObserver" in window) {
    state.resizeObserver = new ResizeObserver(() => state.buffer ? drawSpectrum() : drawEmptySpectrum());
    state.resizeObserver.observe(elements.canvas.parentElement);
  } else {
    window.addEventListener("resize", () => state.buffer ? drawSpectrum() : drawEmptySpectrum());
  }
  document.querySelectorAll(".step-link").forEach((link) => link.addEventListener("click", () => {
    document.querySelectorAll(".step-link").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  }));
  drawEmptySpectrum();
})();
