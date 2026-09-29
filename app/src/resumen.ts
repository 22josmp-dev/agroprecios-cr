// Resumen del día en lenguaje simple, generado en el navegador a partir de latest.json.
import { direccion, porcentaje } from "./formato";
import type { ProductoHoy } from "./tipos";

function frase30d(p: ProductoHoy): string | null {
  const pct = p.vs_30d?.variacion_pct;
  const dir = direccion(pct);
  if (pct === null || pct === undefined || !dir) return null;
  const nombre = p.nombre.toLowerCase();
  if (dir === "igual") return `Hoy el precio de ${nombre} está igual a su promedio de los últimos 30 días.`;
  const lado = dir === "sube" ? "por encima" : "por debajo";
  return `Hoy el precio de ${nombre} está ${porcentaje(pct)} ${lado} de su promedio de los últimos 30 días.`;
}

export function resumenDelDia(productos: ProductoHoy[], favoritos: string[] = []): string[] {
  const frases: string[] = [];
  const favs = productos.filter((p) => favoritos.includes(p.id));
  for (const p of favs.slice(0, 3)) {
    const f = frase30d(p);
    if (f) frases.push(f);
  }
  if (frases.length < 3) {
    const conDato = productos.filter((p) => p.vs_30d?.variacion_pct !== null && p.vs_30d?.variacion_pct !== undefined
      && !favoritos.includes(p.id));
    const orden = [...conDato].sort((a, b) => b.vs_30d!.variacion_pct! - a.vs_30d!.variacion_pct!);
    const alza = orden[0];
    const baja = orden[orden.length - 1];
    if (alza && alza.vs_30d!.variacion_pct! >= 1) frases.push(frase30d(alza)!);
    if (baja && baja !== alza && baja.vs_30d!.variacion_pct! <= -1) frases.push(frase30d(baja)!);
  }
  const conAnterior = productos.filter((p) => p.vs_anterior?.variacion_pct !== null && p.vs_anterior?.variacion_pct !== undefined);
  if (conAnterior.length) {
    const cuenta = { sube: 0, baja: 0, igual: 0 };
    for (const p of conAnterior) cuenta[direccion(p.vs_anterior!.variacion_pct)!]++;
    const n = (k: number, uno: string, varios: string) => `${k} ${k === 1 ? uno : varios}`;
    frases.push(`Frente al boletín anterior: ${n(cuenta.sube, "producto subió", "productos subieron")}, ` +
      `${n(cuenta.baja, "bajó", "bajaron")} y ${n(cuenta.igual, "se mantuvo igual", "se mantuvieron iguales")}.`);
  }
  return frases;
}
