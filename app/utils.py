import os
import re
import shutil
from typing import Tuple

import humanize

from .config import STORAGE_DIR


def pretty_size(num_bytes: int) -> str:
    try:
        return humanize.naturalsize(num_bytes, binary=True)
    except Exception:
        # fallback
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num_bytes < 1024:
                return f"{num_bytes:.1f}{unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f}PB"


SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_name(name: str, default: str = "file") -> str:
    name = (name or "").strip()
    if not name:
        name = default
    name = name.replace("\\", "_").replace("/", "_")
    name = SAFE_NAME_RE.sub("_", name)
    name = name.strip("._ ") or default
    return name[:200]


def ensure_dir(rel_path: str = "") -> str:
    base = STORAGE_DIR
    target = os.path.normpath(os.path.join(base, rel_path))
    if not target.startswith(os.path.normpath(base)):
        raise ValueError("Invalid path")
    os.makedirs(target, exist_ok=True)
    return target


def resolve_path(rel_path: str) -> str:
    base = os.path.normpath(STORAGE_DIR)
    target = os.path.normpath(os.path.join(base, rel_path))
    if not target.startswith(base):
        raise ValueError("Invalid path")
    return target


def disk_usage() -> Tuple[int, int, int]:
    # total, used, free
    du = shutil.disk_usage(STORAGE_DIR)
    return du.total, du.used, du.free
