import { render } from "preact";
import { App } from "./app";
import "./estilos.css";

render(<App />, document.getElementById("app")!);

// Service worker: guarda la app y los últimos datos para usarla sin conexión
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => { /* sin SW la app funciona igual en línea */ });
  });
}
