import argparse
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

try:
    import lxml
    _HTML_PARSER = "lxml"
except ImportError:
    _HTML_PARSER = "html.parser"

ROOT = Path(__file__).parent.parent
CACHE_FILE = ROOT / "data" / "all_fusions_data.json"
SPRITES_BASE = ROOT / "data" / "sprites"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "fetch_missing.log"

LOG_DIR.mkdir(exist_ok=True)
SPRITES_BASE.mkdir(parents=True, exist_ok=True)


def _sprite_subdir(head_id: int) -> Path:
    start = ((head_id - 1) // 100) * 100 + 1
    end = start + 99
    subdir = SPRITES_BASE / f"{start:03d}-{end:03d}"
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def _sprite_dest_exists(key: str) -> bool:
    try:
        pid = key.lstrip("#")
        head_id = int(pid.split(".")[0])
        return (_sprite_subdir(head_id) / f"{pid}.png").exists()
    except Exception:
        return False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

BASE_URL = "https://infinitefusiondex.com/details/"
SPRITE_BASE = "https://infinitefusiondex.com/sprites/"
REQUEST_TIMEOUT = 8
SPRITE_TIMEOUT = 6
RETRY_ATTEMPTS = 2
RETRY_DELAY = 0.3


def load_cache() -> dict:
    if not CACHE_FILE.exists():
        logger.warning("all_fusions_data.json not found — starting fresh")
        return {}
    try:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} existing entries from cache")
        return data
    except Exception as e:
        logger.error(f"Failed to load cache: {e}")
        return {}


def load_pokemon_ids() -> list[int]:
    try:
        sys.path.insert(0, str(ROOT / "app"))
        import importlib
        import pokemon_data as _pd
        importlib.reload(_pd)
        ids = sorted(int(k) for k in _pd.POKEMON_DATA)
        logger.info(f"Loaded {len(ids)} Pokemon IDs from pokemon_data.py")
        return ids
    except Exception as e:
        logger.error(f"Failed to load pokemon_data: {e}")
        sys.exit(1)


def find_missing_pairs(cache: dict, pokemon_ids: list[int]) -> list[tuple[int, int]]:
    existing = set(cache.keys())
    missing: list[tuple[int, int]] = []

    for i, a in enumerate(pokemon_ids):
        for b in pokemon_ids[i:]:
            key1 = f"{a}.{b}"
            key2 = f"{b}.{a}"
            if key1 not in existing or (a != b and key2 not in existing):
                missing.append((a, b))

    logger.info(f"Found {len(missing)} missing pair requests to fetch")
    return missing


_thread_local = threading.local()


def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=1)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        s.headers["User-Agent"] = "Mozilla/5.0 (fusion-fetcher/1.0)"
        _thread_local.session = s
    return _thread_local.session


def _get(url: str, timeout: int = REQUEST_TIMEOUT) -> requests.Response | None:
    session = _get_session()
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)
        except Exception:
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)
    return None


def _parse_stats(soup: BeautifulSoup) -> dict | None:
    stats = {"fusion1": {}, "fusion2": {}}
    try:
        header = soup.find("h2", class_="accordion-header", string="Stats")
        if not header:
            return None
        body = header.find_next("div", class_="accordion-body")
        if not body:
            return None
        for row in body.find_all("div", class_="g-1"):
            name_el = row.find("div", class_="font-gray subheader text-center")
            if not name_el:
                continue
            raw = name_el.text.strip()
            if "SPEED" in raw:
                name = "SPEED"
            elif "SP.ATK" in raw or "SPA" in raw:
                name = "SP.ATK"
            elif "SP.DEF" in raw or "SPD" in raw:
                name = "SP.DEF"
            elif "TOTAL" in raw or "TOT" in raw:
                name = "TOTAL"
            else:
                name = raw
            vals = []
            for col in row.find_all("div", recursive=False):
                sec = col.find("div", class_="section")
                if sec:
                    txt = sec.text.strip().split("(")[0].strip()
                    if txt != "X":
                        try:
                            vals.append(int(txt))
                        except ValueError:
                            pass
            if len(vals) >= 2:
                stats["fusion1"][name] = vals[0]
                stats["fusion2"][name] = vals[1]
        return stats
    except Exception:
        return None


def _parse_weaknesses(soup: BeautifulSoup) -> dict:
    data = {"fusion1": {}, "fusion2": {}}
    try:
        btn = next(
            (b for b in soup.find_all("button", class_="accordion-button") if "Weaknesses" in b.text),
            None,
        )
        if not btn:
            return data
        body = btn.find_next("div", class_="accordion-body")
        if not body:
            return data
        main_row = body.find("div", class_="row")
        if not main_row:
            return data
        cols = main_row.find_all("div", recursive=False)
        i = 0
        while i < len(cols):
            mult_el = cols[i].find("div", class_="subheader")
            if not mult_el:
                i += 1
                continue
            mult = mult_el.text.strip().replace("\n", "").replace(" ", "")
            i += 1
            for fusion_key in ("fusion1", "fusion2"):
                if i < len(cols):
                    sec = cols[i].find("div", class_="section")
                    if sec:
                        types = [
                            img["alt"]
                            for img in sec.find_all("img", class_="elemental-type")
                            if img.get("alt", "-") != "-"
                        ]
                        if types:
                            data[fusion_key].setdefault(mult, []).extend(types)
                    i += 1
            if i < len(cols):
                dup = cols[i].find("div", class_="subheader")
                if dup and dup.text.strip().replace("\n", "").replace(" ", "") == mult:
                    i += 1
    except Exception:
        pass
    return data


def fetch_pair(a: int, b: int) -> dict | None:
    if a == b:
        url = f"{BASE_URL}{a}"
    else:
        url = f"{BASE_URL}{a}.{b}"

    resp = _get(url)
    if resp is None:
        return None

    try:
        soup = BeautifulSoup(resp.content, _HTML_PARSER)

        if a == b:
            panel = soup.find("div", class_="fusionDisplay")
            if not panel:
                return None
            name_el = panel.find("span", class_="px-0")
            sprite_el = panel.find("img", class_="sprite")
            if not name_el:
                return None
            types = [img["alt"] for img in panel.find_all("img", class_="elemental-type")]
            stats_data = _parse_stats(soup)
            weak_data = _parse_weaknesses(soup)
            entry = {
                "name": name_el.text.strip().replace("/wbr>", "/"),
                "types": types,
                "stats": stats_data.get("fusion1") if stats_data else {},
                "weaknesses": weak_data.get("fusion1"),
            }
            return {f"{a}.{a}": entry}

        stack = soup.find("div", id="details-stack")
        if not stack:
            return None
        panels = stack.find_all("div", class_="fusionDisplay")
        if len(panels) < 2:
            return None

        stats_data = _parse_stats(soup)
        weak_data = _parse_weaknesses(soup)

        result = {}
        for idx, (key, fk) in enumerate([(f"{a}.{b}", "fusion1"), (f"{b}.{a}", "fusion2")]):
            panel = panels[idx]
            name_el = panel.find("span", class_="px-0")
            sprite_el = panel.find("img", class_="sprite")
            if not name_el:
                continue
            types = [img["alt"] for img in panel.find_all("img", class_="elemental-type")]
            result[key] = {
                "name": name_el.text.strip().replace("/wbr>", "/"),
                "types": types,
                "stats": stats_data.get(fk) if stats_data else {},
                "weaknesses": weak_data.get(fk),
            }
        return result or None

    except Exception as e:
        logger.debug(f"Parse error for {a}.{b}: {e}")
        return None


CDN_CUSTOM = "https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/"
CDN_GENERATED = "https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/generated/"


def _sprite_urls_to_try(sprite_url: str | None, pid: str) -> list[str]:
    urls: list[str] = []
    if sprite_url:
        urls.append(sprite_url)
        if CDN_GENERATED in sprite_url:
            custom_url = sprite_url.replace(CDN_GENERATED, CDN_CUSTOM)
            if custom_url not in urls:
                urls.append(custom_url)

    direct = f"{CDN_CUSTOM}{pid}.png"
    if direct not in urls:
        urls.append(direct)

    generated = f"{CDN_GENERATED}{pid}.png"
    if generated not in urls:
        urls.append(generated)

    return urls


def download_sprite(sprite_url: str | None, key: str) -> str | None:
    pid = key.lstrip("#")
    parts = pid.split(".")
    try:
        head_id = int(parts[0])
    except (ValueError, IndexError):
        return None
    subdir = _sprite_subdir(head_id)
    filename = f"{pid}.png"
    dest = subdir / filename
    start = ((head_id - 1) // 100) * 100 + 1
    rel = f"{start:03d}-{start + 99:03d}/{filename}"
    if dest.exists():
        return rel

    resp = None
    for url in _sprite_urls_to_try(sprite_url, pid):
        resp = _get(url, timeout=SPRITE_TIMEOUT)
        if resp is not None and resp.content:
            break

    if resp is None or not resp.content:
        return None
    try:
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(resp.content)
        tmp.rename(dest)
        return rel
    except Exception as e:
        logger.debug(f"Sprite write failed for {key}: {e}")
        return None


_save_lock = threading.Lock()


_master_cache: dict = {}
_master_cache_loaded = False


def save_batch(new_entries: dict) -> None:
    if not new_entries:
        return
    global _master_cache, _master_cache_loaded
    with _save_lock:
        try:
            if not _master_cache_loaded:
                if CACHE_FILE.exists():
                    with CACHE_FILE.open("r", encoding="utf-8") as f:
                        _master_cache = json.load(f)
                _master_cache_loaded = True
            _master_cache.update(new_entries)
            tmp = CACHE_FILE.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(_master_cache, f)
            tmp.replace(CACHE_FILE)
            logger.info(f"Saved batch of {len(new_entries)} entries (total: {len(_master_cache)})")
        except Exception as e:
            logger.error(f"Failed to save batch: {e}")


def run(workers: int, batch_size: int, sprites_only: bool, dry_run: bool) -> None:
    cache = load_cache()
    pokemon_ids = load_pokemon_ids()

    if sprites_only:
        logger.info("--sprites-only: downloading sprites for existing entries with missing sprite files")
        _run_sprites_only(cache, workers)
        return

    missing = find_missing_pairs(cache, pokemon_ids)

    if not missing:
        logger.info("Nothing to fetch — all pairs are present.")
        return

    if dry_run:
        logger.info(f"[dry-run] Would fetch {len(missing)} pairs. Exiting.")
        return

    total = len(missing)
    fetched = 0
    skipped = 0
    batch: dict = {}

    logger.info(f"Starting fetch: {total} pairs, {workers} workers, batch_size={batch_size}")

    def process(pair: tuple[int, int]) -> dict | None:
        a, b = pair
        result = fetch_pair(a, b)
        if result:
            for key, entry in result.items():
                download_sprite(None, key)
        return result

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process, pair): pair for pair in missing}
        for future in as_completed(futures):
            pair = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.warning(f"Worker error for {pair}: {e}")
                result = None

            if result:
                batch.update(result)
                fetched += len(result)
            else:
                skipped += 1

            if len(batch) >= batch_size:
                save_batch(batch)
                batch = {}

            done = fetched + skipped
            if done % 500 == 0 or done == total:
                pct = done / total * 100
                logger.info(f"Progress: {done}/{total} ({pct:.1f}%) — fetched={fetched} skipped={skipped}")

    if batch:
        save_batch(batch)

    logger.info(f"Done. Fetched {fetched} entries, skipped {skipped} pairs.")


def _run_sprites_only(cache: dict, workers: int = 8) -> None:
    missing_sprites = [
        key
        for key in cache
        if not _sprite_dest_exists(key)
    ]
    total = len(missing_sprites)
    logger.info(f"Downloading sprites for {total} entries with {workers} workers")
    saved = 0

    def _fetch_one(key):
        rel = download_sprite(None, key)
        return key, rel

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_fetch_one, item): item for item in missing_sprites}
        done = 0
        flush_every = max(500, batch_flush_size := 1000)
        for future in as_completed(futures):
            done += 1
            try:
                key, rel = future.result()
            except Exception:
                continue
            if rel:
                saved += 1
            if done % 1000 == 0 or done == total:
                logger.info(f"Progress: {done}/{total} ({100*done/total:.1f}%) saved={saved}")

    logger.info(f"Downloaded {saved} sprites out of {total} attempted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch missing fusion pair data and sprites")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent HTTP workers (default: 8)")
    parser.add_argument("--batch-size", type=int, default=200, help="Save to disk every N new entries (default: 200)")
    parser.add_argument("--sprites-only", action="store_true", help="Only download missing sprites for existing entries")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched without doing it")
    args = parser.parse_args()

    run(
        workers=args.workers,
        batch_size=args.batch_size,
        sprites_only=args.sprites_only,
        dry_run=args.dry_run,
    )
