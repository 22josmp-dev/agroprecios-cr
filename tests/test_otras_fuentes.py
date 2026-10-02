"""Fruta importada (semanal) y aromáticos y gourmet (quincenal) con boletines REALES de muestra."""
import json
import shutil
from datetime import date, datetime, timezone

import pytest
from conftest import BOLETINES, MUESTRAS

from ingesta import config
from ingesta.almacen import Almacen
from ingesta.diario import ejecutar_fuente
from ingesta.fuente import EntradaBoletin
from ingesta.numeros import LATINO, US
from ingesta.parser_boletin import parsear_pdf
from ingesta.validacion import validar

OTROS = MUESTRAS / "otros"


def test_fruta_real(catalogo):
    r = parsear_pdf(OTROS / "fruta_2026-09-30.pdf")
    assert r.fecha_plaza == date(2026, 9, 30) and len(r.filas) == 24 and r.formato_numerico == US
    registros, rechazos = validar(r, catalogo, date(2026, 10, 1), fuente="fruta")
    assert rechazos == [] and len(registros) == 24
    aguacate = next(x for x in registros if x.id == "aguacate-hass-de-mexico-extra")
    assert (aguacate.unidad, aguacate.minimo, aguacate.maximo, aguacate.moda, aguacate.promedio) == \
        ("Caja (10 kg)", 14000, 15000, 14000, 14333.33)
    assert aguacate.kg == 10


def test_aromaticos_con_miles_separados_por_espacio(catalogo):
    """Caso real (09-07-2026): '2 000,00' — miles con espacio y coma decimal."""
    r = parsear_pdf(OTROS / "aromaticos_2026-07-09_miles_espacio.pdf")
    assert r.formato_numerico == LATINO and len(r.filas) == 43
    registros, rechazos = validar(r, catalogo, date(2026, 7, 10), fuente="aromaticos")
    assert rechazos == []
    ajo = next(x for x in registros if x.id == "ajo-de-china-presentacion-pelado")
    assert (ajo.unidad, ajo.minimo, ajo.maximo, ajo.moda, ajo.promedio) == ("Bolsa (1 kg)", 2000, 2500, 2000, 2200)
    albahaca = next(x for x in registros if x.id == "albahaca")
    assert albahaca.promedio == 233.33


def test_aromaticos_fila_sola_en_pagina_2(catalogo):
    """Caso real (11-06-2026): 'Zucchini baby' es la única fila de la página 2."""
    r = parsear_pdf(OTROS / "aromaticos_2026-06-11_pagina2.pdf")
    zucchini = [f for f in r.filas if f.pagina == 2]
    assert [(f.producto, f.unidad) for f in zucchini] == [("Zucchini baby", "Bandeja (500 g)")]
    _, rechazos = validar(r, catalogo, date(2026, 6, 12), fuente="aromaticos")
    assert rechazos == []


def test_total_de_oferta_no_es_fila(catalogo):
    r = parsear_pdf(OTROS / "aromaticos_2026-10-01.pdf")
    assert r.no_reconocidas == [] and len(r.filas) == 44


def test_catalogo_separado_por_fuente(catalogo):
    assert catalogo.buscar("Kiwi", "fruta")["id"] == "kiwi"
    assert catalogo.buscar("Kiwi", "diario") is None
    assert catalogo.buscar("Manzana Gala.", "fruta")["id"] == "manzana-gala"  # errata del PIMA


class PIMAFalso:
    def __init__(self, por_cm: dict[int, dict[date, bytes]]):
        self.por_cm = por_cm

    def verificar_robots(self):
        return "robots simulado"

    def listar_boletines(self, cm=4):
        return [EntradaBoletin(f, f"Plaza X {f:%d-%m-%Y}", f"https://pima/{cm}/{f}")
                for f in sorted(self.por_cm.get(cm, {}), reverse=True)]

    def descargar(self, url):
        cm, f = url.rsplit("/", 2)[1:]
        return self.por_cm[int(cm)][date.fromisoformat(f)], f"SIMM - Boletin Fruta Importada {f}.pdf"


@pytest.fixture
def repo(repo_temporal):
    return repo_temporal


def leer(repo, ruta):
    return json.loads((repo / ruta).read_text(encoding="utf-8"))


def test_proceso_semanal_de_fruta(repo):
    fruta = {date(2026, 7, 22): (OTROS / "fruta_2026-07-22.pdf").read_bytes(),
             date(2026, 9, 30): (OTROS / "fruta_2026-09-30.pdf").read_bytes()}
    diario = {date(2026, 9, 28): (BOLETINES / "boletin_2026-09-28.pdf").read_bytes()}
    pima = PIMAFalso({4: diario, 79: fruta})
    ahora = datetime(2026, 9, 30, 20, 0, tzinfo=timezone.utc)
    nada = lambda *a: None  # noqa: E731
    assert ejecutar_fuente(Almacen(repo), pima, ahora, log=nada) in (0, 1)  # el diario del 30 no existe: da igual aquí
    assert ejecutar_fuente(Almacen(repo, config.FRUTA), pima, ahora, log=nada) == 0
    meta = leer(repo, "data/meta.json")
    assert meta["fecha_boletin"] == "2026-09-28"  # el nivel superior sigue siendo el diario
    f = meta["fuentes"]["fruta"]
    assert f["estado"] == "ok" and f["fecha_boletin"] == "2026-09-30" and f["registros"] == 24
    assert f["meses_precios"] == ["2026-07", "2026-09"]
    assert (repo / "data/prices/fruta/2026-09.json").exists()
    assert (repo / "archivo/fruta/registro.json").exists()
    latest = leer(repo, "data/latest.json")
    assert latest["fuentes"]["fruta"]["frecuencia"] == "semanal" and latest["fecha_boletin"] == "2026-09-28"
    kiwi = next(p for p in latest["productos"] if p["id"] == "kiwi")
    assert kiwi["fuente"] == "fruta" and kiwi["fecha_boletin"] == "2026-09-30"
    assert kiwi["vs_anterior"]["fecha"] == "2026-07-22" and kiwi["vs_semana"] is None
    assert any(p["fuente"] == "diario" for p in latest["productos"])


def test_fruta_sin_boletin_nuevo(repo):
    fruta = {date(2026, 9, 30): (OTROS / "fruta_2026-09-30.pdf").read_bytes()}
    pima = PIMAFalso({79: fruta})
    alm = Almacen(repo, config.FRUTA)
    nada = lambda *a: None  # noqa: E731
    assert ejecutar_fuente(alm, pima, datetime(2026, 9, 30, 20, tzinfo=timezone.utc), log=nada) == 0
    # 8 días después: todavía dentro del plazo semanal (9 días)
    assert ejecutar_fuente(alm, pima, datetime(2026, 10, 8, 23, tzinfo=timezone.utc), ultimo_intento=True, log=nada) == 0
    # 12 días después sin boletín nuevo: pendiente en el primer intento y error en el último
    assert ejecutar_fuente(alm, pima, datetime(2026, 10, 12, 19, tzinfo=timezone.utc), log=nada) == 0
    assert leer(repo, "data/meta.json")["fuentes"]["fruta"]["estado"] == "pendiente"
    assert ejecutar_fuente(alm, pima, datetime(2026, 10, 12, 23, tzinfo=timezone.utc), ultimo_intento=True, log=nada) == 1
    f = leer(repo, "data/meta.json")["fuentes"]["fruta"]
    assert f["estado"] == "error" and "No hay boletín nuevo de fruta importada" in f["mensaje"]
    assert f["fecha_boletin"] == "2026-09-30"


def test_falla_de_una_fuente_no_toca_las_otras(repo):
    diario = {date(2026, 9, 28): (BOLETINES / "boletin_2026-09-28.pdf").read_bytes()}
    pima = PIMAFalso({4: diario, 79: {}})  # la lista de fruta viene vacía
    ahora = datetime(2026, 9, 28, 20, tzinfo=timezone.utc)
    nada = lambda *a: None  # noqa: E731
    assert ejecutar_fuente(Almacen(repo), pima, ahora, log=nada) == 0
    shutil.copy(repo / "data/latest.json", repo / "antes.json")
    pima.listar_boletines = lambda cm=4: (_ for _ in ()).throw(__import__("ingesta.fuente").fuente.ErrorFuente("vacía")) if cm == 79 else []
    assert ejecutar_fuente(Almacen(repo, config.FRUTA), pima, ahora, log=nada) == 1
    meta = leer(repo, "data/meta.json")
    assert meta["estado"] == "ok" and meta["fuentes"]["fruta"]["estado"] == "error"
    assert (repo / "data/latest.json").read_bytes() == (repo / "antes.json").read_bytes()
