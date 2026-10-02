// Lectura de /data por fetch relativo. Cada archivo se pide una sola vez por sesión.
import type { Catalogo, Ciclos, Historico, IdFuente, Latest, MesPrecios, Meta, Seasonal } from "./tipos";

const cache = new Map<string, Promise<unknown>>();

export class SinDatos extends Error {}

function leer<T>(ruta: string, opcional = false): Promise<T> {
  if (!cache.has(ruta)) {
    const p = fetch(`data/${ruta}`, { cache: "no-cache" }).then((r) => {
      if (!r.ok) {
        if (opcional && r.status === 404) return null;
        throw new SinDatos(`No se pudo cargar ${ruta} (${r.status})`);
      }
      return r.json();
    });
    p.catch(() => cache.delete(ruta)); // reintentar en la próxima visita
    cache.set(ruta, p);
  }
  return cache.get(ruta) as Promise<T>;
}

export const cargarMeta = () => leer<Meta>("meta.json");
export const cargarLatest = () => leer<Latest>("latest.json");
export const cargarCatalogo = () => leer<Catalogo>("catalog.json");
export const cargarSeasonal = () => leer<Seasonal>("seasonal.json");
export const cargarCiclos = () => leer<Ciclos>("cycle_defaults.json");
export const cargarHistorico = (id: string) => leer<Historico | null>(`historico/${id}.json`, true);
/** Carpeta de precios de cada fuente dentro de data/ (igual que ingesta/config.py). */
export const DIR_PRECIOS: Record<IdFuente, string> = { diario: "prices", fruta: "prices/fruta", aromaticos: "prices/aromaticos" };
export const cargarMes = (mes: string, fuente: IdFuente = "diario") =>
  leer<MesPrecios | null>(`${DIR_PRECIOS[fuente]}/${mes}.json`, true);

/** Serie diaria (fecha, promedio) de un producto y unidad en los meses indicados. */
export async function serieDiaria(meses: string[], id: string, unidad: string, fuente: IdFuente = "diario"
): Promise<{ fecha: string; promedio: number }[]> {
  const contenido = await Promise.all(meses.map((m) => cargarMes(m, fuente)));
  const puntos: { fecha: string; promedio: number }[] = [];
  for (const mes of contenido) {
    if (!mes) continue;
    for (const [fecha, filas] of Object.entries(mes.dias)) {
      const fila = filas.find((f) => f[0] === id && f[1] === unidad);
      if (fila) puntos.push({ fecha, promedio: fila[5] });
    }
  }
  return puntos.sort((a, b) => a.fecha.localeCompare(b.fecha));
}
