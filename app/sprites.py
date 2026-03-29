import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

from flask import Response, abort, make_response, send_from_directory

from . import app, get_repo_root

logger = logging.getLogger(__name__)

_CACHE_HEADER = "public, max-age=604800, immutable"
_BASE_SPRITE_INDEX: dict[str, str] | None = None
_REMOTE_SPRITE_MISSES: set[str] = set()
_REMOTE_SPRITE_BASES = (
    "https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/",
    "https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/generated/",
)
_REMOTE_SPRITE_HEADERS = {"User-Agent": "fusion-dex-app/1.0"}
_REMOTE_SPRITE_TIMEOUT = 8
_SPRITE_URL_VERSION = str(int(time.time()))


def _cached(response):
    response.headers["Cache-Control"] = _CACHE_HEADER
    return response


def _subdir(head_id: int) -> str:
    start = ((head_id - 1) // 100) * 100 + 1
    return f"{start:03d}-{start + 99:03d}"


def _build_base_sprite_index() -> dict[str, str]:
    sprites_dir = get_repo_root() / "data" / "sprites"
    out: dict[str, str] = {}
    if not sprites_dir.exists():
        return out
    for bucket in sprites_dir.iterdir():
        if not bucket.is_dir():
            continue
        name = bucket.name
        if len(name) != 7 or name[3] != "-":
            continue
        for png in bucket.glob("*.png"):
            stem = png.stem
            if stem.isdigit():
                rel = str(png.relative_to(sprites_dir)).replace("\\", "/")
                out.setdefault(stem, rel)
    return out


def _get_base_sprite_index() -> dict[str, str]:
    global _BASE_SPRITE_INDEX
    if _BASE_SPRITE_INDEX is None:
        _BASE_SPRITE_INDEX = _build_base_sprite_index()
    return _BASE_SPRITE_INDEX


def _sprite_file_for_pid(pid) -> Path | None:
    if pid is None:
        return None
    s = str(pid).replace(".png", "")
    parts = s.split(".")
    try:
        head_id = int(parts[0])
    except (ValueError, IndexError):
        return None
    return get_repo_root() / "data" / "sprites" / _subdir(head_id) / f"{s}.png"


def _fetch_remote_sprite(pid: str) -> bytes | None:
    if not pid or pid in _REMOTE_SPRITE_MISSES:
        return None
    for base in _REMOTE_SPRITE_BASES:
        try:
            req = urllib.request.Request(f"{base}{pid}.png", headers=_REMOTE_SPRITE_HEADERS)
            with urllib.request.urlopen(req, timeout=_REMOTE_SPRITE_TIMEOUT) as resp:
                data = resp.read()
                if data:
                    return data
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                logger.debug(f"Remote sprite HTTP error for {pid}: {exc}")
        except Exception as exc:
            logger.debug(f"Remote sprite lookup failed for {pid}: {exc}")
    _REMOTE_SPRITE_MISSES.add(pid)
    return None


def _save_sprite_bytes(pid: str, data: bytes) -> None:
    dest = _sprite_file_for_pid(pid)
    if dest is None:
        return
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
    except Exception as exc:
        logger.debug(f"Failed to cache sprite {pid}: {exc}")


def sprite_relpath(pid) -> str | None:
    if pid is None:
        return None
    s = str(pid).replace(".png", "")
    parts = s.split(".")
    try:
        head_id = int(parts[0])
    except (ValueError, IndexError):
        return None
    filename = f"{s}.png"
    rel = f"{_subdir(head_id)}/{filename}"
    sprites_dir = get_repo_root() / "data" / "sprites"
    if (sprites_dir / rel).exists():
        return rel

    if s.isdigit():
        return _get_base_sprite_index().get(s, rel)

    return rel


def sprite_url(pid) -> str:
    rel = sprite_relpath(pid)
    path = f"/sprites/{rel}" if rel else f"/sprites/{pid}.png"
    return f"{path}?v={_SPRITE_URL_VERSION}"


def _serve_id_svg(pid: str) -> Response:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="56" height="56">'
        '<rect width="56" height="56" rx="4" fill="#e9ecef"/>'
        f'<text x="28" y="22" font-size="8" font-family="monospace" text-anchor="middle" fill="#6c757d">#</text>'
        f'<text x="28" y="36" font-size="8" font-family="monospace" text-anchor="middle" fill="#495057">{pid}</text>'
        "</svg>"
    )
    resp = make_response(svg, 200)
    resp.headers["Content-Type"] = "image/svg+xml"
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.server.route("/sprites/<path:filename>")
def serve_sprite(filename):
    try:
        raw = filename.replace("&#x2F;", "/").replace("%2F", "/")
        if ".." in raw or raw.startswith("/") or "\\" in raw:
            logger.warning(f"Path traversal attempt blocked: {raw}")
            abort(403)
        if not raw.endswith(".png"):
            abort(400)
        sprites_dir = get_repo_root() / "data" / "sprites"
        sprite_path = sprites_dir / raw
        if sprite_path.exists():
            rel = str(sprite_path.relative_to(sprites_dir)).replace("\\", "/")
            return _cached(
                make_response(
                    send_from_directory(
                        str(sprites_dir), rel, mimetype="image/png"
                    )
                )
            )
        pid_str = raw.replace(".png", "").split("/")[-1]
        remote_data = _fetch_remote_sprite(pid_str)
        if remote_data:
            _save_sprite_bytes(pid_str, remote_data)
            resp = make_response(remote_data, 200)
            resp.headers["Content-Type"] = "image/png"
            return _cached(resp)
        logger.debug(f"Sprite not found: {raw}")
        return _serve_id_svg(pid_str)
    except Exception as e:
        logger.error(f"Error serving sprite {filename}: {e}")
        pid = str(filename).replace(".png", "").split("/")[-1]
        return _serve_id_svg(pid)
