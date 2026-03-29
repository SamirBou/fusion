import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import pokemon_data
from app.sprites import sprite_relpath

SPRITES_DIR = REPO_ROOT / "data" / "sprites"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def iter_bucket_dirs():
    for child in sorted(SPRITES_DIR.iterdir()):
        if child.is_dir() and (child.name == "fusions" or (len(child.name) == 7 and child.name[3] == "-")):
            yield child


def iter_sprite_files():
    for bucket in iter_bucket_dirs():
        if bucket.name == "fusions":
            yield from sorted(bucket.rglob("*.png"))
        else:
            yield from sorted(bucket.glob("*.png"))


def inspect_image(path: Path) -> tuple[str | None, str | None]:
    try:
        with path.open("rb") as handle:
            if handle.read(8) != PNG_SIGNATURE:
                return "failure", "bad-png-signature"
    except OSError as exc:
        return "failure", f"read-error: {exc}"

    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            if width <= 0 or height <= 0:
                return "failure", "zero-dimensions"

            rgba = image.convert("RGBA")
            if rgba.getchannel("A").getbbox() is None:
                return "failure", "fully-transparent"
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return "warning", f"pillow-decode-warning: {exc}"
    return None, None


def check_expected_base_sprites() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    failures: list[tuple[str, str, str]] = []
    warnings: list[tuple[str, str, str]] = []
    for pid in sorted(pokemon_data.POKEMON_DATA, key=int):
        rel = sprite_relpath(pid)
        if not rel:
            failures.append((pid, "unresolved", "sprite_relpath returned no path"))
            continue
        path = SPRITES_DIR / rel
        if not path.exists():
            failures.append((pid, rel, "missing-file"))
            continue
        level, issue = inspect_image(path)
        if issue:
            target = failures if level == "failure" else warnings
            target.append((pid, rel, issue))
    return failures, warnings


def audit_all_sprite_files() -> tuple[dict[str, int], list[tuple[str, str]], list[tuple[str, str]]]:
    counts = {
        "total": 0,
        "base": 0,
        "fusion": 0,
    }
    failures: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []

    for index, path in enumerate(iter_sprite_files(), start=1):
        counts["total"] += 1
        stem = path.stem
        if stem.isdigit():
            counts["base"] += 1
        else:
            counts["fusion"] += 1

        level, issue = inspect_image(path)
        if issue:
            rel = str(path.relative_to(SPRITES_DIR)).replace("\\", "/")
            target = failures if level == "failure" else warnings
            target.append((rel, issue))

        if index % 10000 == 0:
            print(f"checked {index} files...")

    return counts, failures, warnings


def main() -> int:
    if not SPRITES_DIR.exists():
        print(f"missing sprites directory: {SPRITES_DIR}")
        return 1

    print("=== EXPECTED BASE SPRITES ===")
    base_failures, base_warnings = check_expected_base_sprites()
    print(f"expected base sprites: {len(pokemon_data.POKEMON_DATA)}")
    print(f"base failures       : {len(base_failures)}")
    print(f"base warnings       : {len(base_warnings)}")
    if base_failures:
        for pid, rel, issue in base_failures[:20]:
            print(f"  {pid}: {rel} -> {issue}")
    if base_warnings:
        for pid, rel, issue in base_warnings[:20]:
            print(f"  warn {pid}: {rel} -> {issue}")

    print("\n=== ALL SPRITE FILES ===")
    counts, file_failures, file_warnings = audit_all_sprite_files()
    print(f"total png files     : {counts['total']}")
    print(f"base png files      : {counts['base']}")
    print(f"fusion png files    : {counts['fusion']}")
    print(f"file failures       : {len(file_failures)}")
    print(f"file warnings       : {len(file_warnings)}")
    if file_failures:
        for rel, issue in file_failures[:20]:
            print(f"  {rel} -> {issue}")
    if file_warnings:
        for rel, issue in file_warnings[:20]:
            print(f"  warn {rel} -> {issue}")

    ok = not base_failures and not file_failures
    print("\n=== RESULT ===")
    if ok and (base_warnings or file_warnings):
        print("PASS WITH WARNINGS")
    else:
        print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())