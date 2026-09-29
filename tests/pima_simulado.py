"""PIMA SIMULADO para pruebas de punta a punta (nunca toca el sitio real).

Imita el flujo verificado de bpm.pima.go.cr (docs/FORMATO_BOLETIN.md §2):
  GET  /cm.aspx?id=N          sin sesión -> 302 a /ScreenResolution.aspx + cookie ASP.NET_SessionId
  POST /ScreenResolution.ashx sin X-Requested-With -> 302 /error.aspx (como el real)
  GET  /cm.aspx?id=N          con sesión y resolución -> lista con enlaces AccessDoc.aspx?<token>
  GET  /AccessDoc.aspx?<t>    -> 302 /GetDoc.aspx?<t>
  GET  /GetDoc.aspx?<t>       -> PDF con Content-Disposition
  GET  /robots.txt            -> HTML (el real devuelve la página de login)

Los boletines se sirven desde una carpeta (AAAA-MM-DD.pdf) que la prueba modifica entre corridas.
`estado["caido"] = True` hace que todo responda 503.
"""
from __future__ import annotations

import hashlib
import threading
import uuid
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


class PIMASimulado:
    def __init__(self, carpeta_boletines: Path, carpeta_indices: Path):
        self.boletines = carpeta_boletines
        self.indices = carpeta_indices
        self.estado = {"caido": False}
        self.sesiones: dict[str, bool] = {}  # id -> resolución enviada
        self.solicitudes: list[str] = []
        self.tokens: dict[str, tuple[Path, str]] = {}
        simulado = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _sesion(self):
                for parte in (self.headers.get("Cookie") or "").split(";"):
                    k, _, v = parte.strip().partition("=")
                    if k == "ASP.NET_SessionId":
                        return v
                return None

            def _redirigir(self, destino, cookie=None):
                self.send_response(302)
                self.send_header("Location", destino)
                if cookie:
                    self.send_header("Set-Cookie", f"ASP.NET_SessionId={cookie}; path=/; HttpOnly")
                self.end_headers()

            def _enviar(self, codigo, cuerpo: bytes, tipo="text/html; charset=utf-8", extra=None):
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(cuerpo)))
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(cuerpo)

            def do_GET(self):
                simulado.solicitudes.append(f"GET {self.path}")
                if simulado.estado["caido"]:
                    return self._enviar(503, b"Servicio no disponible")
                ruta, _, consulta = self.path.partition("?")
                sesion = self._sesion()
                if ruta == "/robots.txt":
                    return self._enviar(200, b"<html>login</html>")
                if ruta == "/ScreenResolution.aspx":
                    return self._enviar(200, b"<html><script>setScreenResolution(true)</script></html>")
                if ruta == "/cm.aspx":
                    if not sesion or not simulado.sesiones.get(sesion):
                        nueva = sesion or uuid.uuid4().hex
                        simulado.sesiones.setdefault(nueva, False)
                        return self._redirigir(f"/ScreenResolution.aspx?returnURL=%2fcm.aspx%3f{consulta}",
                                               None if sesion else nueva)
                    cm = consulta.split("=")[-1]
                    return self._enviar(200, simulado.lista(cm, f"http://{self.headers['Host']}").encode())
                if ruta == "/AccessDoc.aspx":
                    return self._redirigir(f"/GetDoc.aspx?{consulta}")
                if ruta == "/GetDoc.aspx":
                    ruta_pdf, nombre = simulado.tokens.get(unquote(consulta), (None, None))
                    if not ruta_pdf or not ruta_pdf.exists():
                        return self._redirigir("/error.aspx?err=0")
                    return self._enviar(200, ruta_pdf.read_bytes(), "application/octet-stream",
                                        {"Content-Disposition": f'attachment; filename="{nombre}"'})
                return self._enviar(404, b"no encontrado")

            def do_POST(self):
                simulado.solicitudes.append(f"POST {self.path}")
                if simulado.estado["caido"]:
                    return self._enviar(503, b"Servicio no disponible")
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                sesion = self._sesion()
                if self.path.startswith("/ScreenResolution.ashx"):
                    if self.headers.get("X-Requested-With") != "XMLHttpRequest" or not sesion:
                        return self._redirigir("/error.aspx?err=0")
                    simulado.sesiones[sesion] = True
                    return self._enviar(200, b'{"isMobile":false}', "application/json; charset=utf-8")
                return self._enviar(404, b"")

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.url = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        self.hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)

    def _token(self, ruta: Path, nombre: str) -> str:
        t = hashlib.sha1(f"{ruta}{ruta.stat().st_mtime_ns}".encode()).hexdigest()
        self.tokens[t] = (ruta, nombre)
        return t

    def lista(self, cm: str, base: str) -> str:
        items = []
        if cm == "4":
            for pdf in sorted(self.boletines.glob("*.pdf"), reverse=True):
                f = date.fromisoformat(pdf.stem)
                titulo = (f"Boletín Diario de Precios sugeridos de Frutas y Hortalizas PIMA-CENADA. "
                          f"Plaza {DIAS[f.weekday()]} {f:%d-%m-%Y}")
                items.append((titulo, self._token(pdf, f"SIMM-Boletin de Precios PIMA-Plaza {f}.pdf")))
        elif cm == "77":
            for pdf in sorted(self.indices.glob("*.pdf")):
                nombre = pdf.stem.replace("indice_", "").split("_")[0].capitalize()
                items.append((f"{nombre} índice estacional de oferta y precio para el año 2026",
                              self._token(pdf, f"{nombre} indice 2026.pdf")))
        cuerpo = "".join(
            f'<tr><td><div><span style="font-size:8pt">{t}</span></div></td></tr>'
            f"<tr><td><a class='ApEst_0140' href=\"{base}/AccessDoc.aspx?{k}\" target=\"AP_Docs\">Documentos adjuntos</a></td></tr>"
            for t, k in items)
        return f"<html><body><table>{cuerpo}</table></body></html>"

    def __enter__(self):
        self.hilo.start()
        return self

    def __exit__(self, *a):
        self.servidor.shutdown()
