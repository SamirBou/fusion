import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def check_file(path, description, required=True):
    if not path.exists():
        if required:
            print(f"MISSING: {description} at {path}")
            return False
        else:
            print(f"optional missing: {description}")
            return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        size_mb = path.stat().st_size / (1024 * 1024)
        entry_count = len(data) if isinstance(data, (dict, list)) else "N/A"
        print(f"OK  {description} | {size_mb:.2f} MB | {entry_count} entries")
        return True
    except json.JSONDecodeError as e:
        print(f"CORRUPT: {description} | {e}")
        return False
    except Exception as e:
        print(f"ERROR: {description} | {e}")
        return False


def check_directory(path, description, required=True, count_files=False):
    if not path.exists() or not path.is_dir():
        if required:
            print(f"MISSING: {description} at {path}")
            return False
        else:
            print(f"optional missing: {description}")
            return None
    if count_files:
        file_count = sum(1 for _ in path.rglob("*") if _.is_file())
        print(f"OK  {description} | {file_count} files")
    else:
        print(f"OK  {description}")
    return True


def validate_fusion_data_schema(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print("FAIL: fusion data must be a dict")
            return False
        sample_size = min(5, len(data))
        required_keys = {"name", "types"}
        for fusion_id, entry in list(data.items())[:sample_size]:
            if not isinstance(entry, dict):
                print(f"FAIL: entry {fusion_id} is not a dict")
                return False
            missing = required_keys - entry.keys()
            if missing:
                print(f"WARN: {fusion_id} missing keys: {missing}")
        print(f"OK  schema valid (sampled {sample_size} entries)")
        return True
    except Exception as e:
        print(f"FAIL: schema validation | {e}")
        return False


def main():
    results = []
    results.append(check_file(Path("data/all_fusions_data.json"), "all_fusions_data.json", required=True))
    check_file(Path("data/pokemon_generations.json"), "pokemon_generations.json", required=False)
    check_file(Path("data/fusion_pokemon_data.json"), "fusion_pokemon_data.json", required=False)
    check_file(Path("data/fusion_to_national.json"), "fusion_to_national.json", required=False)
    sprites_dir = Path("data/sprites")
    results.append(check_directory(sprites_dir, "data/sprites", required=True))
    if sprites_dir.exists():
        for subdir_name in ["001-100", "101-200", "201-300", "301-400", "401-500", "501-600"]:
            check_directory(sprites_dir / subdir_name, subdir_name, required=False)
        check_directory(sprites_dir / "fusions", "fusions", required=False)
        check_file(sprites_dir / "manifest.json", "manifest.json", required=False)
    fusion_data_path = Path("data/all_fusions_data.json")
    if fusion_data_path.exists():
        validate_fusion_data_schema(fusion_data_path)
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    print(f"\npassed={passed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
