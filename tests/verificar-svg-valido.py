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

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ESPACIO_SVG = "http://www.w3.org/2000/svg"


def problemas_de(archivo: Path) -> list[str]:
    """Lo que haría que un navegador no dibuje este archivo.

    Lo decide el árbol y no una expresión regular sobre el texto: `<svg[^>]*>`
    termina en el primer `>`, que puede estar dentro de un atributo o de un
    comentario, y buscar la cadena `xmlns=` rechaza `xmlns = …`, que es XML
    válido. Si el documento parsea y su raíz cae en el espacio de nombres SVG,
    entonces lo declara.
    """
    try:
        texto = archivo.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [f"no se pudo leer: {error}"]

    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError as error:
        # Una etiqueta sin cerrar la dibuja librsvg y no un navegador.
        return [f"XML mal formado: {error}"]

    if raiz.tag == f"{{{ESPACIO_SVG}}}svg":
        return []
    if raiz.tag == "svg":
        # Lo que rompió las flechas: sin espacio de nombres, para un navegador
        # esto no es un documento SVG.
        return ["el <svg> no declara xmlns"]
    return [f"la raíz no es un <svg> del espacio de nombres SVG, sino <{raiz.tag}>"]


def main() -> int:
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "src"
    if not raiz.is_dir():
        print(f"no existe el directorio {raiz}", file=sys.stderr)
        return 2

    revisados = 0
    con_problemas: list[tuple[Path, list[str]]] = []
    ya_vistos: set[Path] = set()

    for archivo in sorted(raiz.rglob("*.svg")):
        if archivo.is_symlink():
            # Un enlace no se salta sin mirarlo: si está roto no lo dibuja nadie,
            # y si apunta fuera del árbol que se recorre, saltarlo daría por
            # bueno un icono que nunca se revisó.
            try:
                destino = archivo.resolve(strict=True)
            except OSError:
                con_problemas.append((archivo, ["el enlace no lleva a ningún archivo"]))
                continue
            if destino.is_relative_to(raiz):
                continue  # se revisa por su cuenta al llegarle el turno
            if destino in ya_vistos:
                continue
            ya_vistos.add(destino)
            revisados += 1
            fallas = problemas_de(destino)
            if fallas:
                con_problemas.append((archivo, [f"apunta fuera del árbol: {f}" for f in fallas]))
            continue

        if not archivo.is_file():
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
