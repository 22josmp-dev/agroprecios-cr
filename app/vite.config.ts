import { readFile } from "node:fs/promises";
import { resolve, normalize } from "node:path";
import { defineConfig, type Plugin } from "vite";
import preact from "@preact/preset-vite";

/** En desarrollo sirve ../data (los datos reales del repositorio) en /data. */
function datosDev(): Plugin {
  const raiz = resolve(import.meta.dirname, "..", "data");
  return {
    name: "datos-dev",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/data", async (req, res, next) => {
        const ruta = normalize(resolve(raiz, "." + decodeURIComponent((req.url || "").split("?")[0])));
        if (!ruta.startsWith(raiz)) return next();
        try {
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(await readFile(ruta));
        } catch {
          res.statusCode = 404;
          res.end();
        }
      });
    },
  };
}

/**
 * Genera dist/sw.js con la lista exacta de archivos de la app (con su hash) para
 * precargarlos, y una versión de caché que cambia en cada compilación.
 */
function serviceWorker(): Plugin {
  return {
    name: "service-worker",
    apply: "build",
    generateBundle(_opts, bundle) {
      const archivos = Object.keys(bundle).filter((f) => !f.endsWith(".map"));
      const version = Date.now().toString(36);
      this.emitFile({
        type: "asset",
        fileName: "sw.js",
        source: SW(version, ["./", ...archivos, "manifest.webmanifest", "icono-192.png", "icono-512.png", "icono-maskable-512.png", "apple-touch-icon.png"]),
      });
    },
  };
}

const SW = (version: string, precache: string[]) => `// Generado en la compilación. No editar.
const VERSION = "${version}";
const APP = "app-" + VERSION;
const DATOS = "datos-v1";
const PRECARGA = ${JSON.stringify(precache)};

// Datos que se guardan al instalar, para que toda la app funcione sin conexión
const DATOS_BASE = ["data/meta.json", "data/latest.json", "data/catalog.json", "data/seasonal.json", "data/cycle_defaults.json"];

async function guardarDatos() {
  const c = await caches.open(DATOS);
  await Promise.all(DATOS_BASE.map((u) => fetch(u, { cache: "no-cache" }).then((r) => r.ok && c.put(u, r)).catch(() => {})));
  try {
    const meta = await (await c.match("data/meta.json")).json();
    // Últimos 2 meses de cada boletín: diario (data/prices) y semanal/quincenal (data/prices/<id>)
    const rutas = (meta.meses_precios || []).slice(-2).map((m) => "data/prices/" + m + ".json");
    for (const [id, f] of Object.entries(meta.fuentes || {})) {
      for (const m of (f.meses_precios || []).slice(-2)) rutas.push("data/prices/" + id + "/" + m + ".json");
    }
    await Promise.all(rutas.map((u) => fetch(u).then((r) => r.ok && c.put(u, r)).catch(() => {})));
  } catch (_) { /* sin meta: se guardará al usar la app */ }
}

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(APP).then((c) => c.addAll(PRECARGA)).then(guardarDatos).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((ks) => Promise.all(ks.filter((k) => k.startsWith("app-") && k !== APP).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/data/")) {
    // Datos: primero la red (siempre lo más nuevo); sin conexión, la última copia guardada.
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          if (r.ok) { const copia = r.clone(); caches.open(DATOS).then((c) => c.put(e.request, copia)); }
          return r;
        })
        .catch(() => caches.open(DATOS).then((c) => c.match(e.request)).then((r) => r || Response.error())),
    );
    return;
  }
  // App: primero la caché (carga instantánea y sin conexión).
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then((r) => r || fetch(e.request).catch(() => caches.match("./"))),
  );
});
`;

export default defineConfig({
  base: "./",
  plugins: [preact(), serviceWorker(), datosDev()],
  build: { target: "es2020", sourcemap: false },
  test: { environment: "node" },
} as never);
