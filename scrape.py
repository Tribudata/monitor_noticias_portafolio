#!/usr/bin/env python3
"""
Extrae los titulares de las secciones Economía y Negocios de portafolio.co
y los guarda en data/noticias.json.

Pensado para ejecutarse desde GitHub Actions con un cron.
El JSON acumula histórico: las secciones rotan cada pocas horas, así que
los titulares que salen de portada se conservan aquí.
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.portafolio.co/"

SECCIONES = {
    "Economía": "https://www.portafolio.co/economia",
    "Negocios": "https://www.portafolio.co/negocios",
}

MAX_POR_SECCION = 60
DIAS_RETENCION = 30

SALIDA = Path(__file__).resolve().parent.parent / "data" / "noticias.json"
BOGOTA = timezone(timedelta(hours=-5))

CABECERAS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}


def limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def es_patrocinado(art) -> bool:
    clases = art.get("class") or []
    if "c-articulo--patrocinado" in clases:
        return True
    etiquetas = " ".join([
        art.get("data-seccion", ""),
        art.get("data-board", ""),
        art.get("data-autor", ""),
    ]).lower()
    return "patrocinado" in etiquetas


def descargar(url: str) -> str:
    r = requests.get(url, headers=CABECERAS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def extraer(html: str) -> list:
    sopa = BeautifulSoup(html, "lxml")
    items = []
    urls_vistas = set()

    for art in sopa.select("article[data-name]"):
        if es_patrocinado(art):
            continue

        enlace = art.select_one("h3.c-articulo__titulo a.c-articulo__titulo__txt")
        if not enlace:
            enlace = art.select_one("h3.c-articulo__titulo a")
        if not enlace:
            continue

        titulo = limpiar(enlace.get_text())
        href = enlace.get("href") or ""
        if not titulo or not href:
            continue

        url = enlace.get("data-mrf-link") or urljoin(BASE, href)
        if url in urls_vistas:
            continue
        urls_vistas.add(url)

        resumen = art.select_one("p.c-article__subtitle a")

        items.append({
            "titulo": titulo,
            "url": url,
            "resumen": limpiar(resumen.get_text()) if resumen else "",
            "autor": limpiar(art.get("data-redactorvisible", "")),
            "subseccion": limpiar(art.get("data-subseccion", "")),
            "publicacion": limpiar(art.get("data-publicacion", "")),
        })

    return items


def cargar_previo() -> dict:
    if not SALIDA.exists():
        return {}
    try:
        return json.loads(SALIDA.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def fusionar(previo: dict, nuevo: dict, ahora: str) -> dict:
    secciones_previas = previo.get("secciones", {})
    limite = datetime.fromisoformat(ahora) - timedelta(days=DIAS_RETENCION)
    salida = {}
    nuevos_totales = 0

    for seccion in SECCIONES:
        por_url = {}

        for item in secciones_previas.get(seccion, []):
            try:
                if datetime.fromisoformat(item["capturado"]) < limite:
                    continue
            except (KeyError, ValueError):
                pass
            por_url[item["url"]] = item

        for item in nuevo.get(seccion, []):
            if item["url"] in por_url:
                por_url[item["url"]]["titulo"] = item["titulo"]
            else:
                por_url[item["url"]] = {**item, "capturado": ahora}
                nuevos_totales += 1

        ordenados = sorted(
            por_url.values(),
            key=lambda i: i.get("capturado", ""),
            reverse=True,
        )
        salida[seccion] = ordenados[:MAX_POR_SECCION]

    return {
        "fuente": BASE,
        "actualizado": ahora,
        "nuevos_en_esta_corrida": nuevos_totales,
        "secciones": salida,
    }


def main() -> int:
    ahora = datetime.now(BOGOTA).isoformat(timespec="seconds")
    nuevo = {}
    fallos = 0

    for seccion, url in SECCIONES.items():
        try:
            items = extraer(descargar(url))
        except requests.RequestException as e:
            print(f"{seccion}: no se pudo descargar ({e})", file=sys.stderr)
            nuevo[seccion] = []
            fallos += 1
            continue

        nuevo[seccion] = items
        print(f"{seccion}: {len(items)} titulares")

    if not any(nuevo.values()):
        print("Ninguna sección devolvió titulares: revise los selectores o la conexión.",
              file=sys.stderr)
        return 1

    datos = fusionar(cargar_previo(), nuevo, ahora)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Guardado {SALIDA} · {datos['nuevos_en_esta_corrida']} titulares nuevos")
    return 1 if fallos == len(SECCIONES) else 0


if __name__ == "__main__":
    raise SystemExit(main())
