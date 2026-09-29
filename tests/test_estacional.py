"""Índice estacional: series SINTÉTICAS (DATOS DE EJEMPLO) con patrón conocido y PDF reales del SIMM."""
import math
from statistics import mean

import pytest
from conftest import MUESTRAS

from ingesta.estacional import (confianza, indice_estacional, indice_porcentaje_promedio,
                                media_movil_centrada)
from ingesta.indices import mapear
from ingesta.indices_simm import parsear_indice

# Patrón con pico en agosto (DATOS DE EJEMPLO)
PATRON = [0.85, 0.85, 0.9, 0.95, 1.0, 1.05, 1.15, 1.35, 1.1, 0.95, 0.95, 0.9]


def serie_sintetica(anios=8, tendencia=0.02, ruido=0.0, desde=2018):
    s = {}
    for i, a in enumerate(range(desde, desde + anios)):
        for m in range(1, 13):
            t = i * 12 + m
            ondita = 1 + ruido * math.sin(t * 2.3)  # ruido determinista
            s[(a, m)] = 1000 * (1 + tendencia) ** (t / 12) * PATRON[m - 1] * ondita
    return s


def test_recupera_el_patron_con_tendencia():
    r = indice_estacional(serie_sintetica())
    assert r["suficiente"] and r["metodo"] == "media_movil_12"
    patron_norm = [p / mean(PATRON) for p in PATRON]
    assert max(abs(a - b) for a, b in zip(r["indice"], patron_norm)) < 0.01
    assert r["indice"].index(max(r["indice"])) == 7  # agosto


def test_normalizado_a_promedio_uno():
    r = indice_estacional(serie_sintetica(ruido=0.1))
    assert mean(r["indice"]) == pytest.approx(1.0, abs=1e-3)


def test_years_of_data_y_ratios():
    r = indice_estacional(serie_sintetica(anios=8))
    assert r["years_of_data"] == 8
    assert r["n_ratios"] == [7] * 12  # la media móvil pierde 6 meses en cada extremo


def test_patron_limpio_confianza_alta():
    r = indice_estacional(serie_sintetica(anios=6))
    assert r["desviacion_media"] < 0.01 and r["confianza"] == "alta"


def test_menos_de_3_anios_confianza_baja():
    r = indice_estacional(serie_sintetica(anios=2))
    assert r["confianza"] == "baja"
    assert "año" in (r["motivo"] or "")


def test_datos_insuficientes():
    r = indice_estacional({(2025, 1): 100.0, (2025, 2): 110.0})
    assert not r["suficiente"] and r["indice"] is None and r["confianza"] == "baja"


def test_fruta_de_temporada_usa_respaldo():
    s = {k: v for k, v in serie_sintetica().items() if k[1] not in (3, 4)}  # sin mercado en marzo y abril
    r = indice_estacional(s)
    assert r["metodo"] == "promedio_anual" and r["meses_sin_dato"] == [3, 4]
    assert r["indice"][2] is None and r["indice"][3] is None
    assert mean(v for v in r["indice"] if v is not None) == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize("anios,desv,esperado", [
    (8, 0.05, "alta"), (5, 0.15, "alta"), (8, 0.30, "baja"), (4, 0.05, "media"), (3, 0.5, "media"),
    (2, 0.01, "baja"), (6, None, "baja"),
])
def test_reglas_de_confianza(anios, desv, esperado):
    assert confianza(anios, desv) == esperado


def test_media_movil_centrada():
    mm = media_movil_centrada([12.0] * 13)
    assert mm[6] == pytest.approx(12.0) and mm[0] is None and mm[12] is None
    assert media_movil_centrada([1.0] * 5 + [None] + [1.0] * 7)[6] is None


@pytest.mark.parametrize("archivo,nombre,unidad,enero", [
    ("indice_camote_2026.pdf", "Camote", "Kilo", 619.05),
    ("indice_tomate_2026.pdf", "Tomate Primera", "Caja plástica (18 kg)", 11738.10),
])
def test_pdf_real_del_simm(archivo, nombre, unidad, enero):
    ind = parsear_indice(MUESTRAS / "indices" / archivo)
    assert ind.nombre == nombre and ind.edicion == 2026 and ind.unidad_precio == unidad
    assert ind.precio.anios == list(range(2018, 2026)) and len(ind.precio.valores) == 96
    assert ind.precio.valores[(2018, 1)] == enero
    assert len(ind.oferta.valores) == 96
    # Con lo leído se reproduce exactamente el índice publicado por el SIMM
    assert indice_porcentaje_promedio(ind.precio.valores) == ind.precio.indice_oficial


def test_mapeo_a_catalogo(catalogo):
    assert mapear("Tomate Primera", catalogo) == (["tomate-primera"], "tomate", "Tomate")
    assert mapear("Manga Keith", catalogo)[0] == ["manga-grande-keitt"]
    assert mapear("Manga Pequeña Irwin", catalogo) == ([], "mango", "Mango")
    assert mapear("Chile Dulce", catalogo) == ([], "chile-dulce", "Chile dulce")
    assert mapear("Aguacate Hass de Costa Rica", catalogo) == ([], "aguacate", "Aguacate")
