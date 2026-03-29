import json
import random
import sys
from pathlib import Path

FUSION_DATA_PATH = Path("data") / "all_fusions_data.json"
SPRITES_DIR = Path("data") / "sprites"
MANIFEST_PATH = SPRITES_DIR / "manifest.json"
SAMPLE_SIZE = 100


def load_fusion_data():
    if not FUSION_DATA_PATH.exists():
        print(f"not found: {FUSION_DATA_PATH}")
        return None
    try:
        with FUSION_DATA_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"failed to load fusion data: {e}")
        return None


def load_manifest():
    if not MANIFEST_PATH.exists():
        return None
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def parse_fusion_id(raw):
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


def check_sprite_exists(id1, id2, manifest):
    if manifest:
        for key in [f"{id1}.{id2}", f"{id1}.{id2}.png"]:
            if key in manifest:
                return True
    for subdir in ["001-100", "101-200", "201-300", "301-400", "401-500", "501-600", "fusions"]:
        if (SPRITES_DIR / subdir / f"{id1}.{id2}.png").exists():
            return True
    return False


def main():
    fusion_data = load_fusion_data()
    if not fusion_data:
        return 1
    manifest = load_manifest()
    all_ids = list(fusion_data.keys())
    sample_ids = random.sample(all_ids, min(SAMPLE_SIZE, len(all_ids)))
    missing = []
    found = 0
    for fusion_id in sample_ids:
        parsed = parse_fusion_id(fusion_id)
        if not parsed:
            continue
        id1, id2 = parsed
        if check_sprite_exists(id1, id2, manifest):
            found += 1
        else:
            missing.append((id1, id2, fusion_id))
    total = len(fusion_data)
    sampled = len(sample_ids)
    print(f"sample={sampled} found={found} missing={len(missing)}")
    if missing:
        for i, (id1, id2, _) in enumerate(missing[:20], 1):
            print(f"  {i}. {id1}.{id2}")
        if len(missing) > 20:
            print(f"  ... +{len(missing) - 20} more")
    est = int((found / sampled) * total) if sampled else 0
    print(f"estimated coverage: ~{est}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
