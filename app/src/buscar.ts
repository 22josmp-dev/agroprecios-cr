import { normalizar } from "./texto";

export interface Entrada {
  id: string;
  nombre: string;
  cultivo?: string;
  sinonimos?: string[];
}

export interface Resultado<T extends Entrada> {
  entrada: T;
  puntaje: number;
  /** Texto con el que coincidió (útil para mostrar "batata → Camote"). */
  coincidencia: string;
}

/** Distancia de Damerau-Levenshtein (alineamiento óptimo): cambios, altas, bajas y transposiciones. */
export function distancia(a: string, b: string): number {
  const d: number[][] = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const costo = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + costo);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
      }
    }
  }
  return d[a.length][b.length];
}

/** Errores tolerados según el largo de lo escrito. */
function tolerancia(largo: number): number {
  if (largo <= 3) return 0;
  if (largo <= 6) return 1;
  return 2;
}

/** ¿Qué tan bien coincide una palabra escrita con una palabra del texto? (0 = nada) */
function puntajePalabra(q: string, t: string): number {
  if (t === q) return 1;
  if (t.startsWith(q)) return 0.9;
  const tol = tolerancia(q.length);
  if (tol === 0) return 0;
  // Contra la palabra completa y contra su comienzo (para quien aún está escribiendo)
  const dist = Math.min(distancia(q, t), distancia(q, t.slice(0, q.length)));
  return dist <= tol ? 0.75 - 0.1 * dist : 0;
}

function puntajeTexto(consulta: string, texto: string): number {
  const t = normalizar(texto);
  if (!t) return 0;
  if (t === consulta) return 100;
  if (t.startsWith(consulta)) return 92;
  const palabrasQ = consulta.split(" ");
  const palabrasT = t.split(" ");
  let total = 0;
  for (const q of palabrasQ) {
    const mejor = Math.max(0, ...palabrasT.map((p) => puntajePalabra(q, p)));
    if (mejor === 0) return t.includes(consulta) ? 60 : 0;
    total += mejor;
  }
  return Math.round(85 * (total / palabrasQ.length));
}

export function buscar<T extends Entrada>(consulta: string, entradas: T[], limite = 12): Resultado<T>[] {
  const q = normalizar(consulta);
  if (!q) return [];
  const resultados: Resultado<T>[] = [];
  for (const entrada of entradas) {
    const candidatos: [string, number][] = [
      [entrada.nombre, 0],
      ...(entrada.cultivo ? [[entrada.cultivo, -2] as [string, number]] : []),
      ...(entrada.sinonimos || []).map((s) => [s, -5] as [string, number]),
    ];
    let mejor: Resultado<T> | null = null;
    for (const [texto, ajuste] of candidatos) {
      const p = puntajeTexto(q, texto);
      if (p > 0 && (!mejor || p + ajuste > mejor.puntaje)) mejor = { entrada, puntaje: p + ajuste, coincidencia: texto };
    }
    if (mejor) resultados.push(mejor);
  }
  resultados.sort((a, b) => b.puntaje - a.puntaje || a.entrada.nombre.localeCompare(b.entrada.nombre, "es"));
  return resultados.slice(0, limite);
}
