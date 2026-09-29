import io
import urllib.error
from datetime import date
from email.message import Message

import pytest
from conftest import MUESTRAS

from ingesta import config
from ingesta.fuente import ClientePIMA, ErrorFuente, fecha_de_nombre_archivo, parsear_listado


def test_listado_real():
    """Página real de la lista guardada el 28-09-2026."""
    entradas = parsear_listado((MUESTRAS / "listado_cm4.html").read_text(encoding="utf-8"))
    assert len(entradas) == 11
    assert entradas[0].fecha == date(2026, 9, 28)
    assert date(2026, 9, 23) in {e.fecha for e in entradas}  # "Miércoles" con tilde
    assert all(e.url.startswith("https://bpm.pima.go.cr/AccessDoc.aspx?") for e in entradas)
    assert all("&amp;" not in e.url for e in entradas)


def test_fecha_de_nombre_archivo():
    assert fecha_de_nombre_archivo("SIMM-Boletin de Precios PIMA-Plaza 2026-09-28.pdf") == date(2026, 9, 28)
    assert fecha_de_nombre_archivo(None) is None


class Respuesta(io.BytesIO):
    def __init__(self, cuerpo, headers=None):
        super().__init__(cuerpo)
        self.headers = Message()
        for k, val in (headers or {}).items():
            self.headers[k] = val


class AbridorFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.peticiones = []

    def open(self, peticion, timeout=None):
        self.peticiones.append(peticion)
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def cliente(respuestas):
    esperas = []
    reloj = iter(range(0, 10_000, 100))  # cada llamada avanza 100 s: nunca hay que esperar turno
    c = ClientePIMA(dormir=esperas.append, reloj=lambda: next(reloj), abridor=AbridorFalso(respuestas))
    return c, esperas


def error_http(codigo):
    return urllib.error.HTTPError("https://x", codigo, "err", Message(), None)


def test_reintentos_con_espera_creciente():
    c, esperas = cliente([error_http(503), urllib.error.URLError("timeout"), Respuesta(b"%PDF-1.7 ok")])
    datos, _ = c.descargar("https://bpm.pima.go.cr/AccessDoc.aspx?x")
    assert datos.startswith(b"%PDF")
    assert esperas == [config.ESPERA_BASE_S, config.ESPERA_BASE_S * 3]


def test_error_404_no_se_reintenta():
    c, esperas = cliente([error_http(404)])
    with pytest.raises(ErrorFuente, match="404"):
        c.descargar("https://x")
    assert esperas == []


def test_se_agotan_los_reintentos():
    c, _ = cliente([error_http(500)] * (config.REINTENTOS + 1))
    with pytest.raises(ErrorFuente, match="intentos"):
        c.descargar("https://x")


def test_no_es_pdf():
    c, _ = cliente([Respuesta(b"<html>login</html>")])
    with pytest.raises(ErrorFuente, match="no es un PDF"):
        c.descargar("https://x")


def test_limite_de_una_solicitud_por_segundo():
    esperas = []
    tiempos = iter([0.0, 0.2, 0.2, 0.3])
    c = ClientePIMA(dormir=esperas.append, reloj=lambda: next(tiempos),
                    abridor=AbridorFalso([Respuesta(b"%PDF-a"), Respuesta(b"%PDF-b")]))
    c.descargar("https://x")
    c.descargar("https://y")
    assert esperas and esperas[0] == pytest.approx(config.INTERVALO_MIN_S - 0.2)


def test_user_agent_identificable():
    c, _ = cliente([Respuesta(b"%PDF-a")])
    c.descargar("https://x")
    assert "AgroPreciosCR-bot" in c._abridor.peticiones[0].get_header("User-agent")


def test_robots_html_no_bloquea():
    c, _ = cliente([Respuesta(b"<html></html>", {"Content-Type": "text/html"})])
    assert "no publica robots.txt" in c.verificar_robots()


def test_robots_que_prohibe():
    c, _ = cliente([Respuesta(b"User-agent: *\nDisallow: /AccessDoc.aspx\n", {"Content-Type": "text/plain"})])
    with pytest.raises(ErrorFuente, match="robots.txt"):
        c.verificar_robots()


def test_flujo_screen_resolution():
    lista = (MUESTRAS / "listado_cm4.html").read_bytes()
    c, _ = cliente([Respuesta(b"<html>ScreenResolution</html>"), Respuesta(b'{"isMobile":false}'), Respuesta(lista)])
    entradas = c.listar_boletines()
    assert len(entradas) == 11
    post = c._abridor.peticiones[1]
    assert post.get_method() == "POST" and post.get_header("X-requested-with") == "XMLHttpRequest"
