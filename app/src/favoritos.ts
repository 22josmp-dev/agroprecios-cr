// Favoritos: lo ÚNICO que la app guarda en el teléfono (localStorage). Sin datos personales.
import { useEffect, useState } from "preact/hooks";

const CLAVE = "agroprecios-favoritos";
const oyentes = new Set<(ids: string[]) => void>();

function leer(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(CLAVE) || "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function guardar(ids: string[]) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(ids));
  } catch {
    // Modo privado o almacenamiento bloqueado: funciona solo durante esta visita
  }
  oyentes.forEach((f) => f(ids));
}

let actuales = leer();

export function alternarFavorito(id: string) {
  actuales = actuales.includes(id) ? actuales.filter((x) => x !== id) : [...actuales, id];
  guardar(actuales);
}

export function useFavoritos(): string[] {
  const [ids, setIds] = useState(actuales);
  useEffect(() => {
    oyentes.add(setIds);
    return () => void oyentes.delete(setIds);
  }, []);
  return ids;
}
