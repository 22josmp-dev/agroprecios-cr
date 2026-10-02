// Resumen del día en lenguaje simple, generado en el navegador a partir de latest.json.
import { direccion, porcentaje } from "./formato";
import type { IdFuente, InfoFuente, ProductoHoy } from "./tipos";

type Fuentes = Partial<Record<IdFuente, InfoFuente>>;

const TEXTO_PROMEDIO: Record<IdFuente, string> = {
  diario: "los últimos 30 días", fruta: "las últimas 5 semanas", aromaticos: "los últimos 2 meses",
};

function frasePromedio(p: ProductoHoy, fuentes: Fuentes): string | null {
  const pct = p.vs_promedio?.variacion_pct;
  const dir = direccion(pct);
  if (pct === null || pct === undefined || !dir) return null;
  const nombre = p.nombre.toLowerCase();
  const ventana = fuentes[p.fuente]?.texto_promedio ?? TEXTO_PROMEDIO[p.fuente];
  // "Hoy" solo para el boletín diario; los otros son semanales o quincenales
  const inicio = p.fuente === "diario" ? `Hoy el precio de ${nombre}` : `El precio de ${nombre}`;
  if (dir === "igual") return `${inicio} está igual a su promedio de ${ventana}.`;
  const lado = dir === "sube" ? "por encima" : "por debajo";
  return `${inicio} está ${porcentaje(pct)} ${lado} de su promedio de ${ventana}.`;
}

export function resumenDelDia(productos: ProductoHoy[], favoritos: string[] = [], fuentes: Fuentes = {}): string[] {
  const frases: string[] = [];
  const favs = productos.filter((p) => favoritos.includes(p.id));
  for (const p of favs.slice(0, 3)) {
    const f = frasePromedio(p, fuentes);
    if (f) frases.push(f);
  }
  if (frases.length < 3) {
    // Mayor alza y mayor baja del boletín diario (el más actual)
    const conDato = productos.filter((p) => p.fuente === "diario" && !favoritos.includes(p.id)
      && p.vs_promedio?.variacion_pct !== null && p.vs_promedio?.variacion_pct !== undefined);
    const orden = [...conDato].sort((a, b) => b.vs_promedio!.variacion_pct! - a.vs_promedio!.variacion_pct!);
    const alza = orden[0];
    const baja = orden[orden.length - 1];
    if (alza && alza.vs_promedio!.variacion_pct! >= 1) frases.push(frasePromedio(alza, fuentes)!);
    if (baja && baja !== alza && baja.vs_promedio!.variacion_pct! <= -1) frases.push(frasePromedio(baja, fuentes)!);
  }
  const conAnterior = productos.filter((p) => p.fuente === "diario"
    && p.vs_anterior?.variacion_pct !== null && p.vs_anterior?.variacion_pct !== undefined);
  if (conAnterior.length) {
    const cuenta = { sube: 0, baja: 0, igual: 0 };
    for (const p of conAnterior) cuenta[direccion(p.vs_anterior!.variacion_pct)!]++;
    const n = (k: number, uno: string, varios: string) => `${k} ${k === 1 ? uno : varios}`;
    frases.push(`Frente al boletín diario anterior: ${n(cuenta.sube, "producto subió", "productos subieron")}, ` +
      `${n(cuenta.baja, "bajó", "bajaron")} y ${n(cuenta.igual, "se mantuvo igual", "se mantuvieron iguales")}.`);
  }
  return frases;
}
