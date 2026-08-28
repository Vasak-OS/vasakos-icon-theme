#!/usr/bin/env python3
"""Verifica que cada icono del pack sea un SVG que un navegador acepte dibujar.

GTK no alcanza como juez. El escritorio de VasakOS no le pasa la ruta del icono
a GTK: el plugin de iconos lee el archivo, lo manda en base64 y la interfaz lo
dibuja con `<img src="data:image/svg+xml;base64,…">`. Y ahí las reglas son las
del navegador, no las de librsvg.

La diferencia que costó los iconos de la barra del gestor de archivos: un SVG
**sin `xmlns`** no es un documento SVG para un navegador. librsvg lo dibuja
igual —es tolerante y asume el espacio de nombres—, así que el icono se veía
bien en cualquier prueba hecha con GTK y salía como imagen rota en la
aplicación. Eran 67 archivos del pack, entre ellos `go-up`, `go-previous` y
`go-next`: las flechas de atrás, adelante y subir.

Uso:
    ./tests/verificar-svg-valido.py         # sobre `src/` de este repositorio
    ./tests/verificar-svg-valido.py <ruta>  # sobre una instalación ya hecha
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ESPACIO_SVG = "http://www.w3.org/2000/svg"
ETIQUETA_ABRE = re.compile(r"<svg\b[^>]*>", re.S)


def problemas_de(archivo: Path) -> list[str]:
    """Lo que haría que un navegador no dibuje este archivo."""
    fallas = []

    try:
        texto = archivo.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [f"no se pudo leer: {error}"]

    etiqueta = ETIQUETA_ABRE.search(texto)
    if etiqueta is None:
        return ["no tiene una etiqueta <svg>"]

    # Lo que rompió las flechas. Se mira en la etiqueta de apertura y no en el
    # archivo entero: un `xmlns` de otro elemento —`<style>`, un `<image>`
    # incrustado— no le da espacio de nombres al documento.
    if "xmlns=" not in etiqueta.group(0):
        fallas.append("el <svg> no declara xmlns")

    # Y que además sea XML bien formado: una etiqueta sin cerrar la dibuja
    # librsvg y no un navegador.
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError as error:
        fallas.append(f"XML mal formado: {error}")
    else:
        if not raiz.tag.endswith("svg"):
            fallas.append(f"la raíz no es <svg> sino <{raiz.tag}>")
        elif raiz.tag != f"{{{ESPACIO_SVG}}}svg":
            fallas.append(f"la raíz no está en el espacio de nombres SVG: {raiz.tag}")

    return fallas


def main() -> int:
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "src"
    if not raiz.is_dir():
        print(f"no existe el directorio {raiz}", file=sys.stderr)
        return 2

    revisados = 0
    con_problemas: list[tuple[Path, list[str]]] = []

    for archivo in sorted(raiz.rglob("*.svg")):
        # Los enlaces apuntan a un archivo que ya se revisa por su cuenta.
        if archivo.is_symlink() or not archivo.is_file():
            continue
        revisados += 1
        fallas = problemas_de(archivo)
        if fallas:
            con_problemas.append((archivo, fallas))

    if con_problemas:
        print(f"{len(con_problemas)} de {revisados} iconos no los dibujaría un navegador:\n")
        for archivo, fallas in con_problemas:
            print(f"  {archivo.relative_to(raiz)}")
            for falla in fallas:
                print(f"      {falla}")
        return 1

    print(f"{revisados} iconos en orden: todos declaran xmlns y son XML bien formado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
