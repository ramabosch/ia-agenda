import re


STOPWORDS = {
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "de",
    "del",
    "al",
    "que",
    "tarea",
    "proyecto",
    "cliente",
}


def normalize_entity_text(text: str) -> str:
    text = text.strip().lower()

    # reemplazar puntuación por espacios
    text = re.sub(r"[^a-záéíóúüñ0-9\s]", " ", text)

    # colapsar espacios
    text = re.sub(r"\s+", " ", text).strip()

    words = [word for word in text.split() if word not in STOPWORDS]

    return " ".join(words)