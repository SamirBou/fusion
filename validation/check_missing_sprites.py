import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

FUSION_DATA_PATH = Path("data") / "all_fusions_data.json"
SPRITES_DIR = Path("data") / "sprites"
MANIFEST_PATH = SPRITES_DIR / "manifest.json"


def load_fusion_data():
    if not FUSION_DATA_PATH.exists():
        print(f"not found: {FUSION_DATA_PATH}")
        return None
    try:
        with FUSION_DATA_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"loaded {len(data)} fusions")
        return data
    except Exception as e:
        print(f"failed to load fusion data: {e}")
        return None


def load_manifest():
    if not MANIFEST_PATH.exists():
        return None
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(f"loaded manifest: {len(manifest)} entries")
        return manifest
    except Exception as e:
        print(f"failed to load manifest: {e}")
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
    sprite_keys = [f"{id1}.{id2}", f"{id1}.{id2}.png", f"#{id1}.{id2}", f"#{id1}.{id2}.png"]
    if manifest:
        for key in sprite_keys:
            if key in manifest:
                return True, "manifest"
    sprite_patterns = [SPRITES_DIR / f"{id1}.{id2}.png", SPRITES_DIR / "fusions" / f"{id1}.{id2}.png"]
    for subdir in SPRITES_DIR.glob("*-*"):
        if subdir.is_dir():
            sprite_patterns.append(subdir / f"{id1}.{id2}.png")
    for sprite_path in sprite_patterns:
        if sprite_path.exists():
            return True, str(sprite_path.relative_to(SPRITES_DIR))
    return False, None


def main():
    fusion_data = load_fusion_data()
    if not fusion_data:
        return 1
    manifest = load_manifest()
    total_fusions = 0
    missing_sprites = []
    found_sprites = 0
    for fusion_id, fusion_entry in fusion_data.items():
        total_fusions += 1
        parsed = parse_fusion_id(fusion_id)
        if not parsed:
            continue
        id1, id2 = parsed
        exists, _ = check_sprite_exists(id1, id2, manifest)
        if exists:
            found_sprites += 1
        else:
            missing_sprites.append((id1, id2, fusion_id))
    print(f"total={total_fusions} found={found_sprites} missing={len(missing_sprites)}")
    if missing_sprites:
        for i, (id1, id2, fusion_id) in enumerate(missing_sprites[:50], 1):
            print(f"  {i}. {id1}.{id2}")
        if len(missing_sprites) > 50:
            print(f"  ... +{len(missing_sprites) - 50} more")
        missing_file = Path("validation") / "missing_sprites.txt"
        missing_file.parent.mkdir(exist_ok=True)
        with missing_file.open("w") as f:
            for id1, id2, fusion_id in missing_sprites:
                f.write(f"{id1}.{id2}\n")
        print(f"saved to {missing_file}")
    return 0 if not missing_sprites else 1


if __name__ == "__main__":
    sys.exit(main())
