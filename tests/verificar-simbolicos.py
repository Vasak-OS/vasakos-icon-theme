#!/usr/bin/env python3
"""Verifica que los iconos simbólicos del escritorio salgan de este pack y se vean.

Dos comprobaciones sobre cada nombre de `nombres-simbolicos.txt`:

1. **Que se resuelva dentro del pack.** El plugin de iconos pide con
   `FORCE_SYMBOLIC`, y GTK con esa bandera busca «<nombre>-symbolic» a lo largo
   de toda la cadena de herencia *antes* de probar el nombre pelado. Un nombre
   que el pack sólo tiene en `actions/16/` y no en `actions/symbolic/` termina
   resuelto por breeze —que hereda— y dibujado en #232629: negro sobre el tema
   oscuro. Así se perdieron veinte iconos de la barra del gestor de archivos.

2. **Que contraste contra el fondo de su variante.** Sólo se exige a los iconos
   monocromos grises, que son los que el instalador recolorea variante por
   variante. Los que tienen color propio —el ámbar del `dialog-warning`, el rojo
   del `edit-delete-shred`— dicen algo con ese color y se dejan en paz.

Uso:
    ./tests/verificar-simbolicos.py            # instala en un temporal y verifica
    ./tests/verificar-simbolicos.py <destino>  # verifica una instalación ya hecha

Necesita PyGObject y gtk-update-icon-cache, lo mismo que `install.sh`.
"""

import os
import re
import subprocess
import sys
import tempfile

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTA = os.path.join(RAIZ, "tests", "nombres-simbolicos.txt")

# El fondo de cada variante, tomado de los tokens del escritorio
# (`--ui-background-dark` y `--ui-background`).
VARIANTES = (("VasakOS-dark", "#1e1e2e"), ("VasakOS-light", "#eff1f5"))

# El mínimo con el que se corrigieron los 32 iconos invisibles del tema oscuro
# (a6ac9ae2). No es el 4.5:1 de texto: un glifo de 16 px es una forma, no algo
# que haya que leer letra por letra.
CONTRASTE_MINIMO = 2.0

COLOR = re.compile(r"#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}\b")


def a_rgb(texto):
    texto = texto.lstrip("#")
    if len(texto) == 3:
        texto = "".join(c * 2 for c in texto)
    return tuple(int(texto[i : i + 2], 16) for i in (0, 2, 4))


def luminancia(rgb):
    def canal(valor):
        valor /= 255
        return valor / 12.92 if valor <= 0.03928 else ((valor + 0.055) / 1.055) ** 2.4

    rojo, verde, azul = (canal(c) for c in rgb)
    return 0.2126 * rojo + 0.7152 * verde + 0.0722 * azul


def contraste(uno, otro):
    mayor, menor = sorted((luminancia(uno), luminancia(otro)), reverse=True)
    return (mayor + 0.05) / (menor + 0.05)


def es_gris(rgb):
    """Si el color es acromático, con la tolerancia justa para los casi-grises."""
    return max(rgb) - min(rgb) <= 8


def nombres():
    with open(LISTA, encoding="utf-8") as archivo:
        return [
            linea.strip()
            for linea in archivo
            if linea.strip() and not linea.startswith("#")
        ]


def instalar(destino):
    subprocess.run(
        [os.path.join(RAIZ, "install.sh"), "-d", destino, "-n", "VasakOS"],
        check=True,
        capture_output=True,
        text=True,
    )


def verificar(destino):
    fallas = []

    for variante, fondo in VARIANTES:
        tema = Gtk.IconTheme.new()
        # El destino primero, para que gane sobre el pack instalado en el
        # sistema; las rutas del sistema van igual porque la herencia a hicolor y
        # breeze es parte de lo que se está midiendo.
        tema.set_search_path([destino, "/usr/share/icons", "/usr/share/pixmaps"])
        tema.set_custom_theme(variante)

        for nombre in nombres():
            info = tema.lookup_icon(
                nombre,
                16,
                Gtk.IconLookupFlags.FORCE_SYMBOLIC | Gtk.IconLookupFlags.FORCE_SVG,
            )
            ruta = info.get_filename() if info else None

            if not ruta:
                fallas.append(f"{variante}: «{nombre}» no lo tiene nadie")
                continue

            if not ruta.startswith(destino):
                fallas.append(
                    f"{variante}: «{nombre}» lo resuelve otro tema — {ruta}\n"
                    f"    falta actions/symbolic/{nombre}-symbolic.svg en el pack"
                )
                continue

            with open(ruta, encoding="utf-8", errors="ignore") as archivo:
                colores = {a_rgb(c) for c in COLOR.findall(archivo.read())}

            grises = [c for c in colores if es_gris(c)]
            if not colores or len(grises) != len(colores):
                # Tiene color propio: no se le pide contraste de monocromo.
                continue

            mejor = max(contraste(c, a_rgb(fondo)) for c in grises)
            if mejor < CONTRASTE_MINIMO:
                fallas.append(
                    f"{variante}: «{nombre}» contrasta {mejor:.2f}:1 contra {fondo} "
                    f"— {os.path.basename(ruta)}"
                )

    return fallas


def main():
    if len(sys.argv) > 1:
        fallas = verificar(os.path.abspath(sys.argv[1]))
    else:
        with tempfile.TemporaryDirectory(prefix="vasakos-iconos-") as destino:
            instalar(destino)
            fallas = verificar(destino)

    if fallas:
        print(f"{len(fallas)} problemas:")
        for falla in fallas:
            print(f"  · {falla}")
        return 1

    print(f"{len(nombres())} nombres × {len(VARIANTES)} variantes: todo en orden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
