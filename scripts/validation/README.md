# Validation Scripts

Scripts to verify data and sprite integrity.

## Available Scripts

### check_missing_data.py
Validates all data files and directory structure.

**Usage:**
```bash
python validation/check_missing_data.py
```

**Checks:**
- Required data files exist and are valid JSON
- Optional data files (reports warnings)
- Sprite directory structure
- Fusion data schema validation
- Duplicate/unwanted files in root directory

**Latest Results:**
```
✓ Fusion data (main cache): 250,168 entries (201.18 MB)
✓ Pokemon generations: 1,025 entries
✓ Fusion pokemon data: 495 entries
✓ Sprite manifest: 251,102 entries (8.65 MB)
✓ Sprite directories: 501,504 total files
✓ No duplicate or unwanted files
```

### quick_sprite_check.py
Quick sprite availability check using random sampling.

**Usage:**
```bash
python validation/quick_sprite_check.py
```

**Checks:**
- Randomly samples 100 fusions
- Checks sprite availability in manifest and filesystem
- Estimates total coverage
- Fast execution (~5 seconds)

**Latest Results:**
```
✓ Sprites found: 100/100 (100%)
✓ Estimated total: ~250,168 of 250,168 sprites available
```

### check_missing_sprites.py
Validates sprite files against ALL fusion data (comprehensive check).

**Usage:**
```bash
python validation/check_missing_sprites.py
```

**Checks:**
- All fusions have corresponding sprite files
- Sprites exist in manifest or filesystem
- Reports missing sprites with statistics
- Saves full missing list to `validation/missing_sprites.txt`

**Warning**: This script validates all 250K+ fusions and may take several minutes. Use `quick_sprite_check.py` for faster validation.

## Running All Checks

To run validation checks:

```bash
# Quick data integrity check
python validation/check_missing_data.py

# Quick sprite coverage check (recommended)
python validation/quick_sprite_check.py

# Full sprite validation (slow, comprehensive)
python validation/check_missing_sprites.py
```

## Exit Codes

- `0`: All checks passed
- `1`: Some checks failed (see output for details)

## Latest Validation Summary

**Data Validation**: ✓ PASSED  
**Sprite Coverage**: ✓ 100% (based on sample)  
**Structure**: ✓ Clean and organized  

All critical files present and valid.
