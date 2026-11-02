"""
Lee las alertas oficiales del Servicio Meteorológico Nacional (formato CAP)
y las guarda en alertas.json. Lo ejecuta GitHub Actions junto con noticias.py.
La app filtra las alertas por tu zona (⚙️ Ajustes → "Zona para alertas del SMN").
No usa IA ni librerías externas.
"""
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEED = "https://ssl.smn.gob.ar/CAP/AR.php"
MAX_ARCHIVOS = 60


def bajar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (asistente-alertas)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def local(tag):
    return tag.split("}")[-1]


def hijo(el, nombre):
    for c in el:
        if local(c.tag) == nombre:
            return (c.text or "").strip()
    return ""


def hijos(el, nombre):
    return [c for c in el if local(c.tag) == nombre]


def leer_cap(root):
    """Devuelve las alertas de cualquier documento que contenga elementos <alert> de CAP."""
    out = []
    alertas = [root] if local(root.tag) == "alert" else [e for e in root.iter() if local(e.tag) == "alert"]
    for al in alertas:
        if hijo(al, "msgType") == "Cancel":
            continue
        for info in hijos(al, "info"):
            areas = [hijo(a, "areaDesc") for a in hijos(info, "area")]
            nivel = ""
            for p in hijos(info, "parameter"):
                if "nivel" in hijo(p, "valueName").lower() or "color" in hijo(p, "valueName").lower():
                    nivel = hijo(p, "value")
            out.append({
                "evento": hijo(info, "event"),
                "titulo": hijo(info, "headline") or hijo(info, "event"),
                "descripcion": hijo(info, "description")[:600],
                "severidad": hijo(info, "severity"),
                "nivel": nivel,
                "areas": "; ".join(a for a in areas if a),
                "desde": hijo(info, "onset") or hijo(info, "effective") or hijo(al, "sent"),
                "hasta": hijo(info, "expires"),
            })
    return out


def enlaces(root):
    links = []
    for e in root.iter():
        n = local(e.tag)
        if n == "link":
            href = e.get("href") or (e.text or "").strip()
            if href:
                links.append(href)
        elif n == "enclosure" and e.get("url"):
            links.append(e.get("url"))
    return [l for l in dict.fromkeys(links) if l != FEED]


def main():
    ahora = datetime.now(timezone.utc).isoformat()
    try:
        root = ET.fromstring(bajar(FEED))
        print("Formato del canal:", local(root.tag))
        alertas = leer_cap(root)
        if not alertas:
            links = enlaces(root)
            print(f"Enlaces encontrados: {len(links)}", links[:3])
            for url in links[:MAX_ARCHIVOS]:
                try:
                    alertas += leer_cap(ET.fromstring(bajar(url)))
                except Exception as e:
                    print("  no se pudo leer", url, "-", e)
        vistos, unicas = set(), []
        for a in alertas:
            k = (a["evento"], a["titulo"], a["areas"], a["hasta"])
            if k not in vistos:
                vistos.add(k)
                unicas.append(a)
        datos = {"actualizado": ahora, "ok": True, "fuente": FEED, "alertas": unicas}
        print(f"OK: {len(unicas)} alertas")
    except Exception as e:
        print("FALLA al leer el SMN:", e)
        datos = {"actualizado": ahora, "ok": False, "error": str(e), "alertas": []}
    with open("alertas.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
