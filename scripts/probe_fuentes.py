"""Prueba de acceso a las fuentes del PIMA-SIMM desde cualquier entorno (local o GitHub Actions).

Solo usa la biblioteca estándar. No guarda datos en el repositorio: descarga el boletín
más reciente y un índice estacional a una carpeta temporal y reporta el resultado.
Sale con código 1 si algo falla, para que el workflow quede en rojo.

Uso:  python scripts/probe_fuentes.py [carpeta_salida]
"""
import hashlib
import html as htmlmod
import http.cookiejar
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

UA = "AgroPreciosCR-bot/0.1 (app informativa sin fines de lucro; datos publicos PIMA-SIMM)"
BASE = "https://bpm.pima.go.cr"
CM_BOLETIN = 4       # iframe de https://www.pima.go.cr/boletin/
CM_INDICES = 77      # iframe de https://www.pima.go.cr/reporte-indices-estacionales/
MIN_INTERVALO = 1.1  # segundos entre solicitudes (máx. 1 por segundo)

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_ultima = [0.0]


def solicitar(url, data=None, headers=None):
    espera = MIN_INTERVALO - (time.time() - _ultima[0])
    if espera > 0:
        time.sleep(espera)
    h = {"User-Agent": UA, **(headers or {})}
    try:
        return _opener.open(urllib.request.Request(url, data=data, headers=h), timeout=60)
    finally:
        _ultima[0] = time.time()


def listado(cm_id):
    """Devuelve [(titulo, url_accessdoc)] de una página de contenido AuraPortal.

    El portal redirige la primera visita a ScreenResolution.aspx; hay que enviar el
    tamaño de pantalla por AJAX (como hace su JavaScript) y volver a pedir la página.
    """
    url = f"{BASE}/cm.aspx?id={cm_id}"
    pagina = solicitar(url).read().decode("utf-8", "replace")
    if "AccessDoc.aspx" not in pagina:
        solicitar(
            f"{BASE}/ScreenResolution.ashx",
            json.dumps({"width": 1280, "height": 800}).encode(),
            {"Content-Type": "application/json; charset=UTF-8", "X-Requested-With": "XMLHttpRequest",
             "Referer": f"{BASE}/ScreenResolution.aspx", "Origin": BASE},
        ).read()
        pagina = solicitar(url).read().decode("utf-8", "replace")
    limpio = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", pagina, flags=re.S | re.I)
    items, previo = [], 0
    for m in re.finditer(r"<a [^>]*href=\"(https://bpm\.pima\.go\.cr/AccessDoc\.aspx\?[^\"]+)\"[^>]*>", limpio):
        texto = htmlmod.unescape(re.sub(r"<[^>]+>", " ", limpio[previo:m.start()]))
        texto = re.sub(r"\s+", " ", texto.replace("Documentos adjuntos", " ")).strip()
        items.append((texto[-160:], m.group(1).replace("&amp;", "&")))
        previo = m.end()
    return items


def descargar(url):
    r = solicitar(url)
    datos = r.read()
    cd = r.headers.get("Content-Disposition", "")
    nombre = re.search(r'filename="?([^";]+)', cd)
    return datos, (nombre.group(1) if nombre else None)


def main():
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="pima_"))
    salida.mkdir(parents=True, exist_ok=True)
    informe = []
    ok = True
    try:
        items = listado(CM_BOLETIN)
        fechas = [re.search(r"(\d{2})-(\d{2})-(\d{4})\s*$", t) for t, _ in items]
        informe.append(f"Boletines listados: {len(items)}")
        if not items:
            raise RuntimeError("La lista de boletines vino vacía (¿cambió el portal o hay bloqueo?)")
        datos, nombre = descargar(items[0][1])
        sha = hashlib.sha256(datos).hexdigest()
        es_pdf = datos[:5] == b"%PDF-"
        informe.append(f"Más reciente: {items[0][0][-40:]} -> {nombre} ({len(datos)} B, PDF={es_pdf}, sha256={sha[:16]})")
        informe.append("Fechas: " + ", ".join(f"{m.group(3)}-{m.group(2)}-{m.group(1)}" for m in fechas if m))
        ok &= es_pdf
        (salida / (nombre or "boletin.pdf")).write_bytes(datos)

        indices = listado(CM_INDICES)
        informe.append(f"Índices estacionales listados: {len(indices)}")
        tomate = next(((t, u) for t, u in indices if re.search(r"\bTomate\b.*ndice", t, re.I)), None)
        if not tomate:
            ok = False
            informe.append("ERROR: no se encontró el índice estacional del tomate en la lista")
        if tomate:
            datos, nombre = descargar(tomate[1])
            informe.append(f"Índice de ejemplo: {tomate[0][:60]} -> {len(datos)} B, PDF={datos[:5] == b'%PDF-'}")
            ok &= datos[:5] == b"%PDF-"
    except Exception as e:  # noqa: BLE001 - queremos reportar cualquier falla de red/formato
        ok = False
        informe.append(f"ERROR: {type(e).__name__}: {e}")

    texto = "\n".join(informe)
    print(texto)
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a", encoding="utf-8") as f:
            f.write(f"## Prueba de fuentes PIMA ({'OK' if ok else 'FALLA'})\n\n```\n{texto}\n```\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
