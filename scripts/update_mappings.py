import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bs4 import BeautifulSoup

SOURCES_DIR = Path(__file__).parent.parent / "data" / "sources"
DATA_DIR = Path(__file__).parent.parent / "data"
POKEMON_DATA_FILE = Path(__file__).parent.parent / "app" / "pokemon_data.py"
FUSION_POKEMON_DATA_FILE = DATA_DIR / "fusion_pokemon_data.json"

_POKEAPI_HEADERS = {"User-Agent": "fusion-dex-app/1.0"}
_POKEAPI_BASE = "https://pokeapi.co/api/v2"
_POKEAPI_WORKERS = 10
_POKEAPI_TIMEOUT = 12


_EXPLICIT_ALIASES: dict[str, str] = {
    "nidoranf": "nidoran\u2640",
    "nidoranm": "nidoran\u2642",
    "ultranecrozma": "necrozma",
    "castformsunnyform": "castform",
    "castformrainyform": "castform",
    "castformsnowyform": "castform",
}

_FORM_SUFFIXES = re.compile(
    r"(midday|midnight|aria\s*forme|pirouette\s*forme|baile\s*style|"
    r"pom.?pom\s*style|pa.?u\s*style|sensu\s*style|meteor|core|"
    r"\s*forme$|\s*form$|\s*style$)"
)


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9\u2640\u2642]", "", name.lower())


def _resolve_name(fusion_name: str, national_lookup: dict) -> dict | None:
    norm = _normalize_name(fusion_name)
    if norm in _EXPLICIT_ALIASES:
        norm = _EXPLICIT_ALIASES[norm]
    result = national_lookup.get(norm)
    if result:
        return result
    stripped = _FORM_SUFFIXES.sub("", fusion_name.lower()).strip()
    norm2 = _normalize_name(stripped)
    return national_lookup.get(norm2)


def parse_pokemondb(html_path: Path) -> dict[str, dict]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    national: dict[str, dict] = {}
    current_gen = 0

    for tag in soup.find_all(["h2", "div"]):
        if tag.name == "h2" and tag.get("id", "").startswith("gen-"):
            try:
                current_gen = int(tag["id"].replace("gen-", ""))
            except ValueError:
                pass
            continue

        if tag.name == "div" and "infocard" in tag.get("class", []):
            small = tag.find("small")
            ent = tag.find("a", class_="ent-name")
            if not small or not ent:
                continue
            raw_id = small.get_text(strip=True).lstrip("#")
            try:
                national_id = int(raw_id)
            except ValueError:
                continue
            name = ent.get_text(strip=True)
            national[_normalize_name(name)] = {
                "name": name,
                "national_id": national_id,
                "generation": current_gen,
            }

    return national


def parse_fusiondex(html_path: Path) -> list[dict]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    entries = []

    for article in soup.find_all("article", class_="dex-entry-preview"):
        dex_id_tag = article.find("span", class_="dex-id")
        name_tag = article.find("h3")
        if not dex_id_tag or not name_tag:
            continue
        raw_id = dex_id_tag.get_text(strip=True).lstrip("#")
        try:
            fusion_id = int(raw_id)
        except ValueError:
            continue
        name_link = name_tag.find("a")
        name = (name_link or name_tag).get_text(strip=True)
        entries.append({"fusion_id": fusion_id, "name": name})

    return entries


def build_mappings(
    fusiondex_entries: list[dict],
    national_lookup: dict[str, dict],
) -> tuple[dict[str, str], dict[str, dict]]:
    pokemon_data: dict[str, str] = {}
    fusion_pokemon_data: dict[str, dict] = {}

    for entry in fusiondex_entries:
        fusion_id = entry["fusion_id"]
        fusion_name = entry["name"]
        key = str(fusion_id)
        official = _resolve_name(fusion_name, national_lookup)

        pokemon_data[key] = fusion_name
        if official:
            fusion_pokemon_data[key] = {
                "name": fusion_name,
                "generation": official["generation"],
                "national_id": str(official["national_id"]),
            }
        else:
            fusion_pokemon_data[key] = {
                "name": fusion_name,
                "generation": 0,
                "national_id": "",
            }

    return pokemon_data, fusion_pokemon_data


def write_pokemon_data_py(pokemon_data: dict[str, str], path: Path) -> None:
    lines = ["POKEMON_DATA = {\n"]
    for k, v in sorted(pokemon_data.items(), key=lambda x: int(x[0])):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    "{k}": "{escaped}",\n')
    lines.append("}\n\n")
    lines.append("POKEMON_NAME_TO_ID: dict[str, int] = {v: int(k) for k, v in POKEMON_DATA.items()}\n")
    path.write_text("".join(lines), encoding="utf-8")


def _pokeapi_get(url: str) -> dict:
    req = urllib.request.Request(url, headers=_POKEAPI_HEADERS)
    with urllib.request.urlopen(req, timeout=_POKEAPI_TIMEOUT) as resp:
        return json.loads(resp.read())


def _fetch_pokemon_abilities(national_id: str) -> list[dict]:
    try:
        data = _pokeapi_get(f"{_POKEAPI_BASE}/pokemon/{national_id}")
        return [
            {"name": a["ability"]["name"], "slot": a["slot"], "is_hidden": a["is_hidden"]}
            for a in data["abilities"]
        ]
    except Exception as e:
        print(f"  [WARN] abilities for national_id={national_id}: {e}")
        return []


def _fetch_ability_description(ability_name: str) -> str:
    try:
        data = _pokeapi_get(f"{_POKEAPI_BASE}/ability/{ability_name}")
        for e in data.get("effect_entries", []):
            if e.get("language", {}).get("name") == "en":
                return e.get("short_effect", "")
        for e in reversed(data.get("flavor_text_entries", [])):
            if e.get("language", {}).get("name") == "en":
                return e.get("flavor_text", "").replace("\n", " ").replace("\x0c", " ")
    except Exception as e:
        print(f"  [WARN] description for {ability_name}: {e}")
    return ""


def enrich_abilities(fusion_pokemon_data: dict[str, dict], force: bool = False) -> None:
    import time

    to_fetch = [
        (fid, v["national_id"])
        for fid, v in fusion_pokemon_data.items()
        if v.get("national_id") and (force or "abilities" not in v)
    ]
    print(f"  Fetching abilities for {len(to_fetch)} Pokemon...")
    t0 = time.time()

    raw: dict[str, list] = {}
    done_count = 0
    with ThreadPoolExecutor(max_workers=_POKEAPI_WORKERS) as pool:
        futures = {pool.submit(_fetch_pokemon_abilities, nat): fid for fid, nat in to_fetch}
        for fut in as_completed(futures):
            fid = futures[fut]
            raw[fid] = fut.result()
            done_count += 1
            if done_count % 100 == 0:
                print(f"    {done_count}/{len(to_fetch)} ({time.time()-t0:.0f}s)")
    print(f"  Phase 1 done in {time.time()-t0:.1f}s")

    existing_descs: dict[str, str] = {}
    for v in fusion_pokemon_data.values():
        for ab in v.get("abilities", []):
            if ab.get("description"):
                existing_descs[ab["name"]] = ab["description"]
    all_names = {a["name"] for abs_list in raw.values() for a in abs_list}
    new_names = [n for n in all_names if n not in existing_descs]
    print(f"  Fetching descriptions for {len(new_names)} abilities...")
    t1 = time.time()
    descriptions = dict(existing_descs)
    with ThreadPoolExecutor(max_workers=_POKEAPI_WORKERS) as pool:
        futures_d = {pool.submit(_fetch_ability_description, n): n for n in new_names}
        for fut in as_completed(futures_d):
            descriptions[futures_d[fut]] = fut.result()
    print(f"  Phase 2 done in {time.time()-t1:.1f}s")

    for fid, abs_list in raw.items():
        fusion_pokemon_data[fid]["abilities"] = [
            {**a, "description": descriptions.get(a["name"], "")}
            for a in abs_list
        ]


def update(
    fusiondex_html: Path | None = None,
    pokemondb_html: Path | None = None,
    fetch_abilities: bool = True,
) -> None:
    fusiondex_html = fusiondex_html or SOURCES_DIR / "fusiondex.html"
    pokemondb_html = pokemondb_html or SOURCES_DIR / "pokemondb_national.html"

    if not fusiondex_html.exists():
        print(f"ERROR: fusiondex source not found: {fusiondex_html}", file=sys.stderr)
        sys.exit(1)
    if not pokemondb_html.exists():
        print(f"ERROR: pokemondb source not found: {pokemondb_html}", file=sys.stderr)
        sys.exit(1)

    print("Parsing pokemondb national dex...")
    national = parse_pokemondb(pokemondb_html)
    print(f"  {len(national)} Pokemon found with national IDs and generations")

    print("Parsing fusiondex...")
    fusiondex_entries = parse_fusiondex(fusiondex_html)
    print(f"  {len(fusiondex_entries)} Pokemon found in fusion dex")

    print("Building mappings...")
    pokemon_data, fusion_pokemon_data = build_mappings(fusiondex_entries, national)

    unmatched = [e["name"] for e in fusiondex_entries if _resolve_name(e["name"], national) is None]
    if unmatched:
        print(f"  {len(unmatched)} unmatched (no official national dex entry): {unmatched[:10]}{'...' if len(unmatched) > 10 else ''}")

    print(f"Writing {POKEMON_DATA_FILE}...")
    write_pokemon_data_py(pokemon_data, POKEMON_DATA_FILE)

    existing_abilities: dict[str, list] = {}
    if FUSION_POKEMON_DATA_FILE.exists():
        try:
            old = json.loads(FUSION_POKEMON_DATA_FILE.read_text(encoding="utf-8"))
            existing_abilities = {k: v["abilities"] for k, v in old.items() if "abilities" in v}
        except Exception:
            pass
    for k, v in fusion_pokemon_data.items():
        if k in existing_abilities:
            v["abilities"] = existing_abilities[k]

    if fetch_abilities:
        print("Fetching ability data from PokéAPI...")
        enrich_abilities(fusion_pokemon_data)

    print(f"Writing {FUSION_POKEMON_DATA_FILE}...")
    FUSION_POKEMON_DATA_FILE.write_text(
        json.dumps(fusion_pokemon_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Done. {len(pokemon_data)} Pokemon mapped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rebuild Pokemon mappings and ability data.")
    parser.add_argument("--skip-abilities", action="store_true", help="Skip PokéAPI ability fetch (use cached data only)")
    args = parser.parse_args()
    update(fetch_abilities=not args.skip_abilities)
