"""Pruebas de PUNTA A PUNTA: el comando real `python -m ingesta diario` contra el PIMA SIMULADO
(tests/pima_simulado.py), en una copia temporal del repositorio que empieza sin datos.

Boletines: los PDF REALES archivados en archivo/boletines/2026 (14 al 28 de setiembre de 2026).
Los cambios de formato usan PDF SINTÉTICOS (DATOS DE EJEMPLO) que nunca se publican.

Secuencia (cada prueba depende de la anterior; se ejecutan en orden):
  1. Instalación nueva: carga de 10 boletines (14–25 set).
  2. Día nuevo: aparece el boletín del lunes 28.
  3. Segundo intento del mismo día: sin cambios.
  4. Día sin boletín (martes 29): pendiente a la 1 p. m., error en el último intento.
  5. Cambio de formato que rompe el parser: error y datos intactos.
  6. Cambio de formato tolerable (otro orden de columnas y 1.000,00): se procesa bien.
  7. Sitio del PIMA caído: error tras reintentos y datos intactos.
  8. El sitio vuelve: todo en orden.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from conftest import RAIZ
from pima_simulado import PIMASimulado
from sinteticos import boletin_sintetico

from ingesta.parser_boletin import parsear_pdf

ARCHIVO_REAL = RAIZ / "archivo" / "boletines" / "2026"


def pdf_real(fecha: str) -> Path:
    return next(ARCHIVO_REAL.glob(f"{fecha}_*.pdf"))


class Escenario:
    def __init__(self, raiz: Path, pima: PIMASimulado):
        self.raiz = raiz
        self.pima = pima
        self.salida = ""

    def publicar(self, fecha: str, origen: Path | bytes):
        destino = self.pima.boletines / f"{fecha}.pdf"
        if isinstance(origen, bytes):
            destino.write_bytes(origen)
        else:
            shutil.copy(origen, destino)

    def correr(self, ahora: str, ultimo=False) -> int:
        env = {**os.environ, "PIMA_BASE_URL": self.pima.url, "PIMA_INTERVALO_MIN_S": "0.01",
               "PIMA_ESPERA_BASE_S": "0.01", "PYTHONIOENCODING": "utf-8"}
        cmd = [sys.executable, "-m", "ingesta", "diario", "--fuente", "diario", "--ahora", ahora] + (["--ultimo-intento"] if ultimo else [])
        r = subprocess.run(cmd, cwd=self.raiz, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300)
        self.salida = r.stdout + r.stderr
        return r.returncode

    def json(self, ruta: str):
        return json.loads((self.raiz / ruta).read_text(encoding="utf-8"))

    def huella_datos(self) -> str:
        """Huella de todos los datos publicados menos meta.json (que registra cada intento)."""
        h = hashlib.sha256()
        for p in sorted((self.raiz / "data").rglob("*.json")):
            if p.name != "meta.json":
                h.update(p.relative_to(self.raiz).as_posix().encode() + p.read_bytes())
        return h.hexdigest()


@pytest.fixture(scope="module")
def esc(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("repo")
    shutil.copytree(RAIZ / "ingesta", raiz / "ingesta", ignore=shutil.ignore_patterns("__pycache__"))
    (raiz / "data").mkdir()
    shutil.copy(RAIZ / "data" / "catalog.json", raiz / "data" / "catalog.json")
    boletines = tmp_path_factory.mktemp("pima_boletines")
    indices = tmp_path_factory.mktemp("pima_indices")
    with PIMASimulado(boletines, indices) as pima:
        yield Escenario(raiz, pima)


def test_1_instalacion_nueva(esc):
    for d in (14, 15, 16, 17, 18, 21, 22, 23, 24, 25):
        esc.publicar(f"2026-09-{d}", pdf_real(f"2026-09-{d}"))
    assert esc.correr("2026-09-25T19:17:00Z") == 0, esc.salida
    meta = esc.json("data/meta.json")
    assert meta["estado"] == "ok" and meta["fecha_boletin"] == "2026-09-25"
    assert meta["dias_con_datos"] == 10 and meta["registros"] == 57 and meta["rechazados"] == 0
    # Flujo del portal respetado: resolución enviada por POST con la cabecera exigida
    assert any(s.startswith("POST /ScreenResolution.ashx") for s in esc.pima.solicitudes)
    assert len(esc.json("archivo/registro.json")) == 10


def test_2_dia_nuevo(esc):
    esc.pima.solicitudes.clear()
    esc.publicar("2026-09-28", pdf_real("2026-09-28"))
    assert esc.correr("2026-09-28T19:17:00Z") == 0, esc.salida
    meta = esc.json("data/meta.json")
    assert meta["fecha_boletin"] == "2026-09-28" and meta["dias_con_datos"] == 11
    assert "Boletines nuevos: 2026-09-28" in meta["mensaje"]
    latest = esc.json("data/latest.json")
    tomate = next(p for p in latest["productos"] if p["id"] == "tomate-primera")
    assert tomate["promedio"] == 10000.0 and tomate["vs_anterior"]["fecha"] == "2026-09-25"
    assert tomate["vs_semana"]["fecha"] == "2026-09-21"
    # Solo se descargan el nuevo y el más reciente anterior (revisión de republicación)
    assert sum(1 for s in esc.pima.solicitudes if s.startswith("GET /GetDoc.aspx")) == 2


def test_3_segundo_intento_sin_cambios(esc):
    antes = esc.huella_datos()
    assert esc.correr("2026-09-28T23:17:00Z", ultimo=True) == 0, esc.salida
    assert esc.huella_datos() == antes
    assert "Sin boletines nuevos" in esc.json("data/meta.json")["mensaje"]


def test_4_dia_sin_boletin(esc):
    antes = esc.huella_datos()
    assert esc.correr("2026-09-29T19:17:00Z") == 0, esc.salida
    meta = esc.json("data/meta.json")
    assert meta["estado"] == "pendiente"
    exito_primer_intento = meta["ultima_actualizacion_exitosa_utc"]
    assert esc.correr("2026-09-29T23:17:00Z", ultimo=True) == 1, esc.salida
    meta = esc.json("data/meta.json")
    assert meta["estado"] == "error" and "no está publicado" in meta["mensaje"]
    assert meta["fecha_boletin"] == "2026-09-28" and meta["registros"] == 57
    assert meta["ultima_actualizacion_exitosa_utc"] == exito_primer_intento
    assert esc.huella_datos() == antes


def test_5_cambio_de_formato_que_rompe(esc):
    antes = esc.huella_datos()
    filas = [(f.producto, f.unidad, {k: float(v.replace(",", "")) for k, v in f.valores.items()})
             for f in parsear_pdf(pdf_real("2026-09-22")).filas]
    esc.publicar("2026-09-29", boletin_sintetico(date(2026, 9, 29), filas, encabezado=False))
    assert esc.correr("2026-09-29T23:30:00Z", ultimo=True) == 1, esc.salida
    meta = esc.json("data/meta.json")
    assert meta["estado"] == "error" and "encabezado" in meta["mensaje"]
    assert meta["fecha_boletin"] == "2026-09-28"
    assert esc.huella_datos() == antes
    fallidos = [r for r in esc.json("archivo/registro.json") if r["estado"] == "fallido"]
    assert len(fallidos) == 1 and (esc.raiz / fallidos[0]["archivo"]).exists()  # PDF guardado para reprocesar


def test_6_cambio_de_formato_tolerable(esc):
    """Otro orden de columnas (el supuesto al inicio) y formato 1.000,00: se lee bien."""
    filas = [(f.producto, f.unidad, {k: float(v.replace(",", "")) for k, v in f.valores.items()})
             for f in parsear_pdf(pdf_real("2026-09-22")).filas]
    esc.publicar("2026-09-29", boletin_sintetico(date(2026, 9, 29), filas,
                                                  orden=("Promedio", "Moda", "Máximo", "Mínimo"), formato="LATINO"))
    assert esc.correr("2026-09-30T00:10:00Z") == 0, esc.salida
    meta = esc.json("data/meta.json")
    assert meta["estado"] == "ok" and meta["fecha_boletin"] == "2026-09-29" and meta["registros"] == 51
    reg22 = {f[0]: f for f in esc.json("data/prices/2026-09.json")["dias"]["2026-09-22"]}
    reg29 = {f[0]: f for f in esc.json("data/prices/2026-09.json")["dias"]["2026-09-29"]}
    assert reg29["tomate-primera"][2:] == reg22["tomate-primera"][2:]  # mismos mínimo, máximo, moda y promedio


def test_7_sitio_caido(esc):
    antes = esc.huella_datos()
    esc.pima.estado["caido"] = True
    assert esc.correr("2026-09-30T19:17:00Z") == 1, esc.salida
    meta = esc.json("data/meta.json")
    assert meta["estado"] == "error" and "503" in meta["mensaje"]
    assert meta["fecha_boletin"] == "2026-09-29"
    assert esc.huella_datos() == antes


def test_8_el_sitio_vuelve(esc):
    esc.pima.estado["caido"] = False
    esc.publicar("2026-09-30", pdf_real("2026-09-23"))  # un miércoles real con otra fecha: debe rechazarse
    assert esc.correr("2026-09-30T23:17:00Z", ultimo=True) == 1, esc.salida
    assert "no coincide" in esc.json("data/meta.json")["mensaje"]  # fecha del PDF ≠ fecha de la lista
    assert esc.json("data/meta.json")["fecha_boletin"] == "2026-09-29"  # el PDF equivocado no entró
    # El PIMA retira el archivo equivocado: el 30 queda sin boletín todavía -> pendiente, sin error
    (esc.pima.boletines / "2026-09-30.pdf").unlink()
    assert esc.correr("2026-10-01T00:30:00Z") == 0, esc.salida
    assert esc.json("data/meta.json")["estado"] == "pendiente"
    # Jueves 1 de octubre sin boletín del 30 ni del 1: el último intento del día falla y avisa
    assert esc.correr("2026-10-01T23:17:00Z", ultimo=True) == 1


def test_9_mismo_pdf_en_otra_fecha_no_pasa_en_silencio(esc):
    """Error real encontrado por estas pruebas: antes, un boletín viejo re-subido con otra fecha se
    daba por 'sin cambios' porque la idempotencia miraba solo el SHA-256."""
    registro = esc.json("archivo/registro.json")
    fallido = [r for r in registro if r["fecha"] == "2026-09-30" and r["estado"] == "fallido"]
    assert fallido and "no coincide" in fallido[0]["error"]
    original = [r for r in registro if r["fecha"] == "2026-09-23" and r["estado"] == "procesado"]
    assert original and original[0]["sha256"] == fallido[0]["sha256"]  # el registro del 23 sigue intacto
