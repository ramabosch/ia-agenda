"""Normalización de input del usuario antes del parsing.

El texto normalizado se usa SOLO para parsing.
Nunca se guarda en DB ni se usa para construir respuestas.
"""

from __future__ import annotations

import re
import unicodedata

# Orden importa: se aplican de arriba a abajo
_ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    (r"\bq\b", "que"),
    (r"\bxq\b", "porque"),
    (r"\btmb\b", "tambien"),
    (r"\bpls\b", "por favor"),
    (r"\bporfa\b", "por favor"),
)


def normalize_input(text: str) -> str:
    """Preprocesa input del usuario para mejorar reconocimiento de intenciones.

    Pasos:
    1. Lowercase
    2. Elimina tildes / diacríticos (á→a, é→e, í→i, ó→o, ú→u, ü→u, ñ→n)
    3. Expande abreviaciones comunes
    4. Elimina puntuación innecesaria (conserva letras, dígitos, espacios, /)
    5. Colapsa espacios múltiples
    """
    # 1. lowercase
    text = text.lower()

    # 2. eliminar diacríticos via NFKD (mismo método que el parser de reglas)
    text = "".join(
        c
        for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )

    # 3. expandir abreviaciones
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)

    # 4. eliminar puntuación innecesaria (conservar / para comandos y : para horarios)
    text = re.sub(r"[^a-z0-9\s/:]", "", text)

    # 5. colapsar espacios
    text = re.sub(r"\s+", " ", text).strip()

    return text
