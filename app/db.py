import json
import os
import threading
from typing import Dict, Any, Optional

from .config import DB_PATH, STORAGE_DIR

_lock = threading.Lock()

DEFAULT_DB: Dict[str, Any] = {
    "next_id": 0,
    # id(str) -> {"path": str, "name": str, "size": int}
    "items": {},
}


def _ensure_base() -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)


def load_db() -> Dict[str, Any]:
    _ensure_base()
    if not os.path.exists(DB_PATH):
        save_db(DEFAULT_DB)
        return dict(DEFAULT_DB)
    with _lock:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = dict(DEFAULT_DB)
    data.setdefault("next_id", 0)
    data.setdefault("items", {})
    return data


def save_db(data: Dict[str, Any]) -> None:
    _ensure_base()
    tmp = DB_PATH + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DB_PATH)


def alloc_id() -> int:
    db = load_db()
    new_id = int(db.get("next_id", 0))
    db["next_id"] = new_id + 1
    save_db(db)
    return new_id


def put_item(item_id: int, path: str, name: str, size: int) -> None:
    db = load_db()
    db["items"][str(item_id)] = {"path": path, "name": name, "size": int(size)}
    save_db(db)


def get_item(item_id: int) -> Optional[Dict[str, Any]]:
    db = load_db()
    return db.get("items", {}).get(str(item_id))


def del_item(item_id: int) -> bool:
    db = load_db()
    items = db.get("items", {})
    if str(item_id) in items:
        del items[str(item_id)]
        save_db(db)
        return True
    return False


def list_items(prefix_path: str = "") -> Dict[str, Any]:
    db = load_db()
    items = db.get("items", {})
    if not prefix_path:
        return items
    out = {}
    prefix_path = os.path.normpath(prefix_path)
    for k, v in items.items():
        p = os.path.normpath(v.get("path", ""))
        if p.startswith(prefix_path):
            out[k] = v
    return out
