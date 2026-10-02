// Motor de la guía de siembra (informativa). Todo en días del año 0..364 (año de 365 días).
import { diaDelAnio, textoDiaDelAnio } from "./fechas";
import { porcentaje } from "./formato";

export const DIAS = 365;
export const SEPARACION_MIN = 14;
export const DESVIACION_BAJA = 0.15; // igual que el motor de datos (ingesta/config.py)

export interface EntradaGuia {
  indice: (number | null)[] | null; // 12 valores, promedio 1.0; null = mes sin mercado
  desviacion: (number | null)[] | null;
  desviacion_media: number | null;
  years_of_data: number;
}

export interface Candidato {
  siembra: number;
  cosechaInicio: number;
  cosechaFin: number;
  indiceEsperado: number;
  riesgo: number;
  puntaje: number;
}

export type Confianza = "alta" | "media" | "baja";

export interface Recomendacion extends Candidato {
  difPromedioPct: number;
  difPeorPct: number;
  confianza: Confianza;
  /** Por qué tiene esa confianza, en lenguaje simple. */
  motivoConfianza: string;
  explicacion: string;
}

export interface ResultadoGuia {
  valido: boolean;
  motivo?: string;
  indiceDiario: (number | null)[];
  riesgoDiario: number[];
  candidatos: (Candidato | null)[];
  mejores: Recomendacion[];
  peor: Candidato | null;
  promedioAnual: number;
}

const mod = (n: number) => ((n % DIAS) + DIAS) % DIAS;

/** Interpolación lineal circular entre los días 15 de cada mes. Meses sin dato -> null. */
export function interpolarDiario(mensual: (number | null)[]): (number | null)[] {
  const anclas = mensual
    .map((v, i) => ({ dia: diaDelAnio(i + 1, 15), v, mes: i + 1 }))
    .filter((a): a is { dia: number; v: number; mes: number } => a.v !== null && a.v !== undefined);
  const salida: (number | null)[] = Array(DIAS).fill(null);
  if (anclas.length === 0) return salida;
  const mesDe = (d: number) => new Date(Date.UTC(2025, 0, 1 + d)).getUTCMonth(); // 0..11
  for (let d = 0; d < DIAS; d++) {
    if (mensual[mesDe(d)] === null || mensual[mesDe(d)] === undefined) continue;
    if (anclas.length === 1) {
      salida[d] = anclas[0].v;
      continue;
    }
    // ancla anterior (≤ d) y siguiente (> d), circulares
    let prev = anclas[anclas.length - 1];
    let prevDia = prev.dia - DIAS;
    for (const a of anclas) if (a.dia <= d) { prev = a; prevDia = a.dia; }
    let next = anclas[0];
    let nextDia = next.dia + DIAS;
    for (let k = anclas.length - 1; k >= 0; k--) if (anclas[k].dia > d) { next = anclas[k]; nextDia = anclas[k].dia; }
    const t = (d - prevDia) / (nextDia - prevDia);
    salida[d] = prev.v + (next.v - prev.v) * t;
  }
  return salida;
}

export function confianzaVentana(anios: number, riesgo: number): Confianza {
  if (anios >= 5 && riesgo <= DESVIACION_BAJA) return "alta";
  if (anios >= 3 && anios <= 4) return "media";
  return "baja";
}

export function calcularGuia(entrada: EntradaGuia, ciclo: number, ventana: number): ResultadoGuia {
  const vacio: ResultadoGuia = {
    valido: false, indiceDiario: Array(DIAS).fill(null), riesgoDiario: Array(DIAS).fill(0),
    candidatos: Array(DIAS).fill(null), mejores: [], peor: null, promedioAnual: 1,
  };
  if (!entrada.indice || entrada.indice.filter((v) => v !== null).length < 3) {
    return { ...vacio, motivo: "No hay suficientes datos de precios para este cultivo." };
  }
  if (!(ciclo > 0) || ventana < 0) return { ...vacio, motivo: "Indique un ciclo mayor que cero." };
  const indiceDiario = interpolarDiario(entrada.indice);
  const desvMensual = (entrada.desviacion || Array(12).fill(null)).map((v) => v ?? entrada.desviacion_media ?? 0);
  const riesgoDiario = interpolarDiario(desvMensual).map((v) => v ?? 0);
  const conocidos = indiceDiario.filter((v): v is number => v !== null);
  const promedioAnual = conocidos.reduce((s, v) => s + v, 0) / conocidos.length;

  const candidatos: (Candidato | null)[] = [];
  const ciclo_ = Math.round(ciclo);
  const ventana_ = Math.round(ventana);
  for (let d = 0; d < DIAS; d++) {
    let suma = 0, sumaRiesgo = 0, n = 0, sinMercado = false;
    for (let k = 0; k <= ventana_; k++) {
      const dia = mod(d + ciclo_ + k);
      const v = indiceDiario[dia];
      if (v === null) { sinMercado = true; break; }
      suma += v; sumaRiesgo += riesgoDiario[dia]; n++;
    }
    if (sinMercado || n === 0) { candidatos.push(null); continue; }
    const indiceEsperado = suma / n;
    const riesgo = sumaRiesgo / n;
    candidatos.push({
      siembra: d, cosechaInicio: mod(d + ciclo_), cosechaFin: mod(d + ciclo_ + ventana_),
      indiceEsperado, riesgo, puntaje: indiceEsperado - 0.5 * riesgo,
    });
  }
  const validos = candidatos.filter((c): c is Candidato => c !== null);
  if (validos.length === 0) {
    return { ...vacio, indiceDiario, riesgoDiario, motivo: "Con ese ciclo, la cosecha siempre caería en meses sin mercado en el CENADA." };
  }
  const peor = validos.reduce((a, b) => (b.puntaje < a.puntaje ? b : a));
  const ordenados = [...validos].sort((a, b) => b.puntaje - a.puntaje);
  const elegidos: Candidato[] = [];
  const distancia = (a: number, b: number) => Math.min(mod(a - b), mod(b - a));
  for (const c of ordenados) {
    if (elegidos.every((e) => distancia(e.siembra, c.siembra) >= SEPARACION_MIN)) elegidos.push(c);
    if (elegidos.length === 3) break;
  }
  const mejores = elegidos.map((c): Recomendacion => {
    const difPromedioPct = (c.indiceEsperado / promedioAnual - 1) * 100;
    const difPeorPct = (c.indiceEsperado / peor.indiceEsperado - 1) * 100;
    const confianza = confianzaVentana(entrada.years_of_data, c.riesgo);
    return { ...c, difPromedioPct, difPeorPct, confianza, motivoConfianza: motivoConfianza(confianza, entrada.years_of_data),
      explicacion: explicar(c, difPromedioPct) };
  });
  return { valido: true, indiceDiario, riesgoDiario, candidatos, mejores, peor, promedioAnual };
}

export function motivoConfianza(confianza: Confianza, anios: number): string {
  if (confianza === "alta") return `Hay ${anios} años de datos y en esas fechas el precio se repite parecido cada año.`;
  if (confianza === "media") return `Hay solo ${anios} años de datos.`;
  if (anios < 3) return `Hay pocos datos: ${anios === 1 ? "1 año" : `${anios} años`}.`;
  return `Aunque hay ${anios} años de datos, en esas fechas el precio cambió mucho de un año a otro.`;
}

export function explicar(c: Candidato, difPromedioPct: number): string {
  const cuando = `Si siembra el ${textoDiaDelAnio(c.siembra)}, la cosecha caería entre el ` +
    `${textoDiaDelAnio(c.cosechaInicio)} y el ${textoDiaDelAnio(c.cosechaFin)}.`;
  if (Math.abs(difPromedioPct) < 1) return `${cuando} En esas fechas el precio suele estar cerca del promedio del año.`;
  const lado = difPromedioPct > 0 ? "por encima" : "por debajo";
  return `${cuando} En esas fechas el precio mayorista suele estar ${porcentaje(difPromedioPct)} ${lado} del promedio del año.`;
}
