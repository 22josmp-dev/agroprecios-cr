"""Construye data/latest.json: el último boletín de cada fuente con sus comparaciones ya
calculadas, para que la app no tenga que descargar el historial solo para mostrar las flechas."""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from . import config
from .almacen import FUENTE, Almacen
from .catalogo import Catalogo, kg_equivalente


def _variacion(actual: float, referencia: float | None) -> float | None:
    if not referencia:
        return None
    return round((actual - referencia) / referencia * 100, 1)


def productos_de_fuente(alm: Almacen, catalogo: Catalogo, fecha: date) -> list[dict]:
    fuente = alm.fuente
    ventana = fuente.ventana_promedio_dias
    # El "boletín anterior" se busca hasta 120 días atrás en las fuentes semanal/quincenal (puede
    # faltar alguna semana); en el diario bastan 45 días.
    atras = 45 if fuente.frecuencia == "diaria" else 120
    dias = alm.cargar_dias(fecha - timedelta(days=max(atras, ventana + 10)), fecha)
    if fecha not in dias:
        raise ValueError(f"No hay datos guardados de {fuente.id} para {fecha}")
    indice = {d: {(f[0], f[1]): f for f in filas} for d, filas in dias.items()}
    previas = sorted((d for d in dias if d < fecha), reverse=True)
    productos = []
    for id_, unidad, minimo, maximo, moda, promedio in dias[fecha]:
        info = catalogo.por_id(id_) or {}
        clave = (id_, unidad)
        # Solo se compara con la misma unidad de comercialización
        anterior = next((d for d in previas if clave in indice[d]), None)
        semana = next((d for d in previas if fecha - timedelta(days=13) <= d <= fecha - timedelta(days=7)
                       and clave in indice[d]), None) if fuente.frecuencia == "diaria" else None
        ventana_vals = [indice[d][clave][5] for d in previas if d >= fecha - timedelta(days=ventana) and clave in indice[d]]
        kg = kg_equivalente(unidad, info.get("nombre", ""))

        def ref(d):
            if d is None:
                return None
            p = indice[d][clave][5]
            return {"fecha": d.isoformat(), "promedio": p, "variacion_pct": _variacion(promedio, p)}

        prom = round(mean(ventana_vals), 2) if len(ventana_vals) >= 3 else None
        productos.append({
            "id": id_, "nombre": info.get("nombre", id_), "cultivo": info.get("cultivo"),
            "cultivo_id": info.get("cultivo_id"), "categoria": info.get("categoria"),
            "fuente": fuente.id, "fecha_boletin": fecha.isoformat(),
            "unidad": unidad, "kg": kg,
            "minimo": minimo, "maximo": maximo, "moda": moda, "promedio": promedio,
            "precio_kg": round(promedio / kg, 2) if kg else None,
            "vs_anterior": ref(anterior),
            "vs_semana": ref(semana),
            "vs_promedio": {"boletines": len(ventana_vals), "promedio": prom, "variacion_pct": _variacion(promedio, prom)} if prom else None,
        })
    return productos


def construir_latest(alm: Almacen, catalogo: Catalogo, generado_utc: str) -> dict | None:
    """Une el último boletín de todas las fuentes. None si todavía no hay datos de ninguna."""
    fuentes, productos = {}, []
    for fuente in config.FUENTES.values():
        a = alm.de(fuente)
        fechas = a.fechas_con_datos()
        if not fechas:
            continue
        fuentes[fuente.id] = {
            "nombre": fuente.nombre, "frecuencia": fuente.frecuencia, "fecha_boletin": fechas[-1].isoformat(),
            "ventana_promedio_dias": fuente.ventana_promedio_dias, "texto_promedio": fuente.texto_promedio,
        }
        productos += productos_de_fuente(a, catalogo, fechas[-1])
    if not productos:
        return None
    productos.sort(key=lambda p: p["nombre"])
    return {
        "esquema": 2, "fuente": FUENTE, "datos_de_ejemplo": False,
        "fecha_boletin": fuentes.get("diario", {}).get("fecha_boletin"), "generado_utc": generado_utc,
        "fuentes": fuentes,
        "productos": productos,
    }
