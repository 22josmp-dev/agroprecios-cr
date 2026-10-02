"""Cliente del portal AuraPortal del PIMA (bpm.pima.go.cr). Solo biblioteca estándar.

Flujo verificado (docs/FORMATO_BOLETIN.md §2): cm.aspx -> ScreenResolution -> POST
ScreenResolution.ashx (con X-Requested-With) -> cm.aspx con cookie -> enlaces AccessDoc.aspx.
"""
from __future__ import annotations

import html
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import date

from . import config


class ErrorFuente(Exception):
    """No se pudo obtener la lista o el archivo desde el PIMA."""


@dataclass(frozen=True)
class EntradaBoletin:
    fecha: date
    titulo: str
    url: str


_RE_ENLACE = re.compile(r'<a [^>]*href="(https?://[^"/]+/AccessDoc\.aspx\?[^"]+)"[^>]*>', re.I)
_RE_FECHA_TITULO = re.compile(r"Plaza\s+\S+\s+(\d{1,2})-(\d{1,2})-(\d{4})\s*$")
_RE_FECHA_ARCHIVO = re.compile(r"(\d{4})-(\d{2})-(\d{2})\.pdf$", re.I)


def extraer_enlaces(pagina: str) -> list[tuple[str, str]]:
    """[(texto que precede al enlace, url)] para cada 'Documentos adjuntos' de la página."""
    limpio = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", pagina, flags=re.S | re.I)
    items, previo = [], 0
    for m in _RE_ENLACE.finditer(limpio):
        texto = html.unescape(re.sub(r"<[^>]+>", " ", limpio[previo:m.start()]))
        texto = re.sub(r"\s+", " ", texto.replace("Documentos adjuntos", " ")).strip()
        items.append((texto[-200:], html.unescape(m.group(1))))
        previo = m.end()
    return items


def parsear_listado(pagina: str) -> list[EntradaBoletin]:
    """Entradas del boletín diario, de la más reciente a la más antigua."""
    salida = []
    for titulo, url in extraer_enlaces(pagina):
        m = _RE_FECHA_TITULO.search(titulo)
        if not m:
            continue
        try:
            fecha = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        salida.append(EntradaBoletin(fecha, titulo, url))
    return salida


def fecha_de_nombre_archivo(nombre: str | None) -> date | None:
    m = _RE_FECHA_ARCHIVO.search(nombre or "")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


class ClientePIMA:
    def __init__(self, dormir=time.sleep, reloj=time.monotonic, abridor=None):
        self._dormir = dormir
        self._reloj = reloj
        self._abridor = abridor or urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self._ultima: float | None = None
        self.solicitudes = 0

    def _esperar_turno(self) -> None:
        if self._ultima is not None:
            falta = config.INTERVALO_MIN_S - (self._reloj() - self._ultima)
            if falta > 0:
                self._dormir(falta)

    def _abrir(self, url: str, data: bytes | None = None, headers: dict | None = None):
        ultimo_error: Exception | None = None
        for intento in range(config.REINTENTOS + 1):
            self._esperar_turno()
            try:
                self.solicitudes += 1
                peticion = urllib.request.Request(url, data=data, headers={"User-Agent": config.USER_AGENT, **(headers or {})})
                with self._abridor.open(peticion, timeout=config.TIMEOUT_S) as r:
                    return r.headers, r.read()
            except urllib.error.HTTPError as e:
                if e.code < 500 and e.code != 429:
                    raise ErrorFuente(f"HTTP {e.code} al pedir {url}") from e
                ultimo_error = e
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                ultimo_error = e
            finally:
                self._ultima = self._reloj()
            if intento < config.REINTENTOS:
                self._dormir(config.ESPERA_BASE_S * 3 ** intento)
        raise ErrorFuente(f"Sin respuesta válida de {url} tras {config.REINTENTOS + 1} intentos: {ultimo_error}")

    def verificar_robots(self) -> str:
        """Respeta robots.txt si el servidor publica uno de verdad (hoy devuelve HTML de login)."""
        headers, cuerpo = self._abrir(f"{config.BASE_URL}/robots.txt")
        if "text/plain" not in (headers.get("Content-Type") or ""):
            return "bpm.pima.go.cr no publica robots.txt (responde HTML); se aplican límites prudentes"
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(cuerpo.decode("utf-8", "replace").splitlines())
        for ruta in (f"/cm.aspx?id={config.CM_BOLETIN}", "/AccessDoc.aspx", "/GetDoc.aspx"):
            if not rp.can_fetch(config.USER_AGENT, config.BASE_URL + ruta):
                raise ErrorFuente(f"robots.txt de bpm.pima.go.cr prohíbe {ruta}; no se descarga")
        return "robots.txt permite el acceso"

    def pagina_contenido(self, cm_id: int) -> str:
        url = f"{config.BASE_URL}/cm.aspx?id={cm_id}"
        _, cuerpo = self._abrir(url)
        pagina = cuerpo.decode("utf-8", "replace")
        if "AccessDoc.aspx" not in pagina:
            self._abrir(
                f"{config.BASE_URL}/ScreenResolution.ashx",
                json.dumps({"width": 1280, "height": 800}).encode(),
                {"Content-Type": "application/json; charset=UTF-8", "X-Requested-With": "XMLHttpRequest",
                 "Referer": f"{config.BASE_URL}/ScreenResolution.aspx", "Origin": config.BASE_URL},
            )
            _, cuerpo = self._abrir(url)
            pagina = cuerpo.decode("utf-8", "replace")
        return pagina

    def listar_boletines(self, cm: int = config.CM_BOLETIN) -> list[EntradaBoletin]:
        entradas = parsear_listado(self.pagina_contenido(cm))
        if not entradas:
            raise ErrorFuente("La lista de boletines del PIMA vino vacía (¿cambió el portal?)")
        return entradas

    def descargar(self, url: str) -> tuple[bytes, str | None]:
        headers, datos = self._abrir(url)
        if datos[:5] != b"%PDF-":
            raise ErrorFuente(f"El archivo descargado no es un PDF (empieza con {datos[:15]!r})")
        m = re.search(r'filename="?([^";]+)', headers.get("Content-Disposition") or "")
        return datos, (m.group(1) if m else None)
