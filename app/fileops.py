import os
import shutil
import zipfile
from typing import List, Tuple

from .utils import safe_name, ensure_dir, resolve_path


def list_dir(rel_path: str = "") -> List[Tuple[str, str, int, bool]]:
    """Return list of (name, relpath, size_bytes, is_dir)."""
    abs_p = ensure_dir(rel_path)
    out: List[Tuple[str, str, int, bool]] = []
    for name in sorted(os.listdir(abs_p)):
        ap = os.path.join(abs_p, name)
        rp = os.path.relpath(ap, ensure_dir(""))
        if os.path.isdir(ap):
            out.append((name, rp, dir_size(ap), True))
        else:
            out.append((name, rp, os.path.getsize(ap), False))
    return out


def dir_size(path: str) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def make_dir(rel_path: str) -> str:
    rel_path = rel_path.strip().strip("/")
    if not rel_path:
        raise ValueError("Folder name required")
    # sanitize each component
    parts = [safe_name(p, default="folder") for p in rel_path.split("/") if p]
    safe_rel = "/".join(parts)
    ensure_dir(safe_rel)
    return safe_rel


def move_rel(src_rel: str, dst_rel: str) -> Tuple[str, str]:
    src_abs = resolve_path(src_rel)
    dst_abs = resolve_path(dst_rel)
    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
    shutil.move(src_abs, dst_abs)
    return src_rel, dst_rel


def delete_rel(rel_path: str) -> None:
    abs_p = resolve_path(rel_path)
    if os.path.isdir(abs_p):
        shutil.rmtree(abs_p)
    else:
        os.remove(abs_p)


def zip_folder(folder_rel: str, zip_rel: str) -> str:
    folder_abs = resolve_path(folder_rel)
    if not os.path.isdir(folder_abs):
        raise ValueError("Not a folder")

    zip_rel = zip_rel.strip().strip("/")
    if not zip_rel.endswith(".zip"):
        zip_rel += ".zip"
    zip_abs = resolve_path(zip_rel)
    os.makedirs(os.path.dirname(zip_abs), exist_ok=True)

    with zipfile.ZipFile(zip_abs, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_abs):
            for fn in files:
                fp = os.path.join(root, fn)
                arc = os.path.relpath(fp, folder_abs)
                zf.write(fp, arcname=arc)
    return zip_rel


def zip_file(file_rel: str, zip_rel: str) -> str:
    file_abs = resolve_path(file_rel)
    if not os.path.isfile(file_abs):
        raise ValueError("Not a file")

    zip_rel = zip_rel.strip().strip("/")
    if not zip_rel.endswith(".zip"):
        zip_rel += ".zip"
    zip_abs = resolve_path(zip_rel)
    os.makedirs(os.path.dirname(zip_abs), exist_ok=True)

    with zipfile.ZipFile(zip_abs, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_abs, arcname=os.path.basename(file_abs))
    return zip_rel


def rename_rel(src_rel: str, new_name: str) -> str:
    src_abs = resolve_path(src_rel)
    new_name = safe_name(new_name, default="file")
    dst_abs = os.path.join(os.path.dirname(src_abs), new_name)
    dst_rel = os.path.relpath(dst_abs, ensure_dir(""))
    os.rename(src_abs, dst_abs)
    return dst_rel
