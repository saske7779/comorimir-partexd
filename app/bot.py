import asyncio
import os
import re
from datetime import datetime
from typing import Optional

from pyrogram import Client, filters


proxy = dict(
    scheme="http",
    hostname="154.3.236.202",
    port=3128
)

from pyrogram.types import Message

from .config import API_ID, API_HASH, BOT_TOKEN, STORAGE_DIR, OWNER_ONLY, OWNER_ID
from .db import alloc_id, put_item, get_item, del_item
from .downloader import download_file, is_google_drive, is_mediafire
from .fileops import list_dir, make_dir, zip_folder, zip_file, rename_rel, delete_rel
from .utils import ensure_dir, pretty_size, safe_name, disk_usage

BANNER = """😈 *Sasuke FileBot*

✅ Bot + Web activos en Render.
📌 Comandos: /help
"""

HELP = """😈 *Sasuke FileBot - Ayuda*

*Descargar*
• `/get <url> [carpeta]` descarga un link (directo, Drive, Mediafire)
• Envia un archivo de Telegram y lo guardo en el storage

*Archivos*
• `/ls [carpeta]` lista archivos/carpetas con tamaño
• `/files` lista todos los archivos guardados por ID
• `/info <id>` info de un archivo
• `/rm <id>` borrar archivo
• `/rename <id> <nuevo_nombre>` renombrar
• `/mkdir <carpeta>` crear carpeta
• `/mv <id> <carpeta>` mover archivo a carpeta

*Compresión*
• `/zip <carpeta> [nombre.zip]` comprime carpeta a ZIP
• `/zipid <id> [nombre.zip]` comprime un archivo a ZIP

*Sistema*
• `/df` uso de disco

Notas:
• Los IDs empiezan en 0 y van subiendo.
• Las rutas son relativas al storage del bot.
"""


def owner_guard():
    if not OWNER_ONLY:
        return filters.all
    return filters.user(OWNER_ID)


def _resolve_rel(folder_rel: str) -> str:
    folder_rel = (folder_rel or "").strip().strip("/")
    ensure_dir(folder_rel)
    return folder_rel


def _unique_name(folder_abs: str, base_name: str) -> str:
    base_name = safe_name(base_name, default="download")
    name = base_name
    stem, ext = os.path.splitext(base_name)
    i = 1
    while os.path.exists(os.path.join(folder_abs, name)):
        name = f"{stem}_{i}{ext}"
        i += 1
    return name


async def _progress_message(msg: Message, prefix: str, wrote: int, total: Optional[int]):
    if total:
        pct = (wrote / total) * 100
        text = f"{prefix}\n📥 {pretty_size(wrote)} / {pretty_size(total)} ({pct:.1f}%)"
    else:
        text = f"{prefix}\n📥 {pretty_size(wrote)}"
    # edit at most ~1/sec
    now = asyncio.get_running_loop().time()
    last = getattr(msg, "_last_edit", 0.0)
    if now - last >= 1.0:
        try:
            await msg.edit_text(text)
            msg._last_edit = now
        except Exception:
            pass


app = Client(
    "sasuke_filebot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
, proxy=proxy)


@app.on_message(filters.command(["start"]) & owner_guard())
async def start_cmd(_, message: Message):
    await message.reply_text(BANNER, disable_web_page_preview=True)


@app.on_message(filters.command(["help"]) & owner_guard())
async def help_cmd(_, message: Message):
    await message.reply_text(HELP, disable_web_page_preview=True)


@app.on_message(filters.command(["df"]) & owner_guard())
async def df_cmd(_, message: Message):
    total, used, free = disk_usage()
    await message.reply_text(
        f"🧠 *Disco*\n"
        f"• Total: {pretty_size(total)}\n"
        f"• Usado: {pretty_size(used)}\n"
        f"• Libre: {pretty_size(free)}",
        disable_web_page_preview=True,
    )


@app.on_message(filters.command(["mkdir"]) & owner_guard())
async def mkdir_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Uso: `/mkdir <carpeta>`", quote=True)
    folder = " ".join(message.command[1:]).strip()
    try:
        rel = make_dir(folder)
        await message.reply_text(f"📁 Carpeta creada: `{rel}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")


@app.on_message(filters.command(["ls"]) & owner_guard())
async def ls_cmd(_, message: Message):
    rel = " ".join(message.command[1:]).strip() if len(message.command) > 1 else ""
    rel = _resolve_rel(rel)
    try:
        entries = list_dir(rel)
        if not entries:
            return await message.reply_text(f"📂 `{rel or '.'}` está vacío.")
        lines = [f"📂 *Listado:* `{rel or '.'}`\n"]
        for name, rp, size_b, is_dir in entries[:60]:
            icon = "📁" if is_dir else "📄"
            lines.append(f"{icon} `{name}`  •  {pretty_size(size_b)}")
        if len(entries) > 60:
            lines.append(f"\n…y {len(entries)-60} más")
        await message.reply_text("\n".join(lines), disable_web_page_preview=True)
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")


@app.on_message(filters.command(["files"]) & owner_guard())
async def files_cmd(_, message: Message):
    from .db import load_db

    db = load_db()
    items = db.get("items", {})
    if not items:
        return await message.reply_text("📦 No hay archivos guardados todavía.")
    lines = ["📦 *Archivos por ID:*\n"]
    # sort numeric
    for k in sorted(items.keys(), key=lambda x: int(x)):
        v = items[k]
        p = v.get("path", "")
        name = v.get("name", os.path.basename(p))
        size_b = int(v.get("size", 0))
        lines.append(f"• *{k}* → `{name}`  ({pretty_size(size_b)})")
        if len(lines) >= 70:
            lines.append("\n…lista cortada (demasiados items)")
            break
    await message.reply_text("\n".join(lines), disable_web_page_preview=True)


@app.on_message(filters.command(["info"]) & owner_guard())
async def info_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Uso: `/info <id>`")
    try:
        item_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID inválido")
    item = get_item(item_id)
    if not item:
        return await message.reply_text("❌ No existe ese ID")
    path = item.get("path", "")
    abs_path = os.path.join(STORAGE_DIR, path)
    exists = os.path.exists(abs_path)
    await message.reply_text(
        "🧾 *Info*\n"
        f"• ID: *{item_id}*\n"
        f"• Nombre: `{item.get('name','')}`\n"
        f"• Ruta: `{path}`\n"
        f"• Tamaño: {pretty_size(int(item.get('size',0)))}\n"
        f"• Existe: {'✅' if exists else '❌'}",
        disable_web_page_preview=True,
    )


@app.on_message(filters.command(["rm"]) & owner_guard())
async def rm_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Uso: `/rm <id>`")
    try:
        item_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID inválido")
    item = get_item(item_id)
    if not item:
        return await message.reply_text("❌ No existe ese ID")
    try:
        delete_rel(item["path"])
    except Exception:
        pass
    del_item(item_id)
    await message.reply_text(f"🗑️ Borrado ID *{item_id}*.")


@app.on_message(filters.command(["rename"]) & owner_guard())
async def rename_cmd(_, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("❌ Uso: `/rename <id> <nuevo_nombre>`")
    try:
        item_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID inválido")
    new_name = " ".join(message.command[2:]).strip()
    item = get_item(item_id)
    if not item:
        return await message.reply_text("❌ No existe ese ID")
    try:
        new_rel = rename_rel(item["path"], new_name)
        # update DB size/name/path
        abs_path = os.path.join(STORAGE_DIR, new_rel)
        put_item(item_id, new_rel, os.path.basename(new_rel), os.path.getsize(abs_path))
        await message.reply_text(f"✏️ Renombrado: *{item_id}* → `{os.path.basename(new_rel)}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")


@app.on_message(filters.command(["mv"]) & owner_guard())
async def mv_cmd(_, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("❌ Uso: `/mv <id> <carpeta>`")
    try:
        item_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID inválido")
    folder_rel = " ".join(message.command[2:]).strip()
    folder_rel = _resolve_rel(folder_rel)
    item = get_item(item_id)
    if not item:
        return await message.reply_text("❌ No existe ese ID")
    try:
        src_rel = item["path"]
        dst_abs_folder = os.path.join(STORAGE_DIR, folder_rel)
        os.makedirs(dst_abs_folder, exist_ok=True)
        dst_name = os.path.basename(src_rel)
        dst_rel = os.path.join(folder_rel, dst_name) if folder_rel else dst_name
        # unique if already exists
        dst_abs = os.path.join(STORAGE_DIR, dst_rel)
        if os.path.exists(dst_abs):
            stem, ext = os.path.splitext(dst_name)
            i = 1
            while os.path.exists(os.path.join(dst_abs_folder, f"{stem}_{i}{ext}")):
                i += 1
            dst_name = f"{stem}_{i}{ext}"
            dst_rel = os.path.join(folder_rel, dst_name) if folder_rel else dst_name
        os.makedirs(os.path.dirname(os.path.join(STORAGE_DIR, dst_rel)), exist_ok=True)
        os.replace(os.path.join(STORAGE_DIR, src_rel), os.path.join(STORAGE_DIR, dst_rel))
        put_item(item_id, dst_rel, dst_name, os.path.getsize(os.path.join(STORAGE_DIR, dst_rel)))
        await message.reply_text(f"📦 Movido ID *{item_id}* → `{folder_rel or '.'}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")


@app.on_message(filters.command(["zip"]) & owner_guard())
async def zip_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Uso: `/zip <carpeta> [nombre.zip]`")
    folder = message.command[1].strip()
    zipname = message.command[2].strip() if len(message.command) >= 3 else f"{safe_name(folder, 'folder')}.zip"
    try:
        folder_rel = _resolve_rel(folder)
        zip_rel = zip_folder(folder_rel, zipname)
        abs_zip = os.path.join(STORAGE_DIR, zip_rel)
        zid = alloc_id()
        put_item(zid, zip_rel, os.path.basename(zip_rel), os.path.getsize(abs_zip))
        await message.reply_text(
            f"🗜️ ZIP creado: `{zip_rel}`\n"
            f"🆔 ID: *{zid}*  •  {pretty_size(os.path.getsize(abs_zip))}"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")


@app.on_message(filters.command(["zipid"]) & owner_guard())
async def zipid_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Uso: `/zipid <id> [nombre.zip]`")
    try:
        item_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID inválido")
    item = get_item(item_id)
    if not item:
        return await message.reply_text("❌ No existe ese ID")
    zipname = message.command[2].strip() if len(message.command) >= 3 else f"{safe_name(item.get('name','file'), 'file')}.zip"
    try:
        zip_rel = zip_file(item["path"], zipname)
        abs_zip = os.path.join(STORAGE_DIR, zip_rel)
        zid = alloc_id()
        put_item(zid, zip_rel, os.path.basename(zip_rel), os.path.getsize(abs_zip))
        await message.reply_text(
            f"🗜️ ZIP creado: `{zip_rel}`\n"
            f"🆔 ID: *{zid}*  •  {pretty_size(os.path.getsize(abs_zip))}"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

@app.on_message(filters.command(["up"]) & owner_guard())

@app.on_message(filters.command(["up"]) & owner_guard())
async def up_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Uso: `/up <id>`")

    try:
        item_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ID inválido")

    item = get_item(item_id)
    if not item:
        return await message.reply_text("❌ No existe ese ID")

    rel_path = item.get("path", "")
    abs_path = os.path.join(STORAGE_DIR, rel_path)

    if not os.path.exists(abs_path):
        return await message.reply_text("❌ El archivo no existe en el storage")

    await message.reply_document(
        document=abs_path,
        caption=f"⬆️ Subido ID *{item_id}*: `{os.path.basename(abs_path)}`",
        quote=True
    )
