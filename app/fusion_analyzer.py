import json
import logging
from pathlib import Path

CACHE_FILE = Path("data") / "all_fusions_data.json"
FALLBACK_CACHE = Path("data") / "all_fusions_data_full_run.json"

logger = logging.getLogger(__name__)


def _load_cache():
    path = CACHE_FILE if CACHE_FILE.exists() else (FALLBACK_CACHE if FALLBACK_CACHE.exists() else None)
    if path is None:
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        logger.warning(f"Failed to load fusion cache {path}: {e}")
        return None


def _parse_fusion_id(raw):
    if not raw:
        return None
    try:
        s = str(raw).lstrip("#")
        parts = s.split(".")
        if len(parts) != 2:
            return None
        return int(parts[0]), int(parts[1])
    except Exception:
        return None


def _normalize_sprite_path(s):
    if not s:
        return None
    try:
        s = str(s).replace('\\', '/').strip()
        if s.startswith('/sprites/') or s.startswith('http'):
            if s.startswith('/sprites/') and not s.lower().endswith('.png'):
                return s + '.png'
            return s
        if 'data/sprites/' in s:
            rel = s.split('data/sprites/')[-1].lstrip('/')
            if not rel.lower().endswith('.png'):
                rel = rel + '.png'
            return f'/sprites/{rel}'
        filename = s.split('/')[-1]
        if not filename.lower().endswith('.png'):
            filename = filename + '.png'
        return f'/sprites/{filename}'
    except Exception:
        return s


def _entry_fusion_id(entry):
    for k in ("Fusion ID", "FusionID", "id", "fusion_id", "fusion"):
        if isinstance(entry, dict) and k in entry and entry.get(k):
            return entry.get(k)
    return None


def _map_to_ui(e, a, b):
    ui = {}
    ui["Fusion ID"] = e.get("Fusion ID") or f"#{a}.{b}"
    ui["Fusion URL"] = e.get("fusion_url") or e.get("Fusion URL") or e.get("fusionUrl")
    ui["Local Sprite"] = _normalize_sprite_path(
        e.get("local_sprite") or e.get("Local Sprite") or e.get("LocalSprite") or e.get("sprite_url") or e.get("Sprite")
    )
    ui["Sprite"] = e.get("sprite_url") or e.get("Sprite")
    ui["Name"] = e.get("name") or e.get("Name")
    ui["Types"] = e.get("types") or e.get("Types")
    stats = e.get("stats") or {}
    ui["Total"] = stats.get("TOTAL") or stats.get("Total") or stats.get("total") or e.get("Total")
    ui["HP"] = stats.get("HP") or stats.get("hp")
    ui["ATK"] = stats.get("ATK") or stats.get("atk")
    ui["DEF"] = stats.get("DEF") or stats.get("def")
    ui["SP.ATK"] = stats.get("SP.ATK") or stats.get("sp_atk") or stats.get("spatk")
    ui["SP.DEF"] = stats.get("SP.DEF") or stats.get("sp_def") or stats.get("spdef")
    ui["SPEED"] = stats.get("SPEED") or stats.get("speed")
    # Defensive and Bulk: compute from stats if not provided
    ui["Defensive"] = e.get("Defensive") if e.get("Defensive") is not None else None
    ui["Bulk"] = e.get("Bulk") if e.get("Bulk") is not None else None
    try:
        if (ui["Defensive"] is None or ui["Bulk"] is None) and isinstance(stats, dict):
            hp = int(stats.get("HP") or stats.get("hp") or 0)
            df = int(stats.get("DEF") or stats.get("def") or 0)
            spd = int(stats.get("SP.DEF") or stats.get("sp_def") or stats.get("spdef") or 0)
            computed_bulk = hp + df + spd
            computed_defensive = hp + int((df + spd) / 2)
            if ui["Bulk"] is None:
                ui["Bulk"] = computed_bulk
            if ui["Defensive"] is None:
                ui["Defensive"] = computed_defensive
    except Exception:
        pass
    weak = e.get("weaknesses") or {}
    ui["Immunities"] = weak.get("x0") or []
    resists = []
    if weak.get("x1/2"):
        resists.extend(weak.get("x1/2"))
    if weak.get("x1/4"):
        resists.extend(weak.get("x1/4"))
    ui["Resists"] = resists
    ui["2x Weak"] = weak.get("x2") or []
    ui["4x Weak"] = weak.get("x4") or []
    for kk, vv in e.items():
        if kk not in ("Fusion ID", "fusion_url", "Fusion URL", "local_sprite", "sprite_url", "Sprite", "name", "Name", "types", "Types", "stats", "weaknesses"):
            ui[kk] = vv
    return ui


def analyze_fusions(pokemon_ids):
    try:
        ids_set = {int(i) for i in (pokemon_ids or [])}
    except Exception:
        ids_set = set()
    if not ids_set:
        return []
    cache = _load_cache()
    if not cache:
        return []
    results = []
    if isinstance(cache, dict):
        for key, entry in cache.items():
            fid = _parse_fusion_id(key.replace('.png', '')) or _parse_fusion_id(_entry_fusion_id(entry))
            if not fid:
                continue
            a, b = fid
            if a in ids_set and b in ids_set:
                e = dict(entry) if isinstance(entry, dict) else {"Fusion ID": f"#{a}.{b}"}
                for sprite_key in ("local_sprite", "Local Sprite", "LocalSprite"):
                    if sprite_key in e and e[sprite_key]:
                        e["local_sprite"] = _normalize_sprite_path(e[sprite_key])
                        break
                else:
                    for sprite_key in ("sprite_url", "Sprite"):
                        if sprite_key in e and e[sprite_key]:
                            e["local_sprite"] = _normalize_sprite_path(e[sprite_key])
                            break
                if not e.get("Fusion ID"):
                    e["Fusion ID"] = f"#{a}.{b}"
                results.append(_map_to_ui(e, a, b))
        return results
    if isinstance(cache, list):
        for entry in cache:
            raw = _entry_fusion_id(entry)
            fid = _parse_fusion_id(raw)
            if not fid:
                continue
            a, b = fid
            if a in ids_set and b in ids_set:
                e = dict(entry)
                for sprite_key in ("local_sprite", "Local Sprite", "LocalSprite"):
                    if sprite_key in e and e[sprite_key]:
                        e["local_sprite"] = _normalize_sprite_path(e[sprite_key])
                        break
                else:
                    for sprite_key in ("sprite_url", "Sprite"):
                        if sprite_key in e and e[sprite_key]:
                            e["local_sprite"] = _normalize_sprite_path(e[sprite_key])
                            break
                if not e.get("Fusion ID"):
                    e["Fusion ID"] = f"#{a}.{b}"
                results.append(_map_to_ui(e, a, b))
        return results
    return []


def fetch_fusion_data(combo, _):
    return None


def download_sprite_if_needed(sprite_url, fusion_key):
    return None


def save_to_cache(data):
    return
