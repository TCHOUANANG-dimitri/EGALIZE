"""Mise en forme des nombres et des textes à la française."""

from __future__ import annotations


def fr_number(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def fr_int(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def fr_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{fr_number(seconds)} s"
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes} min {rest:02d} s"


def describe_dtype(dtype: str) -> tuple[str, str]:
    descriptions = {
        "uint8": ("8 bits", "entiers non signés (uint8)"),
        "int16": ("16 bits", "entiers signés (int16)"),
        "int32": ("32 bits", "entiers signés (int32)"),
        "float32": ("32 bits", "virgule flottante (float32)"),
        "float64": ("64 bits", "virgule flottante (float64)"),
    }
    return descriptions.get(dtype, (dtype, "format des échantillons"))


def explain_wav_warning(message: str) -> str:
    if "EOF prematurely" in message:
        return (
            "Le fichier se termine un peu avant la taille annoncée dans son en-tête "
            "(fichier légèrement tronqué). Les échantillons lisibles sont utilisés normalement."
        )
    return message
