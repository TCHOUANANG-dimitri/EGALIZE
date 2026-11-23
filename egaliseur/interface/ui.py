"""Habillage visuel : feuille de style (thème clair bleu électrique / or / blanc)
et petits composants HTML réutilisés par les pages."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

import streamlit as st

CSS = """
<style>
:root {
  --text: #0b1a33; --muted: #56657f; --faint: #8693a9; --line: #e3e9f5; --tint: #f5f8ff;
  --blue: #1f5bff; --blue-deep: #1238c4; --blue-soft: #eef3ff;
  --gold: #c58c12; --gold-2: #e8b43a; --gold-soft: #fff6df;
  --bass: #1f5bff; --mid: #d39b1e; --treble: #7c5cff; --ok: #12a67a; --danger: #e5484d;
  --shadow: 0 1px 2px rgba(16, 40, 100, .05), 0 10px 28px -16px rgba(16, 40, 100, .25);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMain"] { background: radial-gradient(1100px 420px at 88% -12%, rgba(31, 91, 255, .08), transparent 62%), #ffffff; }
[data-testid="stMainBlockContainer"] { max-width: 1160px; padding-top: 2.2rem; padding-bottom: 4rem; }

/* ---------- Barre latérale bleu électrique ---------- */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1d50ff 0%, #1640e0 52%, #102fb4 100%) !important; border-right: none; }
[data-testid="stSidebar"] > div { background: transparent !important; }
[data-testid="stSidebarNav"] a { border-radius: 10px; }
[data-testid="stSidebarNav"] a:hover { background: rgba(255, 255, 255, .10) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"], [data-testid="stSidebarNavLink"][aria-current="page"] {
  background: rgba(255, 255, 255, .16) !important; box-shadow: inset 3px 0 0 #f2c14e; }
[data-testid="stSidebarNav"] span { color: #ffffff !important; }
[data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * { color: rgba(255, 255, 255, .62) !important; letter-spacing: .14em; font-size: 11px !important; }
.side-label { font-size: 10px; letter-spacing: .17em; color: rgba(255, 255, 255, .62); font-weight: 650; margin: 14px 0 8px; }
.dsp-card { display: flex; gap: 11px; padding: 12px 13px; border-radius: 12px; border: 1px dashed rgba(242, 193, 78, .85); background: rgba(255, 255, 255, .08); }
.dsp-card b { display: block; color: #ffffff; font-size: 13.2px; }
.dsp-card small { display: block; color: rgba(255, 255, 255, .8); font-size: 11.8px; line-height: 1.45; margin-top: 2px; }
.dsp-card.ok { border: 1px solid rgba(255, 255, 255, .4); }
.pulse { width: 9px; height: 9px; border-radius: 50%; background: #f2c14e; margin-top: 5px; flex: none; animation: pulse 2.2s infinite; }
.dsp-card.ok .pulse { background: #4ee0a8; animation: none; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(242, 193, 78, .7); } 70% { box-shadow: 0 0 0 7px rgba(242, 193, 78, 0); } 100% { box-shadow: 0 0 0 0 rgba(242, 193, 78, 0); } }
.checklist { list-style: none; padding: 0; margin: 0; }
.checklist li { display: flex; gap: 9px; font-size: 12.4px; color: rgba(255, 255, 255, .7); padding: 3px 0; line-height: 1.4; margin: 0; }
.checklist li i { font-style: normal; width: 14px; flex: none; text-align: center; color: rgba(255, 255, 255, .45); }
.checklist li.ok { color: #ffffff; }
.checklist li.ok i { color: #f2c14e; font-weight: 700; }
.side-note { font-size: 11.8px; color: rgba(255, 255, 255, .82); line-height: 1.5; padding: 10px 12px; border-radius: 10px; background: rgba(255, 255, 255, .08); margin-top: 16px; }

/* ---------- En-têtes ---------- */
.eyebrow { display: flex; align-items: center; gap: 10px; font-size: 11.5px; letter-spacing: .17em; color: var(--gold); font-weight: 700; }
.eyebrow-line { width: 26px; height: 2px; background: var(--gold-2); border-radius: 2px; }
.hero { padding: 4px 0 8px; }
.hero h1 { font-size: clamp(2.2rem, 4.4vw, 3.15rem); line-height: 1.05; margin: 14px 0 12px; padding: 0; font-weight: 760; letter-spacing: -.03em; color: var(--text); }
.hero h1 span { background: linear-gradient(90deg, #e8b43a, #b47c0c); -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero p { color: var(--muted); max-width: 660px; font-size: 1.05rem; line-height: 1.55; margin: 0; }
.page-head { display: flex; gap: 16px; align-items: flex-start; margin: 0 0 14px; }
.page-num { flex: none; width: 46px; height: 46px; border-radius: 14px; display: grid; place-items: center; font-weight: 750; font-size: 15px;
  color: #ffffff; background: linear-gradient(140deg, #3a72ff, #1238c4); box-shadow: 0 8px 18px -8px rgba(31, 91, 255, .6); }
.page-head .kicker { font-size: 10.5px; letter-spacing: .16em; color: var(--gold); font-weight: 700; }
.page-head h1 { font-size: 1.85rem; margin: 2px 0 4px; padding: 0; color: var(--text); font-weight: 720; letter-spacing: -.02em; }
.page-head p { margin: 0; color: var(--muted); font-size: .97rem; line-height: 1.5; max-width: 780px; }
.progress { display: flex; gap: 6px; margin: 0 0 22px; }
.progress i { flex: 1; height: 4px; border-radius: 4px; background: var(--line); }
.progress i.done { background: var(--blue); }
.progress i.here { background: linear-gradient(90deg, var(--gold-2), var(--gold)); }
.context { display: flex; flex-wrap: wrap; gap: 8px; margin: -4px 0 20px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; font-size: 12.3px; color: var(--muted);
  background: var(--tint); border: 1px solid var(--line); }
.chip b { color: var(--text); font-weight: 600; }

/* ---------- Cartes ---------- */
[class*="st-key-card_"] { background: #ffffff; border: 1px solid var(--line); border-radius: 16px; padding: 18px 18px 16px; box-shadow: var(--shadow); }
.card-title { font-weight: 680; color: var(--text); font-size: 1.02rem; margin: 0 0 2px; }
.card-sub { color: var(--muted); font-size: .86rem; margin: 0; line-height: 1.45; }
.track { display: flex; align-items: center; gap: 14px; padding: 14px 16px; background: #ffffff; border: 1px solid var(--line); border-radius: 14px; box-shadow: var(--shadow); }
.track-icon { width: 46px; height: 46px; border-radius: 12px; display: grid; place-items: center; font-size: 20px; color: #ffffff;
  background: linear-gradient(140deg, #3a72ff, #1238c4); flex: none; }
.track strong { display: block; color: var(--text); font-size: 1.04rem; word-break: break-all; }
.track span { display: block; color: var(--muted); font-size: .84rem; margin-top: 2px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
.stat { background: #ffffff; border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px 11px; box-shadow: var(--shadow); }
.stat span { display: block; font-size: 10px; letter-spacing: .13em; color: var(--faint); font-weight: 700; }
.stat strong { display: block; font-size: 1.24rem; color: var(--blue-deep); margin-top: 5px; font-weight: 700; letter-spacing: -.01em; }
.stat em { display: block; font-style: normal; font-size: 11.5px; color: var(--muted); margin-top: 1px; }

/* ---------- Bandes ---------- */
.band-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 6px; }
.band-pill { background: #ffffff; border: 1px solid var(--line); border-top: 3px solid var(--c); border-radius: 12px; padding: 11px 14px 12px; }
.band-pill-top { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.band-pill-top b { color: var(--text); font-size: .98rem; }
.band-pill-top span { color: var(--muted); font-size: .8rem; white-space: nowrap; }
.band-bar { height: 6px; border-radius: 6px; background: var(--tint); margin: 10px 0 7px; overflow: hidden; }
.band-bar i { display: block; height: 100%; border-radius: 6px; background: var(--c); }
.band-pill-foot { color: var(--muted); font-size: .8rem; }
.band-pill-foot strong { color: var(--c); font-size: .95rem; margin-right: 3px; }
[class*="st-key-band_"] { background: #ffffff; border: 1px solid var(--line); border-radius: 16px; padding: 16px 16px 14px; box-shadow: var(--shadow); }
.st-key-band_bass { border-top: 4px solid var(--bass) !important; }
.st-key-band_mid { border-top: 4px solid var(--mid) !important; }
.st-key-band_treble { border-top: 4px solid var(--treble) !important; }
[class*="st-key-band_"] [data-testid="stSliderThumbValue"] { display: none; }
.band-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.band-head h3 { margin: 0; padding: 0; font-size: 1.14rem; color: var(--text); font-weight: 700; }
.band-head p { margin: 2px 0 0; color: var(--muted); font-size: .82rem; line-height: 1.4; }
.band-range { white-space: nowrap; font-size: 11px; font-weight: 700; color: var(--c); background: color-mix(in srgb, var(--c) 10%, white);
  border: 1px solid color-mix(in srgb, var(--c) 35%, white); padding: 3px 8px; border-radius: 999px; }
.gain-readout { display: flex; align-items: baseline; gap: 10px; margin: 16px 0 2px; }
.gain-readout strong { font-size: 2.2rem; line-height: 1; font-weight: 760; color: var(--c); letter-spacing: -.03em; }
.gain-readout span { color: var(--muted); font-size: .82rem; }
.band-status { font-size: .78rem; color: var(--faint); border-top: 1px dashed var(--line); padding-top: 9px; }

/* ---------- Accueil ---------- */
.explain-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 8px; }
.explain { background: #ffffff; border: 1px solid var(--line); border-top: 4px solid var(--c); border-radius: 14px; padding: 15px 16px; box-shadow: var(--shadow); }
.explain h4 { margin: 0 0 2px; padding: 0; color: var(--text); font-size: 1.04rem; }
.explain .range { color: var(--c); font-size: .8rem; font-weight: 700; }
.explain p { color: var(--muted); font-size: .87rem; margin: 8px 0 0; line-height: 1.5; }
.flow { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin-top: 12px; }
.flow div { padding: 12px 14px; border-radius: 12px; background: var(--tint); border: 1px solid var(--line); color: var(--muted); font-size: .84rem; line-height: 1.45; }
.flow b { display: block; color: var(--blue-deep); font-size: .76rem; letter-spacing: .12em; margin-bottom: 3px; }
.subhead { font-size: 10.5px; letter-spacing: .16em; color: var(--faint); font-weight: 700; margin: 28px 0 4px; }

/* ---------- États verrouillés, alertes, niveaux ---------- */
.locked { display: flex; gap: 16px; padding: 18px 20px; border-radius: 16px; border: 1px dashed var(--gold-2); background: linear-gradient(120deg, var(--gold-soft), #fffdf7); }
.locked-icon { width: 42px; height: 42px; flex: none; border-radius: 12px; display: grid; place-items: center; font-size: 20px; background: #ffffff; border: 1px solid var(--gold-2); }
.locked h4 { margin: 0 0 4px; padding: 0; color: var(--text); font-size: 1.05rem; }
.locked p { margin: 0 0 8px; color: var(--muted); font-size: .9rem; line-height: 1.5; }
.locked ol { margin: 0; padding-left: 18px; color: var(--muted); font-size: .88rem; line-height: 1.65; }
.locked code { color: #8a5d00; background: #ffffff; border: 1px solid #f0dcaa; padding: 1px 6px; border-radius: 6px; font-size: .84rem; }
.placeholder { padding: 14px 16px; border-radius: 12px; border: 1px dashed var(--line); background: var(--tint); color: var(--faint); font-size: .86rem; text-align: center; }
.meter { padding: 14px 16px; border-radius: 14px; background: #ffffff; border: 1px solid var(--line); box-shadow: var(--shadow); }
.meter-top { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; color: var(--muted); font-size: .82rem; }
.meter-top strong { color: var(--text); font-size: 1.08rem; }
.meter-track { position: relative; height: 8px; border-radius: 8px; margin: 10px 0 8px; background: linear-gradient(90deg, #9db8ff 0%, #1f5bff 62%, #e8b43a 85%, #e5484d 100%); }
.meter-mark { position: absolute; top: -4px; width: 3px; height: 16px; border-radius: 2px; background: var(--text); box-shadow: 0 0 0 2px #ffffff; }
.meter-foot { font-size: .8rem; color: var(--muted); line-height: 1.45; }
.meter.warn { border-color: #f3b5b7; background: #fff8f8; }
.meter.warn .meter-foot b { color: var(--danger); }

/* ---------- Navigation entre les pages ---------- */
[class*="st-key-nav_"] { margin-top: 30px; }
.st-key-nav_next a { background: linear-gradient(140deg, #3a72ff, #1640e0) !important; border-radius: 12px; padding: 10px 18px !important;
  box-shadow: 0 10px 22px -12px rgba(31, 91, 255, .8); }
.st-key-nav_next a, .st-key-nav_next a * { color: #ffffff !important; font-weight: 650; }
.st-key-nav_prev a { border: 1px solid var(--line); border-radius: 12px; padding: 10px 16px !important; background: #ffffff; }
.footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; gap: 12px;
  flex-wrap: wrap; color: var(--faint); font-size: 10.5px; letter-spacing: .12em; }

/* ---------- Widgets Streamlit ---------- */
[data-testid="stFileUploaderDropzone"] { background: var(--blue-soft); border: 1.5px dashed #8eabff; border-radius: 14px; }
[data-testid="stExpander"] details { border-color: var(--line); border-radius: 12px; background: #ffffff; }
[data-testid="stExpander"] summary p { color: var(--muted); font-size: .9rem; }
@media (max-width: 760px) { .band-strip { grid-template-columns: 1fr; } }
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def hero() -> str:
    return (
        '<div class="hero">'
        '<div class="eyebrow"><span class="eyebrow-line"></span>EGALIZE · ÉGALISEUR AUDIO · PROJET 2</div>'
        "<h1>Façonnez votre <span>son.</span></h1>"
        "<p>Importez une piste, observez où se trouve son énergie dans le spectre, "
        "puis réglez séparément les <b>graves</b>, les <b>médiums</b> et les <b>aigus</b>.</p>"
        "</div>"
    )


def page_head(number: int, total: int, kicker: str, title: str, subtitle: str) -> str:
    bars = "".join(
        f'<i class="{"done" if index < number else "here" if index == number else ""}"></i>'
        for index in range(1, total + 1)
    )
    return (
        f'<div class="progress" title="Étape {number} sur {total}">{bars}</div>'
        f'<div class="page-head"><span class="page-num">{number:02d}</span>'
        f'<div><div class="kicker">ÉTAPE {number} SUR {total} · {escape(kicker)}</div>'
        f"<h1>{escape(title)}</h1><p>{subtitle}</p></div></div>"
    )


def context_bar(items: list[tuple[str, str]]) -> str:
    chips = "".join(f'<span class="chip">{escape(label)} <b>{escape(value)}</b></span>' for label, value in items)
    return f'<div class="context">{chips}</div>'


def subhead(text: str) -> str:
    return f'<div class="subhead">{escape(text)}</div>'


def card_title(title: str, subtitle: str = "") -> str:
    sub = f'<p class="card-sub">{subtitle}</p>' if subtitle else ""
    return f'<div class="card-title">{escape(title)}</div>{sub}'


def track_card(name: str, subtitle: str) -> str:
    return (
        '<div class="track"><div class="track-icon">♫</div>'
        f"<div><strong>{escape(name)}</strong><span>{escape(subtitle)}</span></div></div>"
    )


def stat_grid(items: list[tuple[str, str, str]]) -> str:
    cells = "".join(
        f'<div class="stat"><span>{escape(label)}</span><strong>{escape(value)}</strong>'
        f"<em>{escape(hint)}</em></div>"
        for label, value, hint in items
    )
    return f'<div class="stat-grid">{cells}</div>'


@dataclass(frozen=True)
class BandSummary:
    label: str
    color: str
    range_text: str
    share: float


def band_strip(bands: list[BandSummary]) -> str:
    cells = []
    for band in bands:
        percent = band.share * 100
        shown = f"{percent:.1f}".replace(".", ",") if percent < 10 else f"{percent:.0f}"
        cells.append(
            f'<div class="band-pill" style="--c:{band.color}">'
            f'<div class="band-pill-top"><b>{escape(band.label)}</b><span>{escape(band.range_text)}</span></div>'
            f'<div class="band-bar"><i style="width:{max(percent, 1.5):.1f}%"></i></div>'
            f'<div class="band-pill-foot"><strong>{shown} %</strong> de l\'énergie du spectre</div></div>'
        )
    return f'<div class="band-strip">{"".join(cells)}</div>'


def band_head(label: str, tagline: str, range_text: str, color: str) -> str:
    return (
        f'<div class="band-head" style="--c:{color}"><div><h3>{escape(label)}</h3>'
        f"<p>{escape(tagline)}</p></div>"
        f'<span class="band-range">{escape(range_text)}</span></div>'
    )


def gain_readout(gain_text: str, factor_text: str, color: str) -> str:
    return (
        f'<div class="gain-readout" style="--c:{color}"><strong>{escape(gain_text)}</strong>'
        f"<span>{escape(factor_text)}</span></div>"
    )


def dsp_status(connected: bool) -> str:
    if connected:
        return (
            '<div class="dsp-card ok"><span class="pulse"></span><div><b>Filtres connectés</b>'
            "<small>Séparation, gains et recombinaison sont actifs.</small></div></div>"
        )
    return (
        '<div class="dsp-card"><span class="pulse"></span><div><b>Filtres non connectés</b>'
        "<small>L'analyse fonctionne déjà. L'écoute des bandes et l'export "
        "s'activeront une fois les filtres conçus (en commençant par le passe-bas).</small></div></div>"
    )


def checklist(items: list[tuple[bool, str]]) -> str:
    rows = "".join(
        f'<li class="{"ok" if done else ""}"><i>{"✓" if done else "○"}</i><span>{escape(text)}</span></li>'
        for done, text in items
    )
    return f'<ul class="checklist">{rows}</ul>'


def side_label(text: str) -> str:
    return f'<div class="side-label">{escape(text)}</div>'


def side_note(text: str) -> str:
    return f'<div class="side-note">{escape(text)}</div>'


def explain_bands(items: list[tuple[str, str, str, str]]) -> str:
    cells = "".join(
        f'<div class="explain" style="--c:{color}"><h4>{escape(label)}</h4>'
        f'<span class="range">{escape(range_text)}</span><p>{escape(text)}</p></div>'
        for label, range_text, text, color in items
    )
    return f'<div class="explain-grid">{cells}</div>'


def flow(items: list[tuple[str, str]]) -> str:
    cells = "".join(f"<div><b>{escape(k)}</b>{escape(v)}</div>" for k, v in items)
    return f'<div class="flow">{cells}</div>'


def locked_card(title: str, body_html: str, icon: str = "🔌") -> str:
    return (
        f'<div class="locked"><div class="locked-icon">{icon}</div>'
        f"<div><h4>{escape(title)}</h4>{body_html}</div></div>"
    )


def placeholder(text: str) -> str:
    return f'<div class="placeholder">{escape(text)}</div>'


def level_meter(title: str, value_text: str, position: float, foot_html: str, warn: bool) -> str:
    """Barre de niveau : `position` entre 0 (−60 dBFS) et 1 (0 dBFS)."""
    left = min(max(position, 0.0), 1.0) * 100
    return (
        f'<div class="meter{" warn" if warn else ""}"><div class="meter-top"><span>{escape(title)}</span>'
        f"<strong>{escape(value_text)}</strong></div>"
        f'<div class="meter-track"><span class="meter-mark" style="left:calc({left:.1f}% - 1.5px)"></span></div>'
        f'<div class="meter-foot">{foot_html}</div></div>'
    )


def footer() -> str:
    return (
        '<div class="footer"><span>EGALIZE · PROJET 2 — ÉGALISEUR AUDIO NUMÉRIQUE</span>'
        "<span>LE FICHIER ORIGINAL N'EST JAMAIS MODIFIÉ</span></div>"
    )
