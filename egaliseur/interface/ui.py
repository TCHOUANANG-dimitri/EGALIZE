"""Habillage visuel : thème clair bleu électrique / or / blanc, composants HTML minimaux."""

from __future__ import annotations

from html import escape

import streamlit as st

CSS = """
<style>
:root {
  --text: #0b1a33; --muted: #56657f; --line: #e3e9f5; --tint: #f5f8ff;
  --blue: #1f5bff; --blue-deep: #1238c4; --gold: #c58c12; --gold-2: #e8b43a;
  --shadow: 0 1px 2px rgba(16, 40, 100, .05), 0 10px 28px -16px rgba(16, 40, 100, .25);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMain"] { background: radial-gradient(1100px 420px at 88% -12%, rgba(31, 91, 255, .07), transparent 62%), #ffffff; }
[data-testid="stMainBlockContainer"] { max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem; }

/* Barre latérale bleu électrique */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1d50ff 0%, #1640e0 52%, #102fb4 100%) !important; border-right: none; }
[data-testid="stSidebar"] > div { background: transparent !important; }
[data-testid="stSidebarNav"] a { border-radius: 10px; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255, 255, 255, .10) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(255, 255, 255, .16) !important; box-shadow: inset 3px 0 0 #f2c14e; }
[data-testid="stSidebarNav"] span { color: #ffffff !important; }
[data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * { color: rgba(255, 255, 255, .62) !important; }

/* En-têtes */
.hero h1 { font-size: clamp(2.2rem, 4.4vw, 3rem); line-height: 1.05; margin: 8px 0 18px; padding: 0; font-weight: 760; letter-spacing: -.03em; color: var(--text); }
.hero h1 span { color: var(--gold); }
.progress { display: flex; gap: 6px; margin: 0 0 18px; }
.progress i { flex: 1; height: 4px; border-radius: 4px; background: var(--line); }
.progress i.done { background: var(--blue); }
.progress i.here { background: linear-gradient(90deg, var(--gold-2), var(--gold)); }
.page-head { display: flex; gap: 14px; align-items: center; margin: 0 0 18px; }
.page-num { flex: none; width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-weight: 750; font-size: 15px;
  color: #ffffff; background: linear-gradient(140deg, #3a72ff, #1238c4); }
.page-head h1 { font-size: 1.7rem; margin: 0; padding: 0; color: var(--text); font-weight: 720; letter-spacing: -.02em; }
.track { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.track strong { color: var(--text); font-size: 1.05rem; }
.track span { color: var(--muted); font-size: .9rem; }
.label { font-size: .82rem; font-weight: 650; color: var(--muted); margin: 0 0 4px; }
.note { font-size: .82rem; color: var(--muted); margin: 2px 0 0; }

/* Cartes */
[class*="st-key-card_"] { background: #ffffff; border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px; box-shadow: var(--shadow); }
[class*="st-key-band_"] { border-radius: 16px; border: 1px solid var(--line); border-top: 4px solid var(--c, var(--blue)); padding: 16px 18px; box-shadow: var(--shadow); background: #fff; }
.st-key-band_bass { --c: #1f5bff; } .st-key-band_mid { --c: #d39b1e; } .st-key-band_treble { --c: #7c5cff; }
.band-range { font-weight: 700; color: var(--text); font-size: 1.05rem; }
.band-range span { color: var(--muted); font-weight: 500; font-size: .9rem; margin-left: 8px; }

/* Navigation précédent / suivant */
[class*="st-key-nav_"] { margin-top: 24px; }
.st-key-nav_next a { background: linear-gradient(140deg, #3a72ff, #1640e0) !important; border-radius: 12px; padding: 10px 18px !important; }
.st-key-nav_next a, .st-key-nav_next a * { color: #ffffff !important; font-weight: 650; }
.st-key-nav_prev a { border: 1px solid var(--line); border-radius: 12px; padding: 10px 16px !important; background: #ffffff; }

[data-testid="stFileUploaderDropzone"] { background: #eef3ff; border: 1.5px dashed #8eabff; border-radius: 14px; }
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def hero() -> str:
    return '<div class="hero"><h1>Égaliseur audio <span>trois bandes</span></h1></div>'


def page_head(number: int, total: int, title: str) -> str:
    bars = "".join(
        f'<i class="{"done" if index < number else "here" if index == number else ""}"></i>'
        for index in range(1, total + 1)
    )
    return (
        f'<div class="progress">{bars}</div>'
        f'<div class="page-head"><span class="page-num">{number}</span><h1>{escape(title)}</h1></div>'
    )


def track_line(name: str, details: str) -> str:
    return f'<div class="track"><strong>{escape(name)}</strong><span>{escape(details)}</span></div>'


def label(text: str) -> str:
    return f'<div class="label">{escape(text)}</div>'


def note(text: str) -> str:
    return f'<div class="note">{escape(text)}</div>'


def band_range(label_text: str, range_text: str) -> str:
    return f'<div class="band-range">{escape(label_text)}<span>{escape(range_text)}</span></div>'
