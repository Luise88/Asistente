"""
Junta los últimos titulares de varios medios (RSS) y los guarda en noticias.json.
Lo ejecuta GitHub Actions cada 30 minutos (ver .github/workflows/noticias.yml).
No usa IA ni librerías externas.

Para agregar o quitar medios, editá la lista FEEDS:
  (nombre del medio, "ar" o "mundo", dirección del RSS)
"""
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FEEDS = [
    # Argentina
    ("Infobae", "ar", "https://www.infobae.com/arc/outboundfeeds/rss/"),
    ("Clarín", "ar", "https://www.clarin.com/rss/lo-ultimo/"),
    ("La Nación", "ar", "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml"),
    ("Página/12", "ar", "https://www.pagina12.com.ar/rss/portada"),
    ("Ámbito", "ar", "https://www.ambito.com/rss/pages/home.xml"),
    ("Perfil", "ar", "https://www.perfil.com/feed"),
    # Mundo
    ("BBC Mundo", "mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    ("DW Español", "mundo", "https://rss.dw.com/xml/rss-sp-all"),
    ("France 24", "mundo", "https://www.france24.com/es/rss"),
    ("El País", "mundo", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),
    ("CNN Español", "mundo", "https://cnnespanol.cnn.com/feed/"),
]

POR_MEDIO = 12          # titulares máximos por medio
HORAS_MAX = 48          # descarta noticias más viejas que esto
TOTAL_MAX = 150         # total de titulares guardados

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"


def limpiar(s, largo=None):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    if largo and len(s) > largo:
        s = s[: largo - 1].rsplit(" ", 1)[0] + "…"
    return s


def fecha(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def texto(el, *tags):
    for t in tags:
        x = el.find(t)
        if x is not None and (x.text or "").strip():
            return x.text.strip()
    return ""


def parsear(data, fuente, region):
    root = ET.fromstring(data)
    items = root.findall(".//item") or root.findall(f".//{ATOM}entry")
    out = []
    for it in items:
        titulo = limpiar(texto(it, "title", f"{ATOM}title"))
        link = texto(it, "link")
        if not link:
            a = it.find(f"{ATOM}link")
            link = a.get("href", "") if a is not None else ""
        if not titulo or not link:
            continue
        d = fecha(texto(it, "pubDate", f"{DC}date", f"{ATOM}published", f"{ATOM}updated"))
        out.append({
            "titulo": titulo,
            "link": link.strip(),
            "fuente": fuente,
            "region": region,
            "fecha": d.isoformat() if d else None,
            "resumen": limpiar(texto(it, "description", f"{ATOM}summary"), 220),
        })
        if len(out) >= POR_MEDIO:
            break
    return out


def bajar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (asistente-noticias)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def main():
    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(hours=HORAS_MAX)
    todos, vistos = [], set()
    for fuente, region, url in FEEDS:
        try:
            items = parsear(bajar(url), fuente, region)
            print(f"OK    {fuente}: {len(items)} titulares")
        except Exception as e:
            print(f"FALLA {fuente}: {e}")
            continue
        for i in items:
            clave = re.sub(r"\W+", "", i["titulo"].lower())
            if clave in vistos:
                continue
            if i["fecha"] and datetime.fromisoformat(i["fecha"]) < limite:
                continue
            vistos.add(clave)
            todos.append(i)

    todos.sort(key=lambda i: i["fecha"] or "", reverse=True)
    if not todos:
        raise SystemExit("No se pudo leer ningún medio; se conserva el archivo anterior.")
    with open("noticias.json", "w", encoding="utf-8") as f:
        json.dump({"actualizado": ahora.isoformat(), "items": todos[:TOTAL_MAX]}, f, ensure_ascii=False)
    print(f"Guardados {min(len(todos), TOTAL_MAX)} titulares.")


if __name__ == "__main__":
    main()
