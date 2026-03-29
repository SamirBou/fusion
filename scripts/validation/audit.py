import json
from pathlib import Path

fpd = json.load(open("data/fusion_pokemon_data.json"))
ftn = json.load(open("data/fusion_to_national.json"))
apd = json.load(open("data/all_fusions_data.json"))
pg = json.load(open("data/pokemon_generations.json"))
sprites = Path("data/sprites")

print("=== DATA FILE SIZES ===")
print(f"fusion_pokemon_data : {len(fpd)} entries")
print(f"fusion_to_national  : {len(ftn)} entries")
print(f"all_fusions_data    : {len(apd)} entries")
print(f"pokemon_generations : {len(pg)} entries")

print("\n=== SPRITE COVERAGE ===")
missing_sprites = []
wrong_subdir = []
for fid in sorted(fpd.keys(), key=int):
    fid_int = int(fid)
    start = ((fid_int - 1) // 100) * 100 + 1
    expected = sprites / f"{start:03d}-{start+99:03d}" / f"{fid_int}.png"
    if not expected.exists():
        anywhere = list(sprites.rglob(f"{fid_int}.png"))
        if anywhere:
            wrong_subdir.append((fid, str(anywhere[0])))
        else:
            missing_sprites.append(fid)

print(f"Missing entirely     : {missing_sprites if missing_sprites else 'None'}")
print(f"Wrong subdirectory   : {wrong_subdir if wrong_subdir else 'None'}")

print("\n=== ID CONSISTENCY ===")
in_fpd_not_ftn = [k for k in fpd if k not in ftn]
in_ftn_not_fpd = [k for k in ftn if k not in fpd]
print(f"In fpd but not ftn   : {in_fpd_not_ftn if in_fpd_not_ftn else 'None'}")
print(f"In ftn but not fpd   : {in_ftn_not_fpd if in_ftn_not_fpd else 'None'}")

print("\n=== FUSION DATA COVERAGE ===")
total_possible = len(fpd) * (len(fpd) - 1)
print(f"Fusion entries       : {len(apd)}")
print(f"Possible fusions     : {total_possible}")
print(f"Coverage             : {len(apd)/total_possible*100:.1f}%")

fusion_sprites_missing = 0
for key in apd:
    parts = key.split(".")
    if len(parts) == 2:
        head = int(parts[0])
        start = ((head - 1) // 100) * 100 + 1
        p = sprites / f"{start:03d}-{start+99:03d}" / f"{key}.png"
        if not p.exists():
            fusion_sprites_missing += 1
print(f"Fusion sprites missing: {fusion_sprites_missing} / {len(apd)}")

print("\n=== GENERATION COVERAGE ===")
no_gen = [fid for fid, info in fpd.items() if not info.get("generation")]
print(f"Entries missing generation : {len(no_gen)} -> {no_gen[:10]}{'...' if len(no_gen)>10 else ''}")

no_nat = [fid for fid, info in fpd.items() if not info.get("national_id")]
print(f"Entries missing national_id : {len(no_nat)} -> {no_nat[:10]}{'...' if len(no_nat)>10 else ''}")

print("\n=== FUSIONS DATA ===")
sample = list(apd.items())[:1]
print(f"Sample all_fusions_data key/val: {sample}")

print("\n=== DONE ===")
