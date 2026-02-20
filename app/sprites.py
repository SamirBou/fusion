import base64
import json
import logging
import threading
from pathlib import Path

from flask import Response, abort, send_from_directory

from . import app, get_repo_root, sprite_rel_cache

logger = logging.getLogger(__name__)


def _index_all_sprites():
    try:
        sprites_dir = get_repo_root() / "data" / "sprites"
        if not sprites_dir.exists():
            logger.info("No sprites directory found to index")
            return 0

        count = 0
        for p in sprites_dir.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif"):
                continue
            try:
                rel = str(p.relative_to(sprites_dir)).replace("\\", "/")
                name = p.stem
                filename = p.name
                sprite_rel_cache[filename] = rel
                sprite_rel_cache[name] = rel
                if name.isdigit():
                    n = str(int(name))
                    sprite_rel_cache[n] = rel
                    sprite_rel_cache[f"{int(n):03}"] = rel
                    sprite_rel_cache[f"{int(n):03}.png"] = rel
                    sprite_rel_cache[f"{n}.png"] = rel
                if "." in name:
                    parts = name.split(".")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        key = f"{int(parts[0])}.{int(parts[1])}"
                        sprite_rel_cache[key] = rel
                        sprite_rel_cache[f"{key}.png"] = rel
                count += 1
            except Exception:
                continue

        logger.info(f"Indexed {count} sprites into sprite_rel_cache")
        try:
            manifest_path = sprites_dir / "manifest.json"
            with manifest_path.open("w", encoding="utf-8") as mf:
                json.dump(sprite_rel_cache, mf, indent=2)
            logger.info(f"Wrote sprite manifest to {manifest_path}")
        except Exception as e:
            logger.warning(f"Failed to write sprite manifest: {e}")
        return count
    except Exception as e:
        logger.warning(f"Error indexing sprites: {e}")
        return 0


def _load_sprite_manifest():
    try:
        sprites_dir = get_repo_root() / "data" / "sprites"
        manifest_path = sprites_dir / "manifest.json"
        if manifest_path.exists():
            with manifest_path.open("r", encoding="utf-8") as mf:
                data = json.load(mf)
                if isinstance(data, dict):
                    sprite_rel_cache.update(data)
                    logger.info(f"Loaded sprite manifest with {len(data)} entries")
                    return True
    except Exception as e:
        logger.warning(f"Failed to load sprite manifest: {e}")
    return False


def get_sprite_base64(rel_path: str):
    try:
        sprites_dir = get_repo_root() / "data" / "sprites"
        full_path = sprites_dir / rel_path
        if full_path.exists():
            data = full_path.read_bytes()
            encoded = base64.b64encode(data).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
        return None
    except Exception:
        return None


def find_sprite_relpath(pid):
    try:
        if pid is None:
            return None

        def try_keys(p):
            keys = []
            s = str(p)
            s_nohash = s.lstrip('#')
            keys.append(s)
            if not s.endswith('.png'):
                keys.append(f"{s}.png")
            if s_nohash != s:
                keys.append(s_nohash)
                if not s_nohash.endswith('.png'):
                    keys.append(f"{s_nohash}.png")
            if s.isdigit():
                keys.append(str(int(s)))
                keys.append(f"{int(s):03}")
                keys.append(f"{int(s):03}.png")
            if '.' in s:
                keys.append(s.replace('.png', ''))
                keys.append(s.replace('.png', '') + '.png')
            return keys

        for k in try_keys(pid):
            if k and k in sprite_rel_cache:
                return sprite_rel_cache[k]

        sprites_dir = get_repo_root() / "data" / "sprites"
        filename = f"{pid}.png" if not str(pid).endswith('.png') else str(pid)
        if "." in filename:
            fusions_path = sprites_dir / "fusions" / filename
            if fusions_path.exists():
                rel = f"fusions/{filename}"
                sprite_rel_cache[pid] = rel
                return rel
        root_path = sprites_dir / filename
        if root_path.exists():
            rel = filename
            sprite_rel_cache[pid] = rel
            return rel
        if "." not in filename:
            try:
                pid_num = int(filename.replace('.png', ''))
                start = ((pid_num - 1) // 100) * 100 + 1
                end = start + 99
                subdir = f"{start:03d}-{end:03d}"
                sub_path = sprites_dir / subdir / filename
                if sub_path.exists():
                    rel = f"{subdir}/{filename}"
                    sprite_rel_cache[pid] = rel
                    return rel
            except Exception:
                pass

            try:
                for p in sprites_dir.rglob(filename):
                    try:
                        rel = str(p.relative_to(sprites_dir)).replace("\\", "/")
                        sprite_rel_cache[pid] = rel
                        return rel
                    except Exception:
                        sprite_rel_cache[pid] = p.name
                        return p.name
            except Exception:
                pass

        parts = filename.replace('.png', '').split('.')
        if len(parts) == 2:
            try:
                if (get_repo_root() / "data" / "sprites").exists():
                    sprite_rel_cache[pid] = f"{parts[0]}.{parts[1]}.png"
                    return sprite_rel_cache[pid]
            except Exception:
                pass

    except Exception:
        sprite_rel_cache[pid] = None
        return None

    sprite_rel_cache[pid] = None
    return None


@app.server.route("/sprites/<path:filename>")
def serve_sprite(filename):
    try:
        raw = filename.replace("&#x2F;", "/").replace("%2F", "/")
        if ".." in raw or raw.startswith("/") or "\\" in raw:
            logger.warning(f"Path traversal attempt blocked: {raw}")
            abort(403)
        if not raw.endswith('.png'):
            abort(400)
        sprites_dir = get_repo_root() / "data" / "sprites"
        if "/" not in raw and "." not in raw:
            try:
                pid_num = int(raw.replace('.png', ''))
                start = ((pid_num - 1) // 100) * 100 + 1
                end = start + 99
                subdir = f"{start:03d}-{end:03d}"
                sub_path = sprites_dir / subdir / raw
                if sub_path.exists():
                    return send_from_directory(str(sprites_dir), f"{subdir}/{raw}", mimetype="image/png")
            except Exception:
                pass
        sprite_path = sprites_dir / raw
        if sprite_path.exists():
            rel = sprite_path.relative_to(sprites_dir)
            return send_from_directory(str(sprites_dir), str(rel).replace("\\", "/"), mimetype="image/png")
        try:
            for p in sprites_dir.rglob(raw.split('/')[-1]):
                try:
                    rel = p.relative_to(sprites_dir)
                    return send_from_directory(str(sprites_dir), str(rel).replace("\\", "/"), mimetype="image/png")
                except Exception:
                    return send_from_directory(str(sprites_dir), p.name, mimetype="image/png")
        except Exception:
            pass
        logger.debug(f"Sprite not found in local storage: {raw}")
        abort(404)
    except Exception as e:
        logger.error(f"Error serving sprite {filename}: {e}")
        abort(500)


try:
    manifest_loaded = _load_sprite_manifest()
    if not manifest_loaded:
        threading.Thread(target=_index_all_sprites, daemon=True).start()
except Exception:
    pass
