# 😈 Sasuke FileBot (Pyrogram) + Web (Render)

Un bot de Telegram para **descargar archivos (links directos, Google Drive, Mediafire)** y **administrar el almacenamiento** (listar, crear carpetas, mover, borrar, comprimir a ZIP), con una **web** simple para que Render mantenga el servicio levantado (y para pings/cronjob).

## ✅ Deploy en Render
1. Sube este proyecto a GitHub.
2. Render → *New* → *Web Service* → conecta el repo.
3. Build Command: *(vacío, Render usa el Dockerfile)*
4. Environment Variables:
   - `API_ID` = tu api_id de Telegram
   - `API_HASH` = tu api_hash
   - `BOT_TOKEN` = token del bot
   - (opcional) `STORAGE_DIR` = `/app/storage`
   - (opcional) `MAX_DOWNLOAD_MB` = límite en MB (default 4096)
   - (opcional) `OWNER_ONLY` = `1` para que solo tu uses el bot
   - (opcional) `OWNER_ID` = tu user id (si OWNER_ONLY=1)

Render pondrá `PORT` automáticamente.

## 🌐 Web (para cronjob/uptime)
- `GET /` → texto
- `GET /health` → `{ok:true}`
- `GET /ping` → `{pong:true}`

Puedes usar un servicio externo de uptime/cron para hacer ping a `/ping`.

## 🤖 Comandos
- `/start` `/help`
- `/get <url> [carpeta]`
- `/ls [carpeta]`
- `/files`
- `/info <id>`
- `/rm <id>`
- `/rename <id> <nuevo_nombre>`
- `/mkdir <carpeta>`
- `/mv <id> <carpeta>`
- `/zip <carpeta> [nombre.zip]`
- `/zipid <id> [nombre.zip]`
- `/df`

## 📌 Notas
- Los IDs se asignan desde 0 y van subiendo.
- Los archivos se guardan en el storage del contenedor (en Render el disco es limitado).
