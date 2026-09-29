/** ₡1 130 · ₡27 857 · ₡319,23 (miles con espacio fino, coma decimal, estilo es-CR). */
export function colones(valor: number): string {
  const decimales = valor < 1000 && !Number.isInteger(valor) ? 2 : 0;
  const texto = valor.toLocaleString("es-CR", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
  return `₡${texto}`;
}

export function porcentaje(valor: number, conSigno = false): string {
  const abs = Math.abs(valor).toLocaleString("es-CR", { maximumFractionDigits: Math.abs(valor) < 10 ? 1 : 0 });
  if (!conSigno) return `${abs} %`;
  return `${valor > 0 ? "+" : valor < 0 ? "−" : ""}${abs} %`;
}

export type Direccion = "sube" | "baja" | "igual";

/** Menos de 1 % de cambio se considera "igual". */
export function direccion(pct: number | null | undefined): Direccion | null {
  if (pct === null || pct === undefined) return null;
  if (pct >= 1) return "sube";
  if (pct <= -1) return "baja";
  return "igual";
}
