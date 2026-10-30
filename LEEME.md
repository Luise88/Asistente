# Asistente Personal — Etapa 1

App instalable (PWA) para Android: escucha tu voz, consulta a Gemini (y a Claude como respaldo) y responde hablando.

## Archivos
- index.html — la app completa
- manifest.json — datos para instalarla como app (nombre, ícono, colores)
- sw.js — permite instalarla y abrirla rápido
- icon-*.png — íconos

## Paso 1: Clave gratuita de Gemini
1. Entrá a https://aistudio.google.com con tu cuenta de Google.
2. Tocá "Get API key" → "Create API key".
3. Copiala (empieza con AQ. o AIza). Guardala, la cargás en el paso 4.

## Paso 2: Publicar en GitHub Pages
1. En GitHub: "New repository" → nombre: asistente → Public → Create.
2. "Add file" → "Upload files" → arrastrá TODOS los archivos de esta carpeta (sin la carpeta). Commit.
3. Settings → Pages → Source: "Deploy from a branch" → Branch: main / (root) → Save.
4. En 1–2 minutos queda en: https://TU-USUARIO.github.io/asistente/

## Paso 3: Instalar en el celular
1. Abrí esa dirección en Chrome (Android).
2. Menú ⋮ → "Instalar app" (o "Agregar a pantalla principal").
3. Queda el ícono del micrófono con el nombre "Asistente".

## Paso 4: Configurar
1. Abrí la app: se abre ⚙️ Ajustes automáticamente.
2. Pegá la clave de Gemini → "Probar Gemini" → debe decir ✅.
3. (Opcional) Clave de Claude como respaldo (console.anthropic.com, pago por uso).
4. Poné tu nombre, elegí la voz → Guardar.
5. Tocá 🎤 y aceptá el permiso de micrófono.

## Si algo falla
- "Gemini 404 / model not found": cambiá el modelo en Ajustes (ej. gemini-3.5-flash-lite).
- "Gemini 429": se alcanzó el límite gratuito del momento; si cargaste Claude, responde Claude.
- El micrófono no anda: Chrome → ⋮ → Configuración → Configuración de sitios → Micrófono → permitir tu sitio.
- No ves los cambios después de actualizar archivos: cerrá y abrí la app dos veces.

## Seguridad
Las claves quedan guardadas solo en tu teléfono (no en GitHub). No compartas la dirección con la app ya configurada en otro dispositivo sin cargar sus propias claves.
