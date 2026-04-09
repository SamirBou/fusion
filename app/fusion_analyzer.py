import json
import logging
from pathlib import Path

from .sprites import sprite_url

CACHE_FILE = Path(__file__).parent.parent / "data" / "all_fusions_data.json"
_FUSION_POKEMON_FILE = Path(__file__).parent.parent / "data" / "fusion_pokemon_data.json"

logger = logging.getLogger(__name__)

_index: dict[tuple[int, int], dict] | None = None
_fusion_pokemon: dict | None = None

_TYPE_ORDER = (
    "NORMAL",
    "FIRE",
    "WATER",
    "ELECTRIC",
    "GRASS",
    "ICE",
    "FIGHTING",
    "POISON",
    "GROUND",
    "FLYING",
    "PSYCHIC",
    "BUG",
    "ROCK",
    "GHOST",
    "DRAGON",
    "DARK",
    "STEEL",
    "FAIRY",
)

_TYPE_CHART = {
    "NORMAL": {"ROCK": 0.5, "GHOST": 0.0, "STEEL": 0.5},
    "FIRE": {
        "FIRE": 0.5,
        "WATER": 0.5,
        "GRASS": 2.0,
        "ICE": 2.0,
        "BUG": 2.0,
        "ROCK": 0.5,
        "DRAGON": 0.5,
        "STEEL": 2.0,
    },
    "WATER": {
        "FIRE": 2.0,
        "WATER": 0.5,
        "GRASS": 0.5,
        "GROUND": 2.0,
        "ROCK": 2.0,
        "DRAGON": 0.5,
    },
    "ELECTRIC": {
        "WATER": 2.0,
        "ELECTRIC": 0.5,
        "GRASS": 0.5,
        "GROUND": 0.0,
        "FLYING": 2.0,
        "DRAGON": 0.5,
    },
    "GRASS": {
        "FIRE": 0.5,
        "WATER": 2.0,
        "GRASS": 0.5,
        "POISON": 0.5,
        "GROUND": 2.0,
        "FLYING": 0.5,
        "BUG": 0.5,
        "ROCK": 2.0,
        "DRAGON": 0.5,
        "STEEL": 0.5,
    },
    "ICE": {
        "FIRE": 0.5,
        "WATER": 0.5,
        "GRASS": 2.0,
        "ICE": 0.5,
        "GROUND": 2.0,
        "FLYING": 2.0,
        "DRAGON": 2.0,
        "STEEL": 0.5,
    },
    "FIGHTING": {
        "NORMAL": 2.0,
        "ICE": 2.0,
        "POISON": 0.5,
        "FLYING": 0.5,
        "PSYCHIC": 0.5,
        "BUG": 0.5,
        "ROCK": 2.0,
        "GHOST": 0.0,
        "DARK": 2.0,
        "STEEL": 2.0,
        "FAIRY": 0.5,
    },
    "POISON": {
        "GRASS": 2.0,
        "POISON": 0.5,
        "GROUND": 0.5,
        "ROCK": 0.5,
        "GHOST": 0.5,
        "STEEL": 0.0,
        "FAIRY": 2.0,
    },
    "GROUND": {
        "FIRE": 2.0,
        "ELECTRIC": 2.0,
        "GRASS": 0.5,
        "POISON": 2.0,
        "FLYING": 0.0,
        "BUG": 0.5,
        "ROCK": 2.0,
        "STEEL": 2.0,
    },
    "FLYING": {
        "ELECTRIC": 0.5,
        "GRASS": 2.0,
        "FIGHTING": 2.0,
        "BUG": 2.0,
        "ROCK": 0.5,
        "STEEL": 0.5,
    },
    "PSYCHIC": {
        "FIGHTING": 2.0,
        "POISON": 2.0,
        "PSYCHIC": 0.5,
        "DARK": 0.0,
        "STEEL": 0.5,
    },
    "BUG": {
        "FIRE": 0.5,
        "GRASS": 2.0,
        "FIGHTING": 0.5,
        "POISON": 0.5,
        "FLYING": 0.5,
        "PSYCHIC": 2.0,
        "GHOST": 0.5,
        "DARK": 2.0,
        "STEEL": 0.5,
        "FAIRY": 0.5,
    },
    "ROCK": {
        "FIRE": 2.0,
        "ICE": 2.0,
        "FIGHTING": 0.5,
        "GROUND": 0.5,
        "FLYING": 2.0,
        "BUG": 2.0,
        "STEEL": 0.5,
    },
    "GHOST": {"NORMAL": 0.0, "PSYCHIC": 2.0, "GHOST": 2.0, "DARK": 0.5},
    "DRAGON": {"DRAGON": 2.0, "STEEL": 0.5, "FAIRY": 0.0},
    "DARK": {"FIGHTING": 0.5, "PSYCHIC": 2.0, "GHOST": 2.0, "DARK": 0.5, "FAIRY": 0.5},
    "STEEL": {
        "FIRE": 0.5,
        "WATER": 0.5,
        "ELECTRIC": 0.5,
        "ICE": 2.0,
        "ROCK": 2.0,
        "STEEL": 0.5,
        "FAIRY": 2.0,
    },
    "FAIRY": {"FIRE": 0.5, "FIGHTING": 2.0, "POISON": 0.5, "DRAGON": 2.0, "DARK": 2.0, "STEEL": 0.5},
}


def _load_fusion_pokemon() -> dict:
    global _fusion_pokemon
    if _fusion_pokemon is not None:
        return _fusion_pokemon
    if _FUSION_POKEMON_FILE.exists():
        try:
            _fusion_pokemon = json.loads(_FUSION_POKEMON_FILE.read_text(encoding="utf-8"))
        except Exception:
            _fusion_pokemon = {}
    else:
        _fusion_pokemon = {}
    return _fusion_pokemon


def _get_fusion_abilities(head_id: int, body_id: int) -> dict:
    fp = _load_fusion_pokemon()

    head_entry = fp.get(str(head_id), {})
    body_entry = fp.get(str(body_id), {})
    head_abs = head_entry.get("abilities", [])
    body_abs = body_entry.get("abilities", [])

    def _pretty(name: str) -> str:
        return name.replace("-", " ").title() if name else ""

    head_slot1 = next((a["name"] for a in head_abs if not a.get("is_hidden")), None)
    body_slot1 = next((a["name"] for a in body_abs if not a.get("is_hidden")), None)
    head_hidden = next((a["name"] for a in head_abs if a.get("is_hidden")), None)

    def _desc(ability_list, name):
        if not name:
            return ""
        entry = next((a for a in ability_list if a.get("name") == name), {})
        return entry.get("description", "")

    return {
        "Ability 1": _pretty(head_slot1) if head_slot1 else "—",
        "Ability 2": _pretty(body_slot1) if body_slot1 else "—",
        "Hidden Ability": _pretty(head_hidden) if head_hidden else "—",
        "_ab1_desc": _desc(head_abs, head_slot1),
        "_ab2_desc": _desc(body_abs, body_slot1),
        "_abH_desc": _desc(head_abs, head_hidden),
    }


_STAT_ALIASES = {
    "HP": ("HP", "hp"),
    "ATK": ("ATK", "atk"),
    "DEF": ("DEF", "def"),
    "SP.ATK": ("SP.ATK", "sp_atk", "spatk"),
    "SP.DEF": ("SP.DEF", "sp_def", "spdef"),
    "SPEED": ("SPEED", "speed"),
    "TOTAL": ("TOTAL", "Total", "total"),
}


def _stat(stats: dict, key: str) -> int:
    for alias in _STAT_ALIASES.get(key, (key,)):
        v = stats.get(alias)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0
    return 0


def _normalize_types(entry: dict) -> list[str]:
    raw_types = entry.get("types") or entry.get("Types") or []
    if isinstance(raw_types, str):
        candidates = [part.strip().upper() for part in raw_types.split(",")]
    else:
        candidates = [str(part).strip().upper() for part in raw_types]
    return [type_name for type_name in candidates if type_name in _TYPE_ORDER]


def _bucket_for_multiplier(multiplier: float) -> str | None:
    rounded = round(multiplier, 2)
    if rounded == 0.0:
        return "x0"
    if rounded == 0.25:
        return "x1/4"
    if rounded == 0.5:
        return "x1/2"
    if rounded == 1.0:
        return "x1"
    if rounded == 2.0:
        return "x2"
    if rounded == 4.0:
        return "x4"
    return None


def _compute_weaknesses_from_types(types: list[str]) -> dict[str, list[str]]:
    if not types:
        return {}

    computed = {bucket: [] for bucket in ("x0", "x1/4", "x1/2", "x1", "x2", "x4")}
    for attack_type in _TYPE_ORDER:
        multiplier = 1.0
        for defend_type in types:
            multiplier *= _TYPE_CHART.get(attack_type, {}).get(defend_type, 1.0)
        bucket = _bucket_for_multiplier(multiplier)
        if bucket:
            computed[bucket].append(attack_type)
    return {bucket: values for bucket, values in computed.items() if values}


def _get_weaknesses(entry: dict) -> dict[str, list[str]]:
    weak = entry.get("weaknesses") or {}
    if isinstance(weak, dict):
        has_data = any(weak.get(bucket) for bucket in ("x0", "x1/4", "x1/2", "x1", "x2", "x4"))
        if has_data:
            return {
                bucket: list(weak.get(bucket) or [])
                for bucket in ("x0", "x1/4", "x1/2", "x1", "x2", "x4")
                if weak.get(bucket)
            }
    return _compute_weaknesses_from_types(_normalize_types(entry))


def _get_metric(entry: dict, metric: str) -> float:
    stats = entry.get("stats") or {}
    hp = _stat(stats, "HP")
    if metric == "Total":
        return float(_stat(stats, "TOTAL"))
    if metric == "Mixed Bulk":
        return hp * (_stat(stats, "DEF") + _stat(stats, "SP.DEF")) / 200
    if metric == "Phys Bulk":
        return hp * _stat(stats, "DEF") / 100
    if metric == "Spec Bulk":
        return hp * _stat(stats, "SP.DEF") / 100
    if metric == "Offense":
        return float(max(_stat(stats, "ATK"), _stat(stats, "SP.ATK")))
    if metric == "Type Score":
        w = _get_weaknesses(entry)
        imm = len(w.get("x0") or [])
        res = len(w.get("x1/2") or []) + len(w.get("x1/4") or [])
        return float(2 * imm + res - 2 * len(w.get("x2") or []) - 4 * len(w.get("x4") or []))
    if metric == "Composite":
        return float(_stat(stats, "TOTAL")) + 20 * _get_metric(entry, "Type Score")
    if metric in ("ATK", "SP.ATK", "SPEED"):
        return float(_stat(stats, metric))
    return 0.0


def _load_index() -> dict[tuple[int, int], dict]:
    global _index
    if _index is not None:
        return _index
    path = CACHE_FILE if CACHE_FILE.exists() else None
    if path is None:
        _index = {}
        return _index
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        _index = {}
        for key, entry in raw.items():
            parts = key.split(".")
            if len(parts) == 2:
                try:
                    _index[(int(parts[0]), int(parts[1]))] = entry
                except Exception:
                    pass
        logger.info(f"Loaded fusion index: {len(_index)} pairs")
    except Exception as e:
        logger.warning(f"Failed to load fusion cache {path}: {e}")
        _index = {}
    return _index


def _sprite_url(a: int, b: int) -> str:
    return sprite_url(f"{a}.{b}")


def _map_to_ui(e, a, b):
    stats = e.get("stats") or {}
    hp    = _stat(stats, "HP")
    atk   = _stat(stats, "ATK")
    df    = _stat(stats, "DEF")
    spatk = _stat(stats, "SP.ATK")
    spdef = _stat(stats, "SP.DEF")
    speed = _stat(stats, "SPEED")

    weak = _get_weaknesses(e)
    imm = weak.get("x0") or []
    res = list(weak.get("x1/2") or []) + list(weak.get("x1/4") or [])
    w2  = weak.get("x2") or []
    w4  = weak.get("x4") or []

    return {
        "Fusion ID": f"#{a}.{b}",
        "Local Sprite": _sprite_url(a, b),
        "Name": e.get("name") or e.get("Name"),
        "Types": e.get("types") or e.get("Types"),
        "Total": _stat(stats, "TOTAL"),
        "HP": hp, "ATK": atk, "DEF": df,
        "SP.ATK": spatk, "SP.DEF": spdef, "SPEED": speed,
        "Phys Bulk": round(hp * df / 100, 1),
        "Spec Bulk": round(hp * spdef / 100, 1),
        "Mixed Bulk": round(hp * (df + spdef) / 200, 1),
        "Offense": max(atk, spatk),
        "Immunities": imm, "Resists": res, "2x Weak": w2, "4x Weak": w4,
        "Type Score": 2 * len(imm) + len(res) - 2 * len(w2) - 4 * len(w4),
        **_get_fusion_abilities(a, b),
    }


def analyze_fusions(pokemon_ids):
    try:
        ids = sorted({int(i) for i in (pokemon_ids or [])})
    except Exception:
        return []
    if not ids:
        return []
    index = _load_index()
    if not index:
        return []
    results = []
    for a in ids:
        for b in ids:
            if a == b:
                continue
            entry = index.get((a, b))
            if entry is None:
                continue
            results.append(_map_to_ui(dict(entry), a, b))
    return results


def _rank_team_pairs(pokemon_ids, metric: str = "Total", max_fusions: int = 6) -> list[tuple[float, list]]:
    try:
        ids = sorted({int(i) for i in (pokemon_ids or [])})
    except Exception:
        return []

    if len(ids) < 2:
        return []

    if len(ids) > 20:
        ids = ids[:20]

    n = len(ids)
    index = _load_index()
    if not index:
        return []

    pair_best: dict[tuple[int, int], tuple] = {}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = ids[i], ids[j]
            e_ab = index.get((a, b))
            e_ba = index.get((b, a))
            if e_ab is None and e_ba is None:
                continue
            score_ab = _get_metric(e_ab, metric) if e_ab is not None else -1.0
            score_ba = _get_metric(e_ba, metric) if e_ba is not None else -1.0
            if score_ab >= score_ba:
                pair_best[(i, j)] = (a, b, e_ab, score_ab)
            else:
                pair_best[(i, j)] = (b, a, e_ba, score_ba)

    dp: dict[int, tuple[float, list]] = {0: (0.0, [])}

    for mask in range(1, 1 << n):
        bits = bin(mask).count("1")
        if bits % 2 != 0:
            continue
        if bits > 2 * max_fusions:
            continue

        first = (mask & -mask).bit_length() - 1

        best_score = -1.0
        best_pairs: list | None = None

        temp = mask ^ (1 << first)
        while temp:
            bit_pos = (temp & -temp).bit_length() - 1
            pair_key = (first, bit_pos)
            if pair_key in pair_best:
                prev_mask = mask ^ (1 << first) ^ (1 << bit_pos)
                if prev_mask in dp:
                    prev_score, prev_pairs = dp[prev_mask]
                    _, _, _, pair_score = pair_best[pair_key]
                    total = prev_score + pair_score
                    if total > best_score:
                        best_score = total
                        best_pairs = prev_pairs + [pair_best[pair_key]]
            temp &= temp - 1

        if best_pairs is not None:
            dp[mask] = (best_score, best_pairs)

    unique_results: dict[tuple[str, ...], tuple[float, list]] = {}
    for score, pairs in dp.values():
        if not pairs:
            continue
        signature = tuple(sorted(f"{a}.{b}" for a, b, _, _ in pairs))
        current = unique_results.get(signature)
        if current is None or score > current[0]:
            unique_results[signature] = (score, pairs)

    ranked = sorted(
        unique_results.items(),
        key=lambda item: (-item[1][0], -len(item[1][1]), item[0]),
    )
    return [payload for _, payload in ranked]


def find_best_teams(
    pokemon_ids,
    metric: str = "Total",
    max_fusions: int = 6,
    max_teams: int = 3,
) -> list[tuple[list, float]]:
    ranked_pairs = _rank_team_pairs(pokemon_ids, metric=metric, max_fusions=max_fusions)
    teams: list[tuple[list, float]] = []
    for score, pairs in ranked_pairs[: max(1, int(max_teams or 1))]:
        team = [_map_to_ui(dict(entry), a, b) for a, b, entry, _ in pairs]
        teams.append((team, score))
    return teams


def find_best_team(pokemon_ids, metric: str = "Total", max_fusions: int = 6) -> tuple[list, float]:
    teams = find_best_teams(pokemon_ids, metric=metric, max_fusions=max_fusions, max_teams=1)
    if not teams:
        return [], 0.0
    return teams[0]
