// Pruebas del motor de la guía con índices SINTÉTICOS (DATOS DE EJEMPLO).
import { describe, expect, it } from "vitest";
import { diaDelAnio } from "./fechas";
import { calcularGuia, DIAS, interpolarDiario, SEPARACION_MIN, type EntradaGuia } from "./guia";

/** Índice mensual con un pico en `mesPico` (1-12), normalizado a promedio 1. */
function conPico(mesPico: number, fuerza = 0.4): number[] {
  const crudo = Array.from({ length: 12 }, (_, i) => {
    const dist = Math.min(Math.abs(i + 1 - mesPico), 12 - Math.abs(i + 1 - mesPico));
    return 1 + fuerza * Math.exp(-(dist * dist) / 2);
  });
  const prom = crudo.reduce((s, v) => s + v, 0) / 12;
  return crudo.map((v) => v / prom);
}

const entrada = (indice: (number | null)[], anios = 8, desv = 0.05): EntradaGuia => ({
  indice, desviacion: Array(12).fill(desv), desviacion_media: desv, years_of_data: anios,
});

const distanciaCircular = (a: number, b: number) => Math.min(((a - b) % DIAS + DIAS) % DIAS, ((b - a) % DIAS + DIAS) % DIAS);

describe("guía de siembra", () => {
  it("pico en agosto y ciclo de 90 días: la mejor siembra cae ~90 días antes del pico", () => {
    const pico = diaDelAnio(8, 15);
    const r = calcularGuia(entrada(conPico(8)), 90, 0);
    expect(r.valido).toBe(true);
    expect(distanciaCircular(r.mejores[0].siembra, pico - 90)).toBeLessThanOrEqual(5);
    expect(r.mejores[0].difPromedioPct).toBeGreaterThan(20);
  });

  it("con ventana de cosecha de 30 días la siembra se adelanta media ventana", () => {
    const pico = diaDelAnio(8, 15);
    const r = calcularGuia(entrada(conPico(8)), 90, 30);
    expect(distanciaCircular(r.mejores[0].siembra, pico - 90 - 15)).toBeLessThanOrEqual(5);
  });

  it("cruce de año: pico en enero, siembra en el año anterior y cosecha que cruza el 31 de diciembre", () => {
    const pico = diaDelAnio(1, 15);
    const r = calcularGuia(entrada(conPico(1)), 90, 40);
    const esperado = pico - 90 - 20 + DIAS; // ~26 de setiembre
    const mejor = r.mejores[0];
    expect(distanciaCircular(mejor.siembra, esperado)).toBeLessThanOrEqual(5);
    expect(mejor.siembra).toBeGreaterThan(diaDelAnio(9, 1));
    // La ventana empieza en diciembre y termina en enero/febrero
    expect(mejor.cosechaInicio).toBeGreaterThan(mejor.cosechaFin);
    // Todos los días tienen candidato (ninguna ventana se pierde al cruzar el año)
    expect(r.candidatos.every((c) => c !== null)).toBe(true);
  });

  it("las 3 mejores fechas están separadas al menos 14 días", () => {
    const r = calcularGuia(entrada(conPico(8)), 90, 30);
    expect(r.mejores).toHaveLength(3);
    for (let i = 0; i < 3; i++)
      for (let j = i + 1; j < 3; j++)
        expect(distanciaCircular(r.mejores[i].siembra, r.mejores[j].siembra)).toBeGreaterThanOrEqual(SEPARACION_MIN);
  });

  it("datos insuficientes: menos de 3 años -> confianza baja", () => {
    const r = calcularGuia(entrada(conPico(8), 2), 90, 30);
    expect(r.mejores.every((m) => m.confianza === "baja")).toBe(true);
  });

  it("confianza alta con ≥5 años y desviación baja; media con 3–4 años", () => {
    expect(calcularGuia(entrada(conPico(8), 8, 0.05), 90, 30).mejores[0].confianza).toBe("alta");
    expect(calcularGuia(entrada(conPico(8), 8, 0.4), 90, 30).mejores[0].confianza).toBe("baja");
    expect(calcularGuia(entrada(conPico(8), 4, 0.05), 90, 30).mejores[0].confianza).toBe("media");
  });

  it("sin índice no hay recomendación", () => {
    const r = calcularGuia({ indice: null, desviacion: null, desviacion_media: null, years_of_data: 0 }, 90, 30);
    expect(r.valido).toBe(false);
    expect(r.motivo).toMatch(/suficientes/);
  });

  it("la puntuación penaliza el riesgo: índice − 0,5 × desviación", () => {
    const r = calcularGuia(entrada(conPico(8), 8, 0.2), 90, 0);
    const c = r.mejores[0];
    expect(c.puntaje).toBeCloseTo(c.indiceEsperado - 0.5 * c.riesgo, 10);
  });

  it("meses sin mercado: ninguna ventana de cosecha cae en ellos", () => {
    const indice: (number | null)[] = conPico(8);
    indice[2] = null; // marzo
    indice[3] = null; // abril
    const r = calcularGuia(entrada(indice), 60, 10);
    const inicioMarzo = diaDelAnio(3, 1), finAbril = diaDelAnio(4, 30);
    for (const c of r.candidatos) {
      if (!c) continue;
      for (let k = 0; k <= 10; k++) {
        const d = (c.siembra + 60 + k) % DIAS;
        expect(d >= inicioMarzo && d <= finAbril).toBe(false);
      }
    }
  });

  it("interpolación circular: continua entre diciembre y enero", () => {
    const diario = interpolarDiario([2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]);
    // A mitad de camino entre el 15 dic (0) y el 15 ene (2) el valor es ~1
    expect(diario[diaDelAnio(12, 31)]!).toBeCloseTo(1, 0);
    expect(diario[diaDelAnio(1, 15)]).toBeCloseTo(2, 5);
  });

  it("diferencia frente a la peor fecha es positiva", () => {
    const r = calcularGuia(entrada(conPico(8)), 90, 30);
    expect(r.mejores[0].difPeorPct).toBeGreaterThan(0);
    expect(r.peor!.puntaje).toBeLessThanOrEqual(r.mejores[2].puntaje);
  });
});
