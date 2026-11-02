# Asistente Personal — Etapas 1 y 2

App instalable (PWA) para Android: escucha tu voz, consulta a Gemini (y a Claude como respaldo) y responde hablando.

## Archivos
- index.html — la app completa
- manifest.json, sw.js, icon-*.png — instalación como app
- noticias.py — junta titulares de medios (GitHub lo corre cada 30 min)
- alertas.py — lee las alertas oficiales del SMN (corre junto con las noticias)
- noticias.json, alertas.json — datos guardados (se actualizan solos)
- .github/workflows/noticias.yml — tarea programada de GitHub (crearla a mano)

## Usar
- Botones: 🌅 Mi día · ☀️ Clima · 🌊 Mar · 📰 Noticias · 🇦🇷 Argentina · 🌍 Mundo
- Pedido simple ("clima", "mar", "viento") → tarjeta completa, sin IA.
- Pregunta puntual ("¿va a haber viento a la tarde?", "¿cómo va a estar el mar mañana a las 16?")
  → Gemini responde usando los datos reales de pronóstico, mar y alertas.
- Cualquier otra cosa la responde la IA.

## Fuentes
- Clima, viento, ráfagas, sol, UV: Open-Meteo (gratis)
- Olas, temperatura del agua, mareas estimadas: Open-Meteo Marine (gratis)
- Alertas oficiales: SMN (ssl.smn.gob.ar/CAP/AR.php), filtradas por "Zona para alertas" en Ajustes
- Alertas propias: ráfagas ≥ 60 km/h, lluvia ≥ 70 %, heladas, calculadas del pronóstico
- Noticias: Infobae, Clarín, La Nación, Página/12, Ámbito, Perfil, BBC Mundo, DW, France 24, El País, CNN Español

## Importante sobre las mareas
Son estimadas por un modelo: los horarios son aproximados y las alturas están medidas
respecto al nivel medio del mar (no coinciden con las tablas oficiales). Para pesca o
navegación, verificar en la tabla oficial (enlace configurable en Ajustes).
