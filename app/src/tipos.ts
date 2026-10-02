// Tipos de los archivos de /data (esquema en docs/DATOS.md)

export interface Meta {
  estado: "ok" | "pendiente" | "error";
  mensaje: string;
  datos_de_ejemplo: boolean;
  ultimo_intento_utc: string;
  ultima_actualizacion_exitosa_utc: string | null;
  fecha_boletin: string | null;
  registros: number;
  rechazados: number;
  meses_precios?: string[];
  /** Fuentes semanal y quincenal (el nivel superior es el boletín diario). */
  fuentes?: Record<string, MetaFuente>;
}

export type IdFuente = "diario" | "fruta" | "aromaticos";

export interface MetaFuente {
  nombre: string;
  frecuencia: "semanal" | "quincenal";
  estado: "ok" | "pendiente" | "error";
  mensaje: string;
  ultima_actualizacion_exitosa_utc: string | null;
  fecha_boletin: string | null;
  meses_precios: string[];
}

export interface InfoFuente {
  nombre: string;
  frecuencia: "diaria" | "semanal" | "quincenal";
  fecha_boletin: string;
  ventana_promedio_dias: number;
  texto_promedio: string;
}

export interface Comparacion {
  fecha: string;
  promedio: number;
  variacion_pct: number | null;
}

export interface ProductoHoy {
  id: string;
  nombre: string;
  cultivo: string | null;
  cultivo_id: string | null;
  categoria: string | null;
  unidad: string;
  kg: number | null;
  minimo: number;
  maximo: number;
  moda: number;
  promedio: number;
  precio_kg: number | null;
  vs_anterior: Comparacion | null;
  vs_semana: Comparacion | null;
  fuente: IdFuente;
  fecha_boletin: string;
  /** Contra el promedio de la ventana de la fuente (latest.fuentes[f].texto_promedio). */
  vs_promedio: { boletines: number; promedio: number | null; variacion_pct: number | null } | null;
}

export interface Latest {
  fecha_boletin: string;
  fuentes: Partial<Record<IdFuente, InfoFuente>>;
  datos_de_ejemplo: boolean;
  productos: ProductoHoy[];
}

export interface ProductoCatalogo {
  id: string;
  nombre: string;
  cultivo: string;
  cultivo_id: string;
  categoria: string;
  sinonimos: string[];
  unidades: { unidad: string; kg: number | null }[];
}

export interface Catalogo {
  productos: ProductoCatalogo[];
}

export interface IndiceProducto {
  id: string;
  nombre: string;
  cultivo_id: string;
  cultivo: string;
  productos_boletin: string[];
  unidad_precio: string | null;
  years_of_data: number;
  anios: [number, number] | null;
  confianza: "alta" | "media" | "baja";
  indice: (number | null)[] | null;
  desviacion: (number | null)[] | null;
  desviacion_media: number | null;
  metodo: string;
  meses_sin_dato: number[];
  motivo: string | null;
  indice_oficial_simm: (number | null)[] | null;
  indice_oferta_oficial_simm: (number | null)[] | null;
}

export interface Seasonal {
  datos_de_ejemplo: boolean;
  productos: IndiceProducto[];
}

export interface Historico {
  id: string;
  nombre: string;
  unidad_precio: string | null;
  precio: Record<string, (number | null)[]>;
  oferta_tm: Record<string, (number | null)[]>;
}

export interface MesPrecios {
  mes: string;
  datos_de_ejemplo: boolean;
  columnas: string[];
  dias: Record<string, [string, string, number, number, number, number][]>;
}

export interface CicloCultivo {
  cultivo_id: string;
  nombre: string;
  tipo: "anual" | "perenne" | "sin_dato";
  referencia: string | null;
  ciclo_dias: { baja: number | null; media: number | null; alta: number | null } | null;
  ventana_cosecha_dias: number | null;
  verified: boolean;
  nota?: string;
}

export interface Ciclos {
  verified: boolean;
  altitudes: Record<"baja" | "media" | "alta", string>;
  cultivos: CicloCultivo[];
}
