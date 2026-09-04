# Monitor Economía y Negocios — Portafolio

Recoge cada 30 minutos los titulares de las secciones
[Economía](https://www.portafolio.co/economia) y
[Negocios](https://www.portafolio.co/negocios) de portafolio.co,
y los publica como una portada estática.

```
.github/workflows/actualizar-noticias.yml   cron + commit automático
scraper/scrape.py                           extracción y fusión con el histórico
data/noticias.json                          archivo que consume la página
index.html                                  portada (GitHub Pages)
requirements.txt
```

## Montaje

1. Repositorio nuevo, rama `main`, con estos archivos en estas rutas.
   Cree `.github/workflows/actualizar-noticias.yml` con **Add file → Create new file**
   escribiendo la ruta completa, para que GitHub genere las carpetas.
2. **Settings → Actions → General → Workflow permissions**: *Read and write permissions*.
3. **Settings → Pages**: *Deploy from a branch*, rama `main`, carpeta `/ (root)`.
4. **Actions → Actualizar Portafolio → Run workflow** para la primera corrida.

## Si va a embeber la página en un iframe

En `index.html`, cambie la ruta relativa por la absoluta de su repo:

```js
const FUENTE_JSON = "https://USUARIO.github.io/REPO/data/noticias.json";
```

## Detalles

- Descarta el contenido patrocinado: filtra los `article` con clase
  `c-articulo--patrocinado` o con "patrocinado" en `data-seccion`, `data-board`
  o `data-autor`.
- Guarda además autor, subsección (Comercio, Infraestructura, Finanzas…),
  fecha de publicación y, cuando existe, la bajada del artículo principal.
- Si una de las dos secciones falla pero la otra responde, la corrida guarda lo
  que consiguió y termina en éxito. Solo falla si caen las dos.
- Conserva 60 titulares por sección y descarta lo anterior a 30 días
  (`MAX_POR_SECCION` y `DIAS_RETENCION` en `scrape.py`).
- Para agregar secciones, añádalas al diccionario `SECCIONES` en `scrape.py`
  **y** a la lista `SECCIONES` en `index.html`.

## Prueba local

```bash
pip install -r requirements.txt
python scraper/scrape.py
python -m http.server 8000   # abrir http://localhost:8000
```
