"""Normalización de texto para comparar nombres de productos y unidades."""
import re
import unicodedata


def sin_tildes(texto: str) -> str:
    """Quita tildes y diéresis (también convierte ñ en n) para comparar con tolerancia."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """'  Piña - Grande ' -> 'pina grande'."""
    t = sin_tildes(texto or "").lower()
    t = re.sub(r"[^a-z0-9()]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def slug(texto: str) -> str:
    """'Fresa (1 Kg)' -> 'fresa-1-kg'."""
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes(texto).lower()).strip("-")


def limpiar_celda(celda: str | None) -> str:
    return re.sub(r"\s+", " ", (celda or "").replace("\n", " ")).strip()
