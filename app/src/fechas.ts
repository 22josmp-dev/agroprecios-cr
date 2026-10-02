// Fechas en hora de Costa Rica (UTC-6, sin horario de verano) y en español de Costa Rica.

export const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
  "setiembre", "octubre", "noviembre", "diciembre"];
export const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];

const MS_DIA = 86_400_000;
const DESFASE_CR = -6 * 3_600_000;

/** Fecha ISO (AAAA-MM-DD) de hoy en Costa Rica. */
export function hoyCR(ahora: Date = new Date()): string {
  return new Date(ahora.getTime() + DESFASE_CR).toISOString().slice(0, 10);
}

export function diasEntre(desdeIso: string, hastaIso: string): number {
  return Math.round((Date.parse(hastaIso) - Date.parse(desdeIso)) / MS_DIA);
}

/** "2026-09-28" -> "28 de setiembre" (con el año si se pide). */
export function fechaLarga(iso: string, conAnio = false): string {
  const [a, m, d] = iso.split("-").map(Number);
  return `${d} de ${MESES[m - 1]}${conAnio ? ` de ${a}` : ""}`;
}

/** "2026-09-28" -> "28 set" */
export function fechaCorta(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${d} ${MESES_CORTOS[m - 1]}`;
}

/** Momento UTC ISO -> "11:33 p. m." en hora de Costa Rica. */
export function horaCR(utcIso: string): string {
  const cr = new Date(Date.parse(utcIso) + DESFASE_CR);
  let h = cr.getUTCHours();
  const mm = String(cr.getUTCMinutes()).padStart(2, "0");
  const sufijo = h < 12 ? "a. m." : "p. m.";
  h = h % 12 || 12;
  return `${h}:${mm} ${sufijo}`;
}

/** Momento UTC ISO -> "28 de setiembre, 11:33 p. m." en hora de Costa Rica. */
export function momentoCR(utcIso: string): string {
  return `${fechaLarga(hoyCR(new Date(utcIso)))}, ${horaCR(utcIso)}`;
}

/** Día del año 0..364 (año no bisiesto) para un mes (1-12) y día. */
export function diaDelAnio(mes: number, dia: number): number {
  const acumulado = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  return acumulado[mes - 1] + dia - 1;
}

/** Día del año 0..364 -> "20 de mayo" */
export function textoDiaDelAnio(d: number): string {
  const n = ((Math.round(d) % 365) + 365) % 365;
  const fecha = new Date(Date.UTC(2025, 0, 1) + n * MS_DIA); // 2025 no es bisiesto
  return `${fecha.getUTCDate()} de ${MESES[fecha.getUTCMonth()]}`;
}

export function mesDeDia(d: number): number {
  const n = ((Math.round(d) % 365) + 365) % 365;
  return new Date(Date.UTC(2025, 0, 1) + n * MS_DIA).getUTCMonth() + 1;
}
