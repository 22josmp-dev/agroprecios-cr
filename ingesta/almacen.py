"""Lectura y escritura de /data (publicado) y /archivo (PDF originales, no publicado).

Todas las escrituras son atómicas (archivo temporal + os.replace): un proceso interrumpido
nunca deja un JSON a medias.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

FUENTE = "PIMA – SIMM"
COLUMNAS_PRECIOS = ["id", "unidad", "minimo", "maximo", "moda", "promedio"]


def ahora_iso(momento: datetime | None = None) -> str:
    momento = momento or datetime.now(timezone.utc)
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def escribir_atomico(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=f".{ruta.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        os.replace(tmp, ruta)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def escribir_json(ruta: Path, obj) -> None:
    escribir_atomico(ruta, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def leer_json(ruta: Path, defecto=None):
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


class Almacen:
    """Rutas de una fuente (boletín). El diario usa las rutas originales: data/prices, data/rejects,
    archivo/; las otras fuentes, subcarpetas (data/prices/fruta, archivo/fruta, …)."""

    def __init__(self, raiz: Path, fuente=None):
        from .config import DIARIO
        self.raiz = Path(raiz)
        self.fuente = fuente or DIARIO
        self.data = self.raiz / "data"
        self.archivo = self.raiz / "archivo"
        self.dir_precios = self.data / self.fuente.dir_precios
        self.dir_rechazos = self.data / self.fuente.dir_rechazos
        self.archivo_fuente = self.raiz / self.fuente.dir_archivo

    def de(self, fuente) -> "Almacen":
        return Almacen(self.raiz, fuente)

    # --- precios mensuales -------------------------------------------------
    def ruta_mes(self, anio: int, mes: int) -> Path:
        return self.dir_precios / f"{anio:04d}-{mes:02d}.json"

    def leer_mes(self, anio: int, mes: int) -> dict:
        return leer_json(self.ruta_mes(anio, mes)) or {
            "esquema": 1, "mes": f"{anio:04d}-{mes:02d}", "fuente": FUENTE, "datos_de_ejemplo": False,
            "columnas": COLUMNAS_PRECIOS, "dias": {},
        }

    def escribir_mes(self, contenido: dict) -> None:
        """Un día por línea: archivo compacto y diferencias de git legibles."""
        anio, mes = map(int, contenido["mes"].split("-"))
        cabecera = {k: v for k, v in contenido.items() if k != "dias"}
        lineas = [json.dumps(f, ensure_ascii=False, separators=(",", ":")) + ":" +
                  json.dumps(contenido["dias"][f], ensure_ascii=False, separators=(",", ":"))
                  for f in sorted(contenido["dias"])]
        cuerpo = json.dumps(cabecera, ensure_ascii=False, separators=(",", ":"))[:-1]
        texto = cuerpo + ',"dias":{\n' + ",\n".join(lineas) + "\n}}\n"
        json.loads(texto)  # verificación de que el JSON quedó bien formado
        escribir_atomico(self.ruta_mes(anio, mes), texto)

    def guardar_dia(self, fecha: date, filas: list[list]) -> None:
        contenido = self.leer_mes(fecha.year, fecha.month)
        contenido["dias"][fecha.isoformat()] = filas
        self.escribir_mes(contenido)

    def cargar_dias(self, desde: date, hasta: date) -> dict[date, list[list]]:
        dias: dict[date, list[list]] = {}
        anio, mes = desde.year, desde.month
        while (anio, mes) <= (hasta.year, hasta.month):
            for f, filas in self.leer_mes(anio, mes)["dias"].items():
                d = date.fromisoformat(f)
                if desde <= d <= hasta:
                    dias[d] = filas
            anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
        return dias

    def fechas_con_datos(self) -> list[date]:
        fechas = []
        for ruta in sorted(self.dir_precios.glob("*.json")):
            fechas += [date.fromisoformat(f) for f in (leer_json(ruta) or {}).get("dias", {})]
        return sorted(fechas)

    # --- rechazos ------------------------------------------------------------
    def guardar_rechazos(self, fecha: date, sha256: str, rechazos: list[dict], momento: str) -> None:
        escribir_json(self.dir_rechazos / f"{fecha.isoformat()}.json", {
            "esquema": 1, "fecha_boletin": fecha.isoformat(), "sha256": sha256, "generado_utc": momento,
            "total": len(rechazos), "rechazados": rechazos,
        })

    # --- archivo de PDF originales --------------------------------------------
    def guardar_pdf(self, fecha: date, sha256: str, datos: bytes) -> str:
        ruta = self.archivo_fuente / "boletines" / f"{fecha.year:04d}" / f"{fecha.isoformat()}_{sha256[:12]}.pdf"
        if not ruta.exists():
            ruta.parent.mkdir(parents=True, exist_ok=True)
            tmp = ruta.with_suffix(".tmp")
            tmp.write_bytes(datos)
            os.replace(tmp, ruta)
        return ruta.relative_to(self.raiz).as_posix()

    def registro(self) -> list[dict]:
        return leer_json(self.archivo_fuente / "registro.json", [])

    def guardar_registro(self, entradas: list[dict]) -> None:
        escribir_json(self.archivo_fuente / "registro.json", sorted(entradas, key=lambda e: (e["fecha"], e["descargado_utc"])))

    # --- meta / latest ----------------------------------------------------------
    def meta(self) -> dict:
        return leer_json(self.data / "meta.json", {}) or {}

    def guardar_meta(self, meta: dict) -> None:
        escribir_json(self.data / "meta.json", meta)

    def guardar_latest(self, latest: dict) -> None:
        escribir_json(self.data / "latest.json", latest)
