"""
Junta titulares de varios medios (RSS), descarta lo que no interesa (horóscopo, quiniela,
chimentos), clasifica por sección y arma un ranking de lo más destacado.
Lo ejecuta GitHub Actions cada 30 minutos. No usa IA ni librerías externas.

Secciones: general (último momento), economia, deportes, ciencia, espectaculos (cine y TV).

Para agregar o quitar medios, editá FEEDS:
  (medio, región "local"/"ar"/"mundo", [direcciones RSS], página principal o None, sección fija o None)
"""
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FEEDS = [
    # --- Comodoro / Chubut ---
    ("El Patagónico", "local", ["https://www.elpatagonico.com/rss/pages/home.xml", "https://www.elpatagonico.com/rss"], "https://www.elpatagonico.com", None),
    ("ADNSUR", "local", ["https://www.adnsur.com.ar/rss/pages/home.xml", "https://www.adnsur.com.ar/rss"], "https://www.adnsur.com.ar", None),
    # --- Argentina: portadas ---
    ("Infobae", "ar", ["https://www.infobae.com/arc/outboundfeeds/rss/"], "https://www.infobae.com", None),
    ("Clarín", "ar", ["https://www.clarin.com/rss/lo-ultimo/"], "https://www.clarin.com", None),
    ("La Nación", "ar", ["https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml"], "https://www.lanacion.com.ar", None),
    ("Página/12", "ar", ["https://www.pagina12.com.ar/arc/outboundfeeds/rss/portada"], "https://www.pagina12.com.ar", None),
    ("Perfil", "ar", ["https://www.perfil.com/feed"], "https://www.perfil.com", None),
    # --- Argentina: secciones (si alguna dirección no anda, se ignora) ---
    ("Ámbito", "ar", ["https://www.ambito.com/rss/pages/home.xml"], "https://www.ambito.com", "economia"),
    ("Clarín", "ar", ["https://www.clarin.com/rss/economia/"], None, "economia"),
    ("La Nación", "ar", ["https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml"], None, "economia"),
    ("Clarín", "ar", ["https://www.clarin.com/rss/deportes/"], None, "deportes"),
    ("Olé", "ar", ["https://www.ole.com.ar/rss/ultimas-noticias/", "https://www.ole.com.ar/rss/"], "https://www.ole.com.ar", "deportes"),
    ("La Nación", "ar", ["https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/deportes/?outputType=xml"], None, "deportes"),
    ("Clarín", "ar", ["https://www.clarin.com/rss/tecnologia/"], None, "ciencia"),
    ("La Nación", "ar", ["https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/ciencia/?outputType=xml"], None, "ciencia"),
    ("Clarín", "ar", ["https://www.clarin.com/rss/espectaculos/"], None, "espectaculos"),
    ("La Nación", "ar", ["https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/espectaculos/?outputType=xml"], None, "espectaculos"),
    # --- Mundo ---
    ("BBC Mundo", "mundo", ["https://feeds.bbci.co.uk/mundo/rss.xml"], "https://www.bbc.com/mundo", None),
    ("DW Español", "mundo", ["https://rss.dw.com/xml/rss-sp-all"], "https://www.dw.com/es", None),
    ("France 24", "mundo", ["https://www.france24.com/es/rss"], "https://www.france24.com/es/", None),
    ("El País", "mundo", ["https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"], "https://elpais.com", None),
    ("El País", "mundo", ["https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada"], None, "ciencia"),
]

POR_MEDIO = 30          # titulares máximos por canal
HORAS_MAX = 48          # descarta noticias más viejas que esto
TOTAL_MAX = 500         # titulares guardados para búsquedas por tema
TOP_GENERAL = 40        # temas destacados (último momento)
TOP_SECCION = 15        # temas destacados por sección

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"


# ---------- Utilidades ----------
def limpiar(s, largo=None):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    if largo and len(s) > largo:
        s = s[: largo - 1].rsplit(" ", 1)[0] + "…"
    return s


def sin_tildes(s):
    s = s.lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u")):
        s = s.replace(a, b)
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


# ---------- Filtro y clasificación ----------
# Fuera del todo
EXCLUIR = re.compile(
    r"horoscop|astrolog|\bsignos?\b|zodiaco|tarot|numerolog|\bquiniela|loteria|\bquini ?6|\bloto\b|brinco|telekino|"
    r"wordle|crucigrama|resultados del sorteo|predicciones (de|para) (hoy|la semana)", re.I)
EXCLUIR_URL = re.compile(r"/(horoscopo|astrologia|quiniela|loterias?|juegos|crucigramas?)/", re.I)
# Chimentos / famosos: fuera, salvo que sea de cine o TV
CHIMENTO_URL = re.compile(r"/(famosos|fama|celebrities|chimentos|gente|realities?|personajes)/", re.I)
CINE_TV = re.compile(
    r"\b(cine|pelicula|peliculas|film|series de tv|series|netflix|hbo|disney|prime video|star\+|paramount|apple tv|"
    r"estreno|estrenos|taquilla|oscar|oscars|globo de oro|emmy|cannes|festival de cine|cineasta|actor|actriz|"
    r"elenco|nueva temporada|television|televisivo|tv|telefe|el trece|eltrece|america tv|canal 9|tv publica|rating|"
    r"telenovela|ficcion|documental|animacion|pixar|marvel|streaming|guion|rodaje|trailer)\b", re.I)
LIVIANAS = re.compile(r"/(recetas|gastronomia|cocina|tendencias|viajes|moda|mascotas|virales?|estilo|lifestyle|bienestar)/", re.I)

SECCIONES = {
    "deportes": (re.compile(r"/(deportes?|futbol|ole|tenis|rugby|basquet|automovilismo|formula-1)/", re.I),
                 re.compile(r"\b(futbol|seleccion argentina|scaloni|messi|boca|river|racing|independiente|san lorenzo|"
                            r"huracan|estudiantes|velez|talleres|belgrano|newell|rosario central|libertadores|sudamericana|"
                            r"liga profesional|copa (del mundo|america|argentina)|mundial|gol|goles|hincha|tenis|"
                            r"roland garros|wimbledon|us open|rugby|los pumas|basquet|nba|formula 1|f1|colapinto|"
                            r"motogp|dakar|boxeo|ufc|juegos olimpicos|olimpiadas|atletismo|hockey|las leonas|dt|tecnico de)\b")),
    "economia": (re.compile(r"/(economia|finanzas|mercados|negocios|dolar|campo|rural|empresas)/", re.I),
                 re.compile(r"\b(dolar|blue|inflacion|indec|bcra|banco central|fmi|riesgo pais|bonos|merval|"
                            r"wall street|tasas?|plazo fijo|tarifas?|salarios?|paritarias?|jubilaciones?|aguinaldo|"
                            r"impuestos?|ganancias|iva|arca|afip|recaudacion|pbi|recesion|exportaciones|importaciones|"
                            r"petroleo|vaca muerta|ypf|presupuesto|deficit|superavit|cepo|devaluacion|cotiza|cotizacion|"
                            r"precios|canasta basica|desempleo|economia|economico|mercados|inversiones?|crypto|bitcoin)\b")),
    "ciencia": (re.compile(r"/(ciencia|tecnologia|salud|medio-ambiente|ambiente|espacio|science|tecno)/", re.I),
                re.compile(r"\b(cientificos?|ciencia|cientific[oa]|estudio revela|nasa|conicet|"
                           r"espacial|planeta|marte|asteroide|cometa|telescopio|astronomos?|galaxia|fosil|"
                           r"dinosaurio|nueva especie|genetic[oa]|adn|vacuna|cancer|alzheimer|inteligencia artificial|"
                           r"\bia\b|chatgpt|robot|cuantic[oa]|cambio climatico|descubr\w+|satelite|cohete|spacex)\b")),
    "espectaculos": (re.compile(r"/(espectaculos|cine|series|television|tv|cultura|show)/", re.I), CINE_TV),
}


def clasificar(it, fija):
    """Devuelve la sección del titular, o None si hay que descartarlo."""
    t, url = sin_tildes(it["titulo"]), it["link"]
    if EXCLUIR.search(t) or EXCLUIR_URL.search(url):
        return None
    es_cine_tv = bool(CINE_TV.search(t))
    if CHIMENTO_URL.search(url) and not es_cine_tv:
        return None
    if fija:
        if fija == "espectaculos" and not es_cine_tv:
            return None                     # en espectáculos solo cine y TV
        return fija
    for sec, (rx_url, rx_tit) in SECCIONES.items():
        if rx_url.search(url):
            if sec == "espectaculos" and not es_cine_tv:
                return None
            return sec
    for sec, (rx_url, rx_tit) in SECCIONES.items():
        if rx_tit.search(t):
            return sec
    return "general"


# ---------- Lectura de los RSS ----------
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
            "pos": len(out),  # posición en el RSS (0 = primera)
        })
        if len(out) >= POR_MEDIO:
            break
    return out


def bajar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (asistente-noticias)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def buscar_rss(home):
    """Entra a la página principal del medio y busca la dirección de su RSS."""
    pagina = bajar(home).decode("utf-8", "ignore")
    urls = []
    for tag in re.findall(r"<link[^>]+>", pagina, re.I):
        if re.search(r"application/(rss|atom)\+xml", tag, re.I):
            m = re.search(r'href=["\']([^"\']+)', tag, re.I)
            if m:
                urls.append(urllib.parse.urljoin(home, html.unescape(m.group(1))))
    return urls


def leer_medio(fuente, region, urls, home):
    probadas = set()
    for url in urls:
        probadas.add(url)
        try:
            items = parsear(bajar(url), fuente, region)
            if items:
                return items, url
        except Exception:
            pass
    if home:                                   # plan B: buscar el RSS en la portada
        for url in buscar_rss(home):
            if url in probadas:
                continue
            try:
                items = parsear(bajar(url), fuente, region)
                if items:
                    return items, url + "  (encontrado en la portada: conviene copiarlo en FEEDS)"
            except Exception:
                pass
    raise RuntimeError("no se encontró un RSS que funcione")


# ---------- Ranking de destacadas (sin IA) ----------
# Un tema es importante cuando lo cubren varios medios a la vez.
STOP = set("""a al algo ante antes aqui asi aun bajo bien cada como con contra cual cuando de del desde donde dos
el ella ellas ellos en entre era es esa ese eso esta este esto estos fue fueron ha hace hacia han hasta hay
la las le les lo los mas me mientras muy ni no nos o otra otro para pero poco por porque que quien se ser si
sin sobre son su sus tambien tan tiene todo tras tu un una uno unos y ya hoy ayer manana dia dias nuevo nueva
anos ano segun dijo despues durante luego vez veces mismo misma solo puede pueden video fotos mira quienes
cuanto cuales tres cuatro cinco""".split())


def tokens(titulo):
    palabras = re.findall(r"[a-zñ0-9]+", sin_tildes(titulo))
    return {p[:6] for p in palabras if len(p) >= 4 and p not in STOP}


def similares(a, b):
    comunes = a & b
    return len(comunes) >= 2 and len(comunes) / max(1, min(len(a), len(b))) >= 0.45


def destacadas(items, ahora):
    grupos = []
    for it in sorted(items, key=lambda i: i["fecha"] or "", reverse=True):
        tk = tokens(it["titulo"])
        if len(tk) < 2:
            continue
        for g in grupos:
            if it["fuente"] not in g["fuentes"] and similares(tk, g["tokens"]):
                g["items"].append(it); g["fuentes"].add(it["fuente"]); g["tokens"] |= tk
                break
        else:
            grupos.append({"items": [it], "fuentes": {it["fuente"]}, "tokens": set(tk)})

    salida = []
    for g in grupos:
        its, n = g["items"], len(g["fuentes"])
        principal = min(its, key=lambda i: i.get("pos", 99))
        fechas = [datetime.fromisoformat(i["fecha"]) for i in its if i["fecha"]]
        horas = (ahora - max(fechas)).total_seconds() / 3600 if fechas else 12
        puntaje = (n - 1) * 4 + max(0, 3 - principal.get("pos", 30) * 0.25) - min(horas, 36) * 0.12
        if any(LIVIANAS.search(i["link"]) for i in its):
            puntaje -= 5
        secs = [i["categoria"] for i in its]
        salida.append({
            "titulo": principal["titulo"], "link": principal["link"], "fuente": principal["fuente"],
            "fecha": max(fechas).isoformat() if fechas else None, "resumen": principal.get("resumen", ""),
            "medios": sorted(g["fuentes"]), "cantidad": n, "regiones": sorted({i["region"] for i in its}),
            "categoria": max(set(secs), key=secs.count), "puntaje": round(puntaje, 2),
            "otros": [{"fuente": i["fuente"], "link": i["link"]} for i in its if i is not principal],
        })
    salida.sort(key=lambda g: g["puntaje"], reverse=True)
    return salida


def elegir(top, cupo_total, cupo_region=12):
    """Los mejores temas, asegurando que haya de Comodoro, Argentina y Mundo."""
    elegidos, ids = [], set()
    for reg in ("local", "ar", "mundo", None):
        cupo = cupo_total if reg is None else cupo_region
        for g in top:
            if len([x for x in elegidos if reg is None or reg in x["regiones"]]) >= cupo:
                break
            if (reg is None or reg in g["regiones"]) and g["link"] not in ids:
                elegidos.append(g); ids.add(g["link"])
    return sorted(elegidos, key=lambda g: g["puntaje"], reverse=True)


# ---------- Programa principal ----------
def main():
    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(hours=HORAS_MAX)
    todos, vistos, descartados = [], set(), 0
    for fuente, region, urls, home, fija in FEEDS:
        etiqueta = f"{fuente}{' · ' + fija if fija else ''}"
        try:
            items, usada = leer_medio(fuente, region, urls, home)
            print(f"OK    {etiqueta}: {len(items)} titulares  <- {usada}")
        except Exception as e:
            print(f"FALLA {etiqueta}: {e}")
            continue
        for i in items:
            clave = re.sub(r"\W+", "", i["titulo"].lower())
            if clave in vistos or i["link"] in vistos:
                continue
            if i["fecha"] and datetime.fromisoformat(i["fecha"]) < limite:
                continue
            cat = clasificar(i, fija)
            if cat is None:
                descartados += 1
                continue
            i["categoria"] = cat
            vistos.add(clave); vistos.add(i["link"])
            todos.append(i)

    if not todos:
        raise SystemExit("No se pudo leer ningún medio; se conserva el archivo anterior.")
    todos.sort(key=lambda i: i["fecha"] or "", reverse=True)

    # En "último momento" deportes y espectáculos pesan menos (tienen su propia sección)
    general_top = destacadas(todos, ahora)
    for g in general_top:
        if g["categoria"] in ("deportes", "espectaculos"):
            g["puntaje"] = round(g["puntaje"] - 4, 2)
    general_top.sort(key=lambda g: g["puntaje"], reverse=True)
    general = elegir(general_top, TOP_GENERAL)
    secciones = {}
    for sec in ("economia", "deportes", "ciencia", "espectaculos"):
        secciones[sec] = elegir(destacadas([i for i in todos if i["categoria"] == sec], ahora), TOP_SECCION, 6)

    with open("noticias.json", "w", encoding="utf-8") as f:
        json.dump({"actualizado": ahora.isoformat(), "destacadas": general, "secciones": secciones,
                   "items": todos[:TOTAL_MAX]}, f, ensure_ascii=False)

    print(f"\nGuardados {min(len(todos), TOTAL_MAX)} titulares · descartados {descartados} (horóscopo, quiniela, chimentos).")
    print("Por sección:", {s: sum(1 for i in todos if i["categoria"] == s)
                           for s in ("general", "economia", "deportes", "ciencia", "espectaculos")})
    print("\nÚltimo momento (top 8):")
    for g in general[:8]:
        print(f"  [{g['cantidad']} medios · {g['puntaje']:>5}] {g['titulo'][:90]}")
    for sec, lista in secciones.items():
        print(f"\n{sec.capitalize()} (top 3):")
        for g in lista[:3]:
            print(f"  [{g['cantidad']} medios · {g['puntaje']:>5}] {g['titulo'][:90]}")


if __name__ == "__main__":
    main()
