"""Genera los íconos PNG de la PWA en app/public (brote blanco sobre fondo verde).

Uso (una vez, o si se cambia el diseño): pip install pillow && python scripts/generar_iconos.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

VERDE = (29, 107, 53)
BLANCO = (255, 255, 255)
SALIDA = Path(__file__).resolve().parent.parent / "app" / "public"


def dibujar(tam: int, margen: float, redondeado: bool) -> Image.Image:
    esc = 4  # dibujar grande y reducir para suavizar bordes
    t = tam * esc
    img = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if redondeado:
        d.rounded_rectangle([0, 0, t - 1, t - 1], radius=int(t * 0.22), fill=VERDE)
    else:
        d.rectangle([0, 0, t, t], fill=VERDE)
    m = t * margen
    area = t - 2 * m
    cx = t / 2
    base = m + area * 0.88
    # Tallo
    d.rounded_rectangle([cx - area * 0.035, m + area * 0.42, cx + area * 0.035, base], radius=int(area * 0.03), fill=BLANCO)
    # Hojas (elipses rotadas)
    for signo in (-1, 1):
        hoja = Image.new("RGBA", (t, t), (0, 0, 0, 0))
        dh = ImageDraw.Draw(hoja)
        w, h = area * 0.36, area * 0.17
        x0 = cx + signo * area * 0.03 + (0 if signo > 0 else -w)
        y0 = m + area * (0.30 if signo > 0 else 0.40)
        dh.ellipse([x0, y0, x0 + w, y0 + h], fill=BLANCO)
        hoja = hoja.rotate(signo * 28, center=(cx, y0 + h / 2), resample=Image.BICUBIC)
        img.alpha_composite(hoja)
    # Suelo
    d.rounded_rectangle([m + area * 0.18, base - area * 0.02, t - m - area * 0.18, base + area * 0.05],
                        radius=int(area * 0.03), fill=BLANCO)
    return img.resize((tam, tam), Image.LANCZOS)


if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    dibujar(192, 0.14, True).save(SALIDA / "icono-192.png")
    dibujar(512, 0.14, True).save(SALIDA / "icono-512.png")
    # Maskable: fondo completo y dibujo dentro de la zona segura (80 % central)
    dibujar(512, 0.24, False).save(SALIDA / "icono-maskable-512.png")
    dibujar(180, 0.16, False).convert("RGB").save(SALIDA / "apple-touch-icon.png")
    print("Íconos generados en", SALIDA)
