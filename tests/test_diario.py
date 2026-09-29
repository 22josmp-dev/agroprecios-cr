"""Proceso diario de punta a punta con un PIMA simulado y boletines reales de muestra."""
import json
from datetime import date, datetime, timezone

import pytest
from conftest import BOLETINES
from sinteticos import boletin_sintetico, filas_ejemplo

from ingesta.almacen import Almacen
from ingesta.diario import ejecutar_diario, referencia_registros, reprocesar
from ingesta.fuente import EntradaBoletin, ErrorFuente

REALES = {date(2026, 9, d): (BOLETINES / f"boletin_2026-09-{d}.pdf").read_bytes() for d in (22, 23, 24, 28)}
# 28-09-2026 a las 14:00 hora de Costa Rica
LUNES_TARDE = datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)
MARTES_TARDE = datetime(2026, 9, 29, 23, 0, tzinfo=timezone.utc)


class PIMAFalso:
    def __init__(self, pdfs: dict[date, bytes], falla_lista=False):
        self.pdfs = dict(pdfs)
        self.falla_lista = falla_lista
        self.descargas = 0

    def verificar_robots(self):
        return "robots simulado"

    def listar_boletines(self):
        if self.falla_lista:
            raise ErrorFuente("HTTP 503 simulado")
        return [EntradaBoletin(f, f"Plaza X {f:%d-%m-%Y}", f"https://pima/{f}") for f in sorted(self.pdfs, reverse=True)]

    def descargar(self, url):
        self.descargas += 1
        f = date.fromisoformat(url.rsplit("/", 1)[1])
        return self.pdfs[f], f"SIMM-Boletin de Precios PIMA-Plaza {f}.pdf"


def correr(repo, pima, ahora=LUNES_TARDE, **kw):
    return ejecutar_diario(Almacen(repo), pima, ahora=ahora, log=lambda *a: None, **kw)


def leer(repo, ruta):
    return json.loads((repo / ruta).read_text(encoding="utf-8"))


def instantanea(repo):
    return {p.relative_to(repo).as_posix(): p.read_bytes() for p in (repo / "data").rglob("*.json")
            if p.name != "meta.json"}


def test_primera_carga(repo_temporal):
    assert correr(repo_temporal, PIMAFalso(REALES)) == 0
    meta = leer(repo_temporal, "data/meta.json")
    assert meta["estado"] == "ok" and meta["fecha_boletin"] == "2026-09-28"
    assert meta["registros"] == 57 and meta["rechazados"] == 0 and meta["datos_de_ejemplo"] is False
    assert meta["ultima_actualizacion_exitosa_utc"] == "2026-09-28T20:00:00Z"
    mes = leer(repo_temporal, "data/prices/2026-09.json")
    assert sorted(mes["dias"]) == ["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-28"]
    assert len(mes["dias"]["2026-09-23"]) == 65
    latest = leer(repo_temporal, "data/latest.json")
    assert latest["fecha_boletin"] == "2026-09-28" and len(latest["productos"]) == 57
    tomate = next(p for p in latest["productos"] if p["id"] == "tomate-primera")
    assert tomate["vs_anterior"]["fecha"] == "2026-09-24"
    assert tomate["precio_kg"] == round(tomate["promedio"] / 18, 2)
    assert tomate["vs_semana"] is None  # no hay muestra del 21-09 ni anteriores dentro de la ventana
    assert tomate["vs_30d"]["dias"] == 3
    registro = leer(repo_temporal, "archivo/registro.json")
    assert [r["estado"] for r in registro] == ["procesado"] * 4
    assert all((repo_temporal / r["archivo"]).exists() for r in registro)
    assert (repo_temporal / "data/rejects/2026-09-28.json").exists()


def test_repetir_es_idempotente(repo_temporal):
    correr(repo_temporal, PIMAFalso(REALES))
    antes = instantanea(repo_temporal)
    pima = PIMAFalso(REALES)
    assert correr(repo_temporal, pima) == 0
    assert instantanea(repo_temporal) == antes
    assert pima.descargas == 2  # solo se revisan los 2 más recientes (republicaciones)
    assert "Sin boletines nuevos" in leer(repo_temporal, "data/meta.json")["mensaje"]


def test_dia_sin_boletin(repo_temporal):
    correr(repo_temporal, PIMAFalso(REALES))
    antes = instantanea(repo_temporal)
    # Martes 29: primer intento -> pendiente, sin error
    assert correr(repo_temporal, PIMAFalso(REALES), ahora=MARTES_TARDE) == 0
    assert leer(repo_temporal, "data/meta.json")["estado"] == "pendiente"
    # Último intento del día -> error, datos intactos
    assert correr(repo_temporal, PIMAFalso(REALES), ahora=MARTES_TARDE, ultimo_intento=True) == 1
    meta = leer(repo_temporal, "data/meta.json")
    assert meta["estado"] == "error" and "no está publicado" in meta["mensaje"]
    assert meta["fecha_boletin"] == "2026-09-28"
    assert meta["ultima_actualizacion_exitosa_utc"] == "2026-09-29T23:00:00Z"  # la del primer intento
    assert instantanea(repo_temporal) == antes


def test_fin_de_semana_no_es_error(repo_temporal):
    sabado = datetime(2026, 9, 26, 23, 0, tzinfo=timezone.utc)
    pdfs = {f: b for f, b in REALES.items() if f < date(2026, 9, 26)}
    assert correr(repo_temporal, PIMAFalso(pdfs), ahora=sabado, ultimo_intento=True) == 0


def test_cambio_de_formato_no_sobrescribe(repo_temporal):
    correr(repo_temporal, PIMAFalso(REALES))
    antes = instantanea(repo_temporal)
    roto = dict(REALES)
    roto[date(2026, 9, 28)] = boletin_sintetico(date(2026, 9, 28), filas_ejemplo(25), encabezado=False)
    assert correr(repo_temporal, PIMAFalso(roto)) == 1
    meta = leer(repo_temporal, "data/meta.json")
    assert meta["estado"] == "error" and "encabezado" in meta["mensaje"]
    assert meta["fecha_boletin"] == "2026-09-28" and meta["registros"] == 57
    assert instantanea(repo_temporal) == antes
    registro = leer(repo_temporal, "archivo/registro.json")
    assert [r["estado"] for r in registro].count("fallido") == 1
    # El siguiente intento vuelve a fallar (no se oculta el problema)
    assert correr(repo_temporal, PIMAFalso(roto)) == 1


def test_pocos_registros_es_falla(repo_temporal):
    correr(repo_temporal, PIMAFalso(REALES))
    lunes = date(2026, 10, 5)
    pdfs = dict(REALES)
    pdfs[lunes] = boletin_sintetico(lunes, filas_ejemplo(25))  # 25 < 80 % de 57 (lunes 28-09)
    ahora = datetime(2026, 10, 5, 20, 0, tzinfo=timezone.utc)
    assert correr(repo_temporal, PIMAFalso(pdfs), ahora=ahora) == 1
    meta = leer(repo_temporal, "data/meta.json")
    assert "Solo 25 registros" in meta["mensaje"] and "boletín del 2026-09-28" in meta["mensaje"]
    assert meta["fecha_boletin"] == "2026-09-28"


def test_republicacion_mismo_dia_reemplaza(repo_temporal):
    correr(repo_temporal, PIMAFalso(REALES))
    nuevo = dict(REALES)
    nuevo[date(2026, 9, 28)] = REALES[date(2026, 9, 28)] + b"\n%republicado\n"  # otro SHA, mismo contenido
    assert correr(repo_temporal, PIMAFalso(nuevo)) == 0
    estados = [(r["fecha"], r["estado"]) for r in leer(repo_temporal, "archivo/registro.json")]
    assert ("2026-09-28", "reemplazado") in estados and ("2026-09-28", "procesado") in estados


def test_lista_caida_conserva_datos(repo_temporal):
    correr(repo_temporal, PIMAFalso(REALES))
    antes = instantanea(repo_temporal)
    assert correr(repo_temporal, PIMAFalso(REALES, falla_lista=True)) == 1
    meta = leer(repo_temporal, "data/meta.json")
    assert meta["estado"] == "error" and "503" in meta["mensaje"]
    assert meta["ultima_actualizacion_exitosa_utc"] == "2026-09-28T20:00:00Z"
    assert instantanea(repo_temporal) == antes


def test_reprocesar_reconstruye_igual(repo_temporal):
    correr(repo_temporal, PIMAFalso(REALES))
    mes_antes = leer(repo_temporal, "data/prices/2026-09.json")
    (repo_temporal / "data/prices/2026-09.json").unlink()
    assert reprocesar(Almacen(repo_temporal), ahora=LUNES_TARDE, log=lambda *a: None) == 0
    assert leer(repo_temporal, "data/prices/2026-09.json") == mes_antes


def test_referencia_por_dia_de_semana():
    registro = [
        {"fecha": "2026-09-21", "estado": "procesado", "registros": 57},  # lunes
        {"fecha": "2026-09-23", "estado": "procesado", "registros": 65},  # miércoles
        {"fecha": "2026-09-25", "estado": "procesado", "registros": 57},  # viernes
    ]
    miercoles = referencia_registros(registro, date(2026, 9, 30))
    assert miercoles[0] == 65 and "2026-09-23" in miercoles[1] and miercoles[2] == 0.8
    martes = referencia_registros(registro, date(2026, 9, 29))  # sin martes previo: mediana, umbral holgado
    assert martes[0] == 57 and "mediana" in martes[1] and martes[2] == 0.6
    assert referencia_registros([], date(2026, 9, 29)) is None


@pytest.mark.parametrize("dia,esperado", [(date(2026, 9, 15), False), (date(2026, 4, 3), False),
                                          (date(2026, 9, 16), True), (date(2026, 9, 27), False)])
def test_feriados_y_fines_de_semana(dia, esperado):
    from ingesta.config import se_espera_boletin
    assert se_espera_boletin(dia) is esperado
