import type { IdFuente } from "./tipos";

/** Los tres boletines del PIMA-CENADA que muestra la app. */
export const FUENTES: { id: IdFuente; nombre: string; frecuencia: string; corto: string }[] = [
  { id: "diario", nombre: "Boletín diario", frecuencia: "diario", corto: "Diario" },
  { id: "fruta", nombre: "Fruta importada", frecuencia: "semanal", corto: "Semanal" },
  { id: "aromaticos", nombre: "Aromáticos y gourmet", frecuencia: "quincenal", corto: "Quincenal" },
];

export const fuente = (id: IdFuente) => FUENTES.find((f) => f.id === id) ?? FUENTES[0];
