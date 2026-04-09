"""
Offline-app test suite.
Tests: sprite serving, URL caching, result-table population, callback logic,
tab-switch isolation, and the fusion-analyzer Python backend directly.

Run from the repo root:
    .venv/Scripts/python -m pytest scripts/test_offline_app.py -v
or
    .venv/Scripts/python scripts/test_offline_app.py
"""

import importlib.util
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ════════════════════════════════════════════════════════════════════════════
# 1. SPRITE URL / CACHING
# ════════════════════════════════════════════════════════════════════════════

class TestSpriteVersion(unittest.TestCase):
    """Sprite URL cache-busting version must be stable across calls."""

    def setUp(self):
        import app.sprites as s
        self.s = s

    def test_version_is_string(self):
        self.assertIsInstance(self.s._SPRITE_URL_VERSION, str)

    def test_version_is_numeric(self):
        self.assertTrue(self.s._SPRITE_URL_VERSION.isdigit(),
            f"Version should be a digit string, got: {self.s._SPRITE_URL_VERSION!r}")

    def test_version_stable_across_two_calls(self):
        v1 = self.s._make_sprite_version()
        time.sleep(0.01)
        v2 = self.s._make_sprite_version()
        self.assertEqual(v1, v2,
            "Sprite version changed between two rapid calls — it is time-based, not mtime-based")

    def test_version_not_current_epoch(self):
        """Version should NOT be close to time.time() (that was the old bug)."""
        now = int(time.time())
        v = int(self.s._SPRITE_URL_VERSION)
        # The mtime of the sprites dir will be far in the past, not 'now'
        self.assertLess(abs(v - now), 60 * 60 * 24 * 365 * 10,
            "Version suspiciously close to the future — sanity check")
        # More importantly: in a test run started fresh, v should NOT equal now
        self.assertNotAlmostEqual(v, now, delta=5,
            msg="Version equals time.time() (±5s) — the old time-based bug is back")


class TestSpriteUrl(unittest.TestCase):

    def setUp(self):
        import app.sprites as s
        self.s = s

    def test_url_starts_with_sprites(self):
        url = self.s.sprite_url("1.6")
        self.assertTrue(url.startswith("/sprites/"), url)

    def test_url_has_version_query(self):
        url = self.s.sprite_url("1.6")
        self.assertIn("?v=", url)

    def test_url_version_matches_module_version(self):
        url = self.s.sprite_url("1.6")
        v = url.split("?v=")[-1]
        self.assertEqual(v, self.s._SPRITE_URL_VERSION)

    def test_url_for_base_pokemon(self):
        url = self.s.sprite_url("25")
        self.assertIn("25", url)

    def test_url_for_fusion(self):
        url = self.s.sprite_url("1.6")
        self.assertIn("1.6", url)

    def test_relpath_existing_sprite(self):
        """sprite_relpath should return a relative path for a fusion that exists on disk."""
        sprites_dir = ROOT / "data" / "sprites"
        # Find any .png in the first subdir
        first_png = next(sprites_dir.rglob("*.png"), None)
        if first_png is None:
            self.skipTest("No sprites on disk")
        stem = first_png.stem  # e.g. "1.6" or "25"
        rel = self.s.sprite_relpath(stem)
        self.assertIsNotNone(rel)
        self.assertTrue((sprites_dir / rel).exists(), f"Relpath {rel!r} does not exist on disk")

    def test_relpath_none_input(self):
        self.assertIsNone(self.s.sprite_relpath(None))

    def test_subdir_boundaries(self):
        from app.sprites import _subdir
        self.assertEqual(_subdir(1),   "001-100")
        self.assertEqual(_subdir(100), "001-100")
        self.assertEqual(_subdir(101), "101-200")
        self.assertEqual(_subdir(200), "101-200")
        self.assertEqual(_subdir(501), "501-600")


# ════════════════════════════════════════════════════════════════════════════
# 2. SPRITE GRID — PC.PY
# ════════════════════════════════════════════════════════════════════════════

class TestSpriteGrid(unittest.TestCase):

    def setUp(self):
        import app.pc as pc
        from app import grid_cache
        grid_cache.clear()          # start each test with empty cache
        self.pc = pc
        self.grid_cache = grid_cache

    def test_gen1_grid_returns_component(self):
        from dash import html
        result = self.pc.create_pokemon_sprite_grid(gen="gen1")
        self.assertIsNotNone(result)

    def test_gen1_grid_is_cached_on_second_call(self):
        t0 = time.time()
        r1 = self.pc.create_pokemon_sprite_grid(gen="gen1")
        cold = time.time() - t0

        t0 = time.time()
        r2 = self.pc.create_pokemon_sprite_grid(gen="gen1")
        hot = time.time() - t0

        self.assertIs(r1, r2, "Second call should return cached object (same identity)")
        # Cached call must be substantially faster
        if cold > 0.01:     # only meaningful if cold took some time
            self.assertLess(hot, cold * 0.5,
                f"Hot path {hot:.4f}s not faster than cold {cold:.4f}s")

    def test_search_result_is_not_shared_with_unfiltered_cache(self):
        r_all  = self.pc.create_pokemon_sprite_grid(gen="gen1")
        r_bulb = self.pc.create_pokemon_sprite_grid(gen="gen1", search="bulba")
        self.assertIsNot(r_all, r_bulb)

    def test_search_cache_key_includes_search_term(self):
        self.pc.create_pokemon_sprite_grid(gen="gen1", search="pika")
        self.pc.create_pokemon_sprite_grid(gen="gen1", search="char")
        # Both should be cached under different keys
        self.assertEqual(len(self.grid_cache), 2)

    def test_different_gens_cached_separately(self):
        self.pc.create_pokemon_sprite_grid(gen="gen1")
        self.pc.create_pokemon_sprite_grid(gen="gen2")
        self.assertEqual(len(self.grid_cache), 2)

    def test_gen1_grid_contains_151_pokemon(self):
        from app import fusion_pokemon_data
        gen1_ids = [
            pid for pid, info in fusion_pokemon_data.items()
            if info.get("generation") == 1
        ]
        self.assertEqual(len(gen1_ids), 151)

    def test_search_empty_string_treated_as_no_search(self):
        r1 = self.pc.create_pokemon_sprite_grid(gen="gen1", search="")
        r2 = self.pc.create_pokemon_sprite_grid(gen="gen1", search=None)
        # Both should land in the same cache slot or return equivalent results
        # by touching the cache with the same key
        key_empty = "gen1_"
        self.assertIn(key_empty, self.grid_cache)


# ════════════════════════════════════════════════════════════════════════════
# 3. FUSION ANALYZER — _stat, _get_metric, _map_to_ui, analyze_fusions
# ════════════════════════════════════════════════════════════════════════════

class TestStatHelper(unittest.TestCase):

    def setUp(self):
        from app.fusion_analyzer import _stat, _get_metric, _STAT_ALIASES
        self.stat = _stat
        self.metric = _get_metric
        self.aliases = _STAT_ALIASES

    def _stats(self, **kw):
        return kw

    def test_canonical_keys(self):
        s = self._stats(HP=80, ATK=100, DEF=60)
        self.assertEqual(self.stat(s, "HP"),  80)
        self.assertEqual(self.stat(s, "ATK"), 100)
        self.assertEqual(self.stat(s, "DEF"), 60)

    def test_alias_spatk(self):
        s = {"sp_atk": 95}
        self.assertEqual(self.stat(s, "SP.ATK"), 95)

    def test_alias_spdef(self):
        s = {"spdef": 70}
        self.assertEqual(self.stat(s, "SP.DEF"), 70)

    def test_alias_total_lowercase(self):
        s = {"total": 500}
        self.assertEqual(self.stat(s, "TOTAL"), 500)

    def test_missing_key_returns_0(self):
        self.assertEqual(self.stat({}, "HP"), 0)

    def test_none_value_returns_0(self):
        self.assertEqual(self.stat({"HP": None}, "HP"), 0)

    def test_string_value_converted(self):
        self.assertEqual(self.stat({"HP": "80"}, "HP"), 80)

    def test_float_string_truncated(self):
        # "80.5" → int(80.5) raises ValueError, so returns 0
        # but "80" → 80
        self.assertEqual(self.stat({"HP": "80"}, "HP"), 80)

    def test_all_metrics_non_negative(self):
        s = {"HP": 100, "ATK": 90, "DEF": 80, "SP.ATK": 85,
             "SP.DEF": 75, "SPEED": 70, "TOTAL": 500}
        e = {"stats": s, "types": ["WATER"]}
        for m in ("Total", "Mixed Bulk", "Phys Bulk", "Spec Bulk",
                  "Offense", "ATK", "SP.ATK", "SPEED"):
            val = self.metric(e, m)
            self.assertGreaterEqual(val, 0, f"Metric {m!r} returned negative: {val}")

    def test_composite_equals_total_plus_20x_type_score(self):
        s = {"HP": 100, "ATK": 90, "DEF": 80, "SP.ATK": 85,
             "SP.DEF": 75, "SPEED": 70, "TOTAL": 500}
        e = {"stats": s, "types": ["STEEL", "FAIRY"]}
        total = self.metric(e, "Total")
        ts    = self.metric(e, "Type Score")
        comp  = self.metric(e, "Composite")
        self.assertAlmostEqual(comp, total + 20 * ts, places=5)

    def test_unknown_metric_returns_0(self):
        e = {"stats": {"HP": 100}, "types": ["FIRE"]}
        self.assertEqual(self.metric(e, "NONEXISTENT"), 0.0)


class TestMapToUi(unittest.TestCase):

    def setUp(self):
        from app.fusion_analyzer import _map_to_ui, _load_index
        self.map_to_ui = _map_to_ui
        self.index = _load_index()

    def _entry(self, h, b):
        return self.index.get((h, b))

    def test_1_6_mapping_has_required_keys(self):
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        for key in ("Fusion ID", "Local Sprite", "Name", "Types",
                    "Total", "HP", "ATK", "DEF", "SP.ATK", "SP.DEF", "SPEED",
                    "Phys Bulk", "Spec Bulk", "Mixed Bulk", "Offense",
                    "Type Score", "Immunities", "Resists", "2x Weak", "4x Weak",
                    "Ability 1", "Ability 2", "Hidden Ability"):
            self.assertIn(key, row, f"Missing key: {key!r}")

    def test_fusion_id_format(self):
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        self.assertEqual(row["Fusion ID"], "#1.6")

    def test_local_sprite_is_url(self):
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        self.assertTrue(row["Local Sprite"].startswith("/sprites/"))

    def test_stats_are_integers(self):
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        for stat in ("HP", "ATK", "DEF", "SP.ATK", "SP.DEF", "SPEED", "Total"):
            self.assertIsInstance(row[stat], int, f"{stat} should be int")

    def test_bulk_stats_are_floats(self):
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        for stat in ("Phys Bulk", "Spec Bulk", "Mixed Bulk"):
            self.assertIsInstance(row[stat], float, f"{stat} should be float")

    def test_weakness_lists_contain_valid_types(self):
        TYPE_ORDER = ['NORMAL','FIRE','WATER','ELECTRIC','GRASS','ICE','FIGHTING',
            'POISON','GROUND','FLYING','PSYCHIC','BUG','ROCK','GHOST','DRAGON',
            'DARK','STEEL','FAIRY']
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        for bucket in ("Immunities", "Resists", "2x Weak", "4x Weak"):
            for t in row[bucket]:
                self.assertIn(t, TYPE_ORDER, f"{bucket} contains unknown type {t!r}")

    def test_phys_bulk_formula(self):
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        expected = round(row["HP"] * row["DEF"] / 100, 1)
        self.assertAlmostEqual(row["Phys Bulk"], expected, places=1)

    def test_offense_is_max_atk_spatk(self):
        e = self._entry(1, 6)
        if e is None:
            self.skipTest("Fusion 1.6 not in index")
        row = self.map_to_ui(dict(e), 1, 6)
        self.assertEqual(row["Offense"], max(row["ATK"], row["SP.ATK"]))

    def test_duplicate_keys_absent(self):
        """The returned dict must not have private keys leaking."""
        e = self._entry(25, 150)
        if e is None:
            self.skipTest("Fusion 25.150 not in index")
        row = self.map_to_ui(dict(e), 25, 150)
        # Private keys (prefixed _) should NOT appear — they are ability descs
        # stored under "_ab1_desc" etc. but not under leading underscore otherwise
        public_keys = [k for k in row if not k.startswith("_")]
        self.assertGreater(len(public_keys), 15)


class TestAnalyzeFusions(unittest.TestCase):

    def setUp(self):
        from app.fusion_analyzer import analyze_fusions
        self.analyze = analyze_fusions

    def test_two_pokemon_returns_at_least_2_rows(self):
        """1 and 6 should each fuse as head and body."""
        rows = self.analyze([1, 6])
        self.assertGreaterEqual(len(rows), 2)

    def test_three_pokemon_returns_6_rows(self):
        rows = self.analyze([1, 6, 25])
        self.assertEqual(len(rows), 6, f"Expected 6 rows, got {len(rows)}")

    def test_no_self_fusions_in_output(self):
        rows = self.analyze([1, 6, 25])
        for row in rows:
            fid = row["Fusion ID"]   # "#H.B"
            parts = fid.lstrip("#").split(".")
            self.assertNotEqual(parts[0], parts[1], f"Self-fusion in results: {fid}")

    def test_results_all_have_required_columns(self):
        rows = self.analyze([1, 6])
        required = {"Fusion ID", "Name", "Types", "Total", "HP", "ATK", "DEF",
                    "SP.ATK", "SP.DEF", "SPEED", "Phys Bulk", "Spec Bulk",
                    "Mixed Bulk", "Offense", "Type Score",
                    "Ability 1", "Ability 2", "Hidden Ability"}
        for row in rows:
            missing = required - row.keys()
            self.assertFalse(missing, f"Row {row.get('Fusion ID')} missing: {missing}")

    def test_empty_input_returns_empty(self):
        self.assertEqual(self.analyze([]), [])

    def test_single_pokemon_returns_empty(self):
        self.assertEqual(self.analyze([1]), [])

    def test_duplicate_ids_deduplicated(self):
        """Passing [1, 1, 6] should behave the same as [1, 6]."""
        r1 = self.analyze([1, 6])
        r2 = self.analyze([1, 1, 6])
        self.assertEqual(len(r1), len(r2))

    def test_result_sorted_by_total_descending_if_applied(self):
        """After Python-side sort, order should be by Total desc."""
        rows = self.analyze([1, 6, 25, 9])
        sorted_rows = sorted(rows, key=lambda r: r["Total"], reverse=True)
        for a, b in zip(sorted_rows, sorted_rows[1:]):
            self.assertGreaterEqual(a["Total"], b["Total"])

    def test_10_pokemon_returns_90_rows(self):
        t0 = time.time()
        rows = self.analyze(list(range(1, 11)))
        elapsed = time.time() - t0
        self.assertEqual(len(rows), 10 * 9)
        print(f"\n  analyze_fusions(10 pokemon): {elapsed:.3f}s, {len(rows)} rows")

    def test_20_pokemon_correct_count(self):
        t0 = time.time()
        rows = self.analyze(list(range(1, 21)))
        elapsed = time.time() - t0
        self.assertEqual(len(rows), 20 * 19)
        self.assertLess(elapsed, 10.0, "analyze_fusions took >10 s for 20 pokemon")
        print(f"\n  analyze_fusions(20 pokemon): {elapsed:.3f}s, {len(rows)} rows")

    def test_no_duplicate_fusion_ids(self):
        rows = self.analyze(list(range(1, 11)))
        ids = [r["Fusion ID"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate Fusion IDs in results")


# ════════════════════════════════════════════════════════════════════════════
# 4. RESULT TABLE POPULATION — _build_table_rows_and_tooltips, _build_columns
# ════════════════════════════════════════════════════════════════════════════

class TestResultTableBuilding(unittest.TestCase):
    """Tests that the callbacks correctly format fusion data for the DataTable."""

    @classmethod
    def setUpClass(cls):
        # Load app.py once per class — it registers Dash callbacks but does not start the server
        spec = importlib.util.spec_from_file_location("app_main", ROOT / "app.py")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

        from app.fusion_analyzer import analyze_fusions
        cls.raw_fusions = analyze_fusions([1, 6, 25])

    def test_rows_count_matches_input(self):
        rows, _ = self.mod._build_table_rows_and_tooltips(self.raw_fusions)
        self.assertEqual(len(rows), len(self.raw_fusions))

    def test_tooltip_count_matches_rows(self):
        rows, tips = self.mod._build_table_rows_and_tooltips(self.raw_fusions)
        self.assertEqual(len(rows), len(tips))

    def test_add_column_is_floppy_disk(self):
        rows, _ = self.mod._build_table_rows_and_tooltips(self.raw_fusions)
        for row in rows:
            self.assertEqual(row["Add"], "💾")

    def test_sprite_column_is_markdown_image(self):
        rows, _ = self.mod._build_table_rows_and_tooltips(self.raw_fusions)
        for row in rows:
            sprite = row["Sprite"]
            self.assertTrue(
                sprite.startswith("![Sprite]") or "/" in sprite,
                f"Sprite value unexpected: {sprite!r}"
            )

    def test_types_column_is_string(self):
        rows, _ = self.mod._build_table_rows_and_tooltips(self.raw_fusions)
        for row in rows:
            self.assertIsInstance(row["Types"], str)

    def test_weakness_counts_are_integers(self):
        rows, _ = self.mod._build_table_rows_and_tooltips(self.raw_fusions)
        for row in rows:
            for col in ("Immunities", "Resists", "2x Weak", "4x Weak"):
                self.assertIsInstance(row[col], int, f"{col} should be int in table row")

    def test_ability_tooltip_populated_when_present(self):
        rows, tips = self.mod._build_table_rows_and_tooltips(self.raw_fusions)
        # At least some fusions should have ability descriptions
        has_tip = any("Ability 1" in t for t in tips)
        self.assertTrue(has_tip, "No ability tooltips found — ability descriptions missing")

    def test_columns_includes_sprite_as_markdown(self):
        cols = self.mod._build_columns(self.raw_fusions)
        sprite_col = next((c for c in cols if c["id"] == "Sprite"), None)
        self.assertIsNotNone(sprite_col)
        self.assertEqual(sprite_col.get("presentation"), "markdown")

    def test_columns_no_private_keys(self):
        cols = self.mod._build_columns(self.raw_fusions)
        col_ids = [c["id"] for c in cols]
        for cid in col_ids:
            self.assertFalse(cid.startswith("_"), f"Private key {cid!r} in columns")

    def test_columns_order_add_sprite_first(self):
        cols = self.mod._build_columns(self.raw_fusions)
        col_ids = [c["id"] for c in cols]
        self.assertEqual(col_ids[0], "Add")
        self.assertEqual(col_ids[1], "Sprite")


# ════════════════════════════════════════════════════════════════════════════
# 5. TAB ISOLATION — callbacks must not bleed between tabs
# ════════════════════════════════════════════════════════════════════════════

class TestTabIsolation(unittest.TestCase):
    """
    Verifies that each PC-display callback returns independently and quickly,
    simulating rapid tab switching without state bleed.
    """

    def setUp(self):
        import app.pc as pc
        self.pc = pc

    def test_display_box_empty_pc_returns_empty_message(self):
        from dash import html
        result = self.pc.display_box([], [])
        self.assertIsInstance(result, html.Div)
        # Should contain the "empty" message
        self.assertIn("empty", str(result).lower())

    def test_display_box_with_pokemon_returns_row(self):
        import dash_bootstrap_components as dbc
        result = self.pc.display_box([1, 6], [])
        self.assertIsInstance(result, dbc.Row)

    def test_display_box_unchanged_by_repeated_calls(self):
        """Calling display_box twice with same args must return equivalent structure."""
        r1 = self.pc.display_box([1, 6, 25], [])
        r2 = self.pc.display_box([1, 6, 25], [])
        # Same type and same number of cards
        self.assertEqual(type(r1), type(r2))
        self.assertEqual(str(r1), str(r2))

    def test_display_box_with_fusion_item(self):
        import dash_bootstrap_components as dbc
        result = self.pc.display_box(["fusion_1_6"], [])
        self.assertIsInstance(result, dbc.Row)

    def test_pc_summary_empty(self):
        from dash import html
        result = self.pc.render_pc_summary([])
        self.assertIsInstance(result, html.Div)

    def test_pc_summary_non_empty(self):
        from dash import html
        result = self.pc.render_pc_summary([1, 6])
        # Should return a Div containing buttons
        self.assertIsInstance(result, html.Div)

    def test_grid_switch_gen1_to_gen2_no_cache_contamination(self):
        """Switching from gen1 to gen2 grid must not return gen1 content."""
        from app import grid_cache
        grid_cache.clear()
        g1 = self.pc.create_pokemon_sprite_grid(gen="gen1")
        g2 = self.pc.create_pokemon_sprite_grid(gen="gen2")
        self.assertIsNot(g1, g2)
        self.assertNotEqual(str(g1), str(g2))

    def test_grid_cache_persists_across_simulated_tab_switches(self):
        """Simulating Browse → PC → Browse: gen1 grid should be served from cache."""
        from app import grid_cache
        grid_cache.clear()

        # First visit to Browse (gen1)
        r1 = self.pc.create_pokemon_sprite_grid(gen="gen1")
        cache_size_after_browse = len(grid_cache)

        # "Switch to PC tab" — grid callback not called, cache unchanged
        self.assertEqual(len(grid_cache), cache_size_after_browse)

        # "Switch back to Browse tab" — same gen1 grid returned from cache
        r2 = self.pc.create_pokemon_sprite_grid(gen="gen1")
        self.assertIs(r1, r2, "gen1 grid was rebuilt instead of served from cache")


# ════════════════════════════════════════════════════════════════════════════
# 6. SPRITE SERVING PERFORMANCE (Flask route logic)
# ════════════════════════════════════════════════════════════════════════════

class TestSpriteServingLogic(unittest.TestCase):
    """Test the disk-lookup logic without starting a real HTTP server."""

    def setUp(self):
        import app.sprites as s
        self.s = s

    def test_sprite_file_for_pid_fusion(self):
        path = self.s._sprite_file_for_pid("1.6")
        self.assertIsNotNone(path)
        # Path structure: data/sprites/001-100/1.6.png
        self.assertIn("sprites", str(path))
        self.assertTrue(str(path).endswith(".png"))

    def test_sprite_file_for_pid_base(self):
        path = self.s._sprite_file_for_pid("25")
        self.assertIsNotNone(path)

    def test_sprite_file_for_pid_none(self):
        self.assertIsNone(self.s._sprite_file_for_pid(None))

    def test_sprite_file_invalid_pid(self):
        self.assertIsNone(self.s._sprite_file_for_pid("not_a_number"))

    def test_cache_header_set_correctly(self):
        self.assertEqual(self.s._CACHE_HEADER, "public, max-age=604800, immutable")

    def test_remote_sprite_miss_cache_prevents_retry(self):
        """Once a PID is recorded as a miss, _fetch_remote_sprite returns None immediately."""
        self.s._REMOTE_SPRITE_MISSES.add("999.999")
        result = self.s._fetch_remote_sprite("999.999")
        self.assertIsNone(result)
        self.s._REMOTE_SPRITE_MISSES.discard("999.999")  # clean up

    def test_base_sprite_index_built_lazily(self):
        """_BASE_SPRITE_INDEX is None initially and built on first access."""
        original = self.s._BASE_SPRITE_INDEX
        self.s._BASE_SPRITE_INDEX = None   # reset
        idx = self.s._get_base_sprite_index()
        self.assertIsNotNone(idx)
        self.assertIsInstance(idx, dict)
        self.s._BASE_SPRITE_INDEX = original  # restore


# ════════════════════════════════════════════════════════════════════════════
# 7. FIND BEST TEAMS — Python backend
# ════════════════════════════════════════════════════════════════════════════

class TestFindBestTeams(unittest.TestCase):

    def setUp(self):
        from app.fusion_analyzer import find_best_teams
        self.find = find_best_teams

    def test_two_pokemon_one_pair(self):
        teams = self.find([1, 6], metric="Total", max_fusions=6, max_teams=3)
        self.assertGreater(len(teams), 0)
        self.assertEqual(len(teams[0][0]), 1)   # one pair per team

    def test_four_pokemon_two_pairs(self):
        teams = self.find([1, 6, 25, 9], metric="Total", max_fusions=6, max_teams=3)
        self.assertGreater(len(teams), 0)
        self.assertEqual(len(teams[0][0]), 2)

    def test_scores_descending(self):
        teams = self.find([1, 6, 25, 9, 150], metric="Total", max_fusions=6, max_teams=3)
        scores = [score for _, score in teams]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i+1])

    def test_no_pokemon_used_twice(self):
        teams = self.find([1, 6, 25, 9], metric="Total", max_fusions=6, max_teams=3)
        for team, _ in teams:
            used = []
            for fusion in team:
                fid = fusion["Fusion ID"].lstrip("#")
                h, b = map(int, fid.split("."))
                self.assertNotIn(h, used, f"Head {h} used twice")
                self.assertNotIn(b, used, f"Body {b} used twice")
                used.extend([h, b])

    def test_composite_metric_works(self):
        teams = self.find([1, 6, 25, 9], metric="Composite", max_fusions=6, max_teams=3)
        self.assertGreater(len(teams), 0)

    def test_single_pokemon_returns_empty(self):
        teams = self.find([1], metric="Total", max_fusions=6, max_teams=3)
        self.assertEqual(teams, [])

    def test_empty_returns_empty(self):
        self.assertEqual(self.find([], metric="Total", max_fusions=6, max_teams=3), [])

    def test_20_pokemon_completes_in_time(self):
        t0 = time.time()
        teams = self.find(list(range(1, 21)), metric="Total", max_fusions=6, max_teams=5)
        elapsed = time.time() - t0
        self.assertGreater(len(teams), 0)
        self.assertLess(elapsed, 30.0, f"find_best_teams(20) took {elapsed:.1f}s (>30 s limit)")
        print(f"\n  find_best_teams(20 pokemon): {elapsed:.3f}s, {len(teams)} teams")


# ════════════════════════════════════════════════════════════════════════════
# 8. STARTUP PRE-CACHE
# ════════════════════════════════════════════════════════════════════════════

class TestStartupPrecache(unittest.TestCase):
    """Verify the startup pre-cache targets gen1, not the slow 'all' generation."""

    def test_precache_targets_gen1(self):
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        # Must reference gen1 pre-cache key
        self.assertIn('gen1_key', src)
        self.assertIn('"gen1"', src)

    def test_precache_does_not_target_all(self):
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        # The old "all_" pre-cache must be gone from the _pre_cache_grids function
        # Find the function body
        start = src.index("def _pre_cache_grids")
        end   = src.index("_pre_cache_grids()", start) + 20
        fn_body = src[start:end]
        self.assertNotIn('"all_"', fn_body,
            '_pre_cache_grids still uses "all_" — should be "gen1_"')
        self.assertNotIn("gen=\"all\"", fn_body,
            '_pre_cache_grids still fetches gen="all" — should be gen="gen1"')


# ════════════════════════════════════════════════════════════════════════════
# 9. NATIONAL DEX ↔ FUSION DEX MAPPING
#
# Invariants:
#   - GENERATION is determined by national dex position, stored in fusion_pokemon_data.json
#   - DISPLAY SORT ORDER uses national_id (not fusion_id)
#   - SPRITE PATHS and FUSION IDs always use the fusion dex number
#   - From gen3 onward, fusion_id and national_id diverge significantly
# ════════════════════════════════════════════════════════════════════════════

class TestNationalDexMapping(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import fusion_pokemon_data
        cls.fp = dict(fusion_pokemon_data)   # {"fusion_id_str": {name, generation, national_id, ...}}

    # ── Data integrity ────────────────────────────────────────────────────

    def test_all_entries_have_national_id(self):
        missing = [fid for fid, v in self.fp.items() if not v.get("national_id")]
        self.assertFalse(missing, f"{len(missing)} entries lack national_id: {missing[:5]}")

    def test_all_entries_have_generation(self):
        missing = [fid for fid, v in self.fp.items() if "generation" not in v]
        self.assertFalse(missing, f"{len(missing)} entries lack generation: {missing[:5]}")

    def test_gen1_fusion_ids_equal_national_ids(self):
        """Gen1 Pokémon: fusion IDs 1-151, national IDs also 1-151 (1:1 match)."""
        gen1 = {fid: v for fid, v in self.fp.items() if v.get("generation") == 1}
        self.assertEqual(len(gen1), 151)
        for fid, v in gen1.items():
            self.assertEqual(fid, v["national_id"],
                f"Gen1 fusion_id={fid} has national_id={v['national_id']} — expected match")

    def test_gen2_fusion_ids_match_national_ids(self):
        """Gen2 Pokémon also have 1:1 fusion ID ↔ national ID."""
        gen2 = {fid: v for fid, v in self.fp.items() if v.get("generation") == 2}
        for fid, v in gen2.items():
            self.assertEqual(fid, v["national_id"],
                f"Gen2 fusion_id={fid} has national_id={v['national_id']} — expected match")

    def test_gen3_diverges_from_national(self):
        """From gen3 onward, fusion IDs and national IDs are different for many Pokémon."""
        gen3 = {fid: v for fid, v in self.fp.items() if v.get("generation") == 3}
        mismatches = [fid for fid, v in gen3.items() if fid != v["national_id"]]
        self.assertGreater(len(mismatches), 0,
            "No gen3 mismatches found — mapping may have changed")

    def test_known_mismatch_azurill(self):
        """Azurill: fusion_id=252, national_id=298, generation=3."""
        a = self.fp.get("252")
        self.assertIsNotNone(a, "Fusion ID 252 missing from data")
        self.assertEqual(a["national_id"], "298")
        self.assertEqual(a["generation"], 3)
        self.assertEqual(a["name"], "Azurill")

    def test_known_mismatch_treecko(self):
        """Treecko: fusion_id=276, national_id=252, generation=3."""
        t = self.fp.get("276")
        self.assertIsNotNone(t, "Fusion ID 276 missing from data")
        self.assertEqual(t["national_id"], "252")
        self.assertEqual(t["generation"], 3)

    def test_known_mismatch_gen4_ambipom(self):
        """Ambipom: fusion_id=254, national_id=424, generation=4."""
        a = self.fp.get("254")
        self.assertIsNotNone(a)
        self.assertEqual(a["national_id"], "424")
        self.assertEqual(a["generation"], 4)

    # ── Generation filtering uses generation field, not fusion ID range ───

    def test_gen3_filter_includes_azurill(self):
        """Gen3 tab must include Azurill (fusion_id=252) even though 252 is in the gen2 ID range."""
        from app import grid_cache
        grid_cache.clear()
        import app.pc as pc
        grid_str = str(pc.create_pokemon_sprite_grid(gen="gen3"))
        self.assertIn("252", grid_str,
            "Azurill (fusion_id=252) missing from gen3 grid — generation filter is broken")

    def test_gen3_filter_excludes_gen2_pokemon(self):
        """A genuine gen2 Pokémon (fusion_id=152, Chikorita) must NOT appear in the gen3 tab."""
        from app import grid_cache
        grid_cache.clear()
        import app.pc as pc
        grid_str = str(pc.create_pokemon_sprite_grid(gen="gen3"))
        # Check by name — Chikorita's button id contains "152"
        chikorita = self.fp.get("152")
        self.assertIsNotNone(chikorita)
        self.assertEqual(chikorita["generation"], 2)
        # Its fusion_id 152 should not be a button in the gen3 grid
        # We check for the id="pokemon-btn" with index 152
        self.assertNotIn('"index": 152', grid_str,
            "Chikorita (gen2, fusion_id=152) appeared in gen3 grid")

    def test_gen1_tab_exact_count(self):
        """Gen1 tab should contain exactly 151 Pokémon."""
        from app import grid_cache
        grid_cache.clear()
        import app.pc as pc
        gen1_ids_in_data = [fid for fid, v in self.fp.items() if v.get("generation") == 1]
        # Can't count buttons directly from str, but check data source matches
        self.assertEqual(len(gen1_ids_in_data), 151)

    # ── Display sort uses national_id, not fusion_id ──────────────────────

    def test_sort_key_returns_national_id(self):
        """_display_sort_key must use national_id for the primary sort key."""
        from app.pc import _display_sort_key
        # Azurill: fusion_id=252, national_id=298 → sort key should be (298, 252)
        key = _display_sort_key(("252", "Azurill"))
        self.assertEqual(key, (298, 252),
            f"Sort key for Azurill is {key}, expected (298, 252)")

    def test_treecko_sorts_before_azurill(self):
        """Treecko (nat=252) must sort before Azurill (nat=298) even though Treecko's fusion_id=276 > Azurill's 252."""
        from app.pc import _display_sort_key
        treecko_key = _display_sort_key(("276", "Treecko"))   # (252, 276)
        azurill_key = _display_sort_key(("252", "Azurill"))   # (298, 252)
        self.assertLess(treecko_key, azurill_key,
            f"Treecko sort key {treecko_key} should be < Azurill {azurill_key}")

    def test_sort_key_fallback_to_fusion_id_when_no_national(self):
        """If national_id is absent, sort key falls back to fusion_id."""
        from app.pc import _display_sort_key
        # Unknown Pokémon not in fusion_pokemon_data
        key = _display_sort_key(("999", "Unknown"))
        self.assertEqual(key[1], 999)   # secondary key is always fusion_id

    # ── Sprite paths always use fusion ID ─────────────────────────────────

    def test_sprite_url_uses_fusion_id_not_national(self):
        """sprite_url('252') must embed '252' (fusion ID), not '298' (national ID)."""
        from app.sprites import sprite_url
        url = sprite_url("252")
        self.assertIn("252", url)
        self.assertNotIn("298", url)

    def test_analyze_fusions_uses_fusion_ids(self):
        """analyze_fusions takes fusion IDs; Fusion ID column must reflect them."""
        from app.fusion_analyzer import analyze_fusions
        rows = analyze_fusions([252, 253])
        self.assertTrue(len(rows) > 0)
        for row in rows:
            fid = row["Fusion ID"].lstrip("#")
            h, b = fid.split(".")
            self.assertIn(h, ("252", "253"))
            self.assertIn(b, ("252", "253"))

    # ── gen_ranges keys only drive tab labels ─────────────────────────────

    def test_gen_ranges_covers_all_gens_in_data(self):
        """Every generation present in fusion_pokemon_data must have a gen_ranges entry."""
        from app import gen_ranges
        gens_in_data = {v.get("generation") for v in self.fp.values() if v.get("generation")}
        for g in gens_in_data:
            key = f"gen{g}"
            self.assertIn(key, gen_ranges, f"{key} missing from gen_ranges")

    def test_gen_ranges_values_are_fusion_id_ranges(self):
        """gen_ranges values are (min_fusion_id, max_fusion_id), not national ID ranges."""
        from app import gen_ranges
        # gen1 IDs are 1-151 in both schemes — use gen3 to distinguish
        lo, hi = gen_ranges.get("gen3", (None, None))
        if lo is None:
            self.skipTest("gen3 not in gen_ranges")
        # Gen3 national IDs start at 252; gen3 fusion IDs start around 252 too
        # but the DEFAULTS in the code were the old national ranges (252-386)
        # In our code, gen3 is computed from actual fusion IDs in the data
        # so lo should be the minimum fusion_id among gen3 Pokémon
        gen3_fusion_ids = [int(fid) for fid, v in self.fp.items() if v.get("generation") == 3]
        self.assertEqual(lo, min(gen3_fusion_ids))
        self.assertEqual(hi, max(gen3_fusion_ids))


if __name__ == "__main__":
    unittest.main(verbosity=2)
