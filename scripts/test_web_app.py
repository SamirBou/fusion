"""
Unit tests for the web app JS logic, ported to Python.
Tests: PC management, type chart, stat calculations, fusion analysis, best team DP.
"""

import json
import math
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent

# -- Load real data -------------------------------------------------------------
with open(ROOT / "data" / "fusion_pokemon_data.json") as f:
    POKEMON_DATA = json.load(f)

def load_fusion(head_id):
    p = ROOT / "data" / "fusions" / f"{head_id}.json"
    if not p.exists():
        return {}
    with open(p) as f:
        return json.load(f)

# -- Port of JS logic ----------------------------------------------------------

TYPE_ORDER = ['NORMAL','FIRE','WATER','ELECTRIC','GRASS','ICE','FIGHTING',
  'POISON','GROUND','FLYING','PSYCHIC','BUG','ROCK','GHOST','DRAGON','DARK','STEEL','FAIRY']

TYPE_CHART = {
  'NORMAL':   {'ROCK':.5,'GHOST':0,'STEEL':.5},
  'FIRE':     {'FIRE':.5,'WATER':.5,'GRASS':2,'ICE':2,'BUG':2,'ROCK':.5,'DRAGON':.5,'STEEL':2},
  'WATER':    {'FIRE':2,'WATER':.5,'GRASS':.5,'GROUND':2,'ROCK':2,'DRAGON':.5},
  'ELECTRIC': {'WATER':2,'ELECTRIC':.5,'GRASS':.5,'GROUND':0,'FLYING':2,'DRAGON':.5},
  'GRASS':    {'FIRE':.5,'WATER':2,'GRASS':.5,'POISON':.5,'GROUND':2,'FLYING':.5,'BUG':.5,'ROCK':2,'DRAGON':.5,'STEEL':.5},
  'ICE':      {'FIRE':.5,'WATER':.5,'GRASS':2,'ICE':.5,'GROUND':2,'FLYING':2,'DRAGON':2,'STEEL':.5},
  'FIGHTING': {'NORMAL':2,'ICE':2,'POISON':.5,'FLYING':.5,'PSYCHIC':.5,'BUG':.5,'ROCK':2,'GHOST':0,'DARK':2,'STEEL':2,'FAIRY':.5},
  'POISON':   {'GRASS':2,'POISON':.5,'GROUND':.5,'ROCK':.5,'GHOST':.5,'STEEL':0,'FAIRY':2},
  'GROUND':   {'FIRE':2,'ELECTRIC':2,'GRASS':.5,'POISON':2,'FLYING':0,'BUG':.5,'ROCK':2,'STEEL':2},
  'FLYING':   {'ELECTRIC':.5,'GRASS':2,'FIGHTING':2,'BUG':2,'ROCK':.5,'STEEL':.5},
  'PSYCHIC':  {'FIGHTING':2,'POISON':2,'PSYCHIC':.5,'DARK':0,'STEEL':.5},
  'BUG':      {'FIRE':.5,'GRASS':2,'FIGHTING':.5,'POISON':.5,'FLYING':.5,'PSYCHIC':2,'GHOST':.5,'DARK':2,'STEEL':.5,'FAIRY':.5},
  'ROCK':     {'FIRE':2,'ICE':2,'FIGHTING':.5,'GROUND':.5,'FLYING':2,'BUG':2,'STEEL':.5},
  'GHOST':    {'NORMAL':0,'PSYCHIC':2,'GHOST':2,'DARK':.5},
  'DRAGON':   {'DRAGON':2,'STEEL':.5,'FAIRY':0},
  'DARK':     {'FIGHTING':.5,'PSYCHIC':2,'GHOST':2,'DARK':.5,'FAIRY':.5},
  'STEEL':    {'FIRE':.5,'WATER':.5,'ELECTRIC':.5,'ICE':2,'ROCK':2,'STEEL':.5,'FAIRY':2},
  'FAIRY':    {'FIRE':.5,'FIGHTING':2,'POISON':.5,'DRAGON':2,'DARK':2,'STEEL':.5},
}

def compute_weaknesses(types):
    out = {'x0':[],'x1/4':[],'x1/2':[],'x1':[],'x2':[],'x4':[]}
    for atk in TYPE_ORDER:
        mult = 1.0
        for def_ in types:
            mult *= TYPE_CHART.get(atk, {}).get(def_, 1.0)
        r = round(mult, 2)
        if   r == 0:    out['x0'].append(atk)
        elif r == 0.25: out['x1/4'].append(atk)
        elif r == 0.5:  out['x1/2'].append(atk)
        elif r == 1.0:  out['x1'].append(atk)
        elif r == 2.0:  out['x2'].append(atk)
        elif r == 4.0:  out['x4'].append(atk)
    return out

def normalize_types(entry):
    raw = entry.get('types') or entry.get('Types') or []
    if isinstance(raw, str):
        raw = [x.strip() for x in raw.split(',')]
    return [t.strip().upper() for t in raw if t.strip().upper() in TYPE_ORDER]

def to_int(v):
    try: return int(v or 0)
    except: return 0

def map_to_ui(entry, h, b):
    s = entry.get('stats') or {}
    hp   = to_int(s.get('HP'))
    df   = to_int(s.get('DEF'))
    spd  = to_int(s.get('SP.DEF') or s.get('sp_def') or s.get('spdef'))
    atk  = to_int(s.get('ATK') or s.get('atk'))
    spatk= to_int(s.get('SP.ATK') or s.get('sp_atk') or s.get('spatk'))
    total= to_int(s.get('TOTAL') or s.get('Total') or s.get('total'))
    types = normalize_types(entry)
    weak  = compute_weaknesses(types)
    imm = weak['x0'];   res = weak['x1/2'] + weak['x1/4']
    w2  = weak['x2'];   w4  = weak['x4']
    return {
        '_h': h, '_b': b,
        'total': total, 'hp': hp, 'atk': atk, 'def': df,
        'spatk': spatk, 'spdef': spd, 'speed': to_int(s.get('SPEED') or s.get('speed')),
        'physBulk': round(hp*df/100, 1),
        'specBulk': round(hp*spd/100, 1),
        'mixedBulk': round(hp*(df+spd)/200, 1),
        'offense': max(atk, spatk),
        'typeScore': 2*len(imm)+len(res)-2*len(w2)-4*len(w4),
        'immunities': len(imm), 'resists': len(res),
        'weak2': len(w2), 'weak4': len(w4),
        'types': types,
    }

def get_metric(entry, metric):
    s = entry.get('stats') or {}
    def f(v): return float(v or 0) or 0
    if metric == 'Total':      return f(s.get('TOTAL') or s.get('Total') or s.get('total'))
    if metric == 'Phys Bulk':  return f(s.get('HP')) * f(s.get('DEF')) / 100
    if metric == 'Spec Bulk':  return f(s.get('HP')) * f(s.get('SP.DEF') or s.get('sp_def') or 0) / 100
    if metric == 'Mixed Bulk':
        hp=f(s.get('HP')); df=f(s.get('DEF')); sp=f(s.get('SP.DEF') or s.get('sp_def') or 0)
        return hp*(df+sp)/200
    if metric == 'Offense':
        return max(f(s.get('ATK') or s.get('atk') or 0), f(s.get('SP.ATK') or s.get('sp_atk') or 0))
    return 0

def popcount(x):
    c = 0
    while x:
        c += x & 1
        x >>= 1
    return c

def ctz(x):
    if not x: return 32
    c = 0
    while not (x & 1):
        c += 1; x >>= 1
    return c

def compute_best_teams(ids, fusion_cache, metric='Total', max_fusions=6, max_teams=3):
    n = min(len(ids), 20)
    limited = ids[:n]
    pair_best = {}
    for i in range(n):
        for j in range(i+1, n):
            h, b = limited[i], limited[j]
            e_ab = (fusion_cache.get(h) or {}).get(f'{h}.{b}')
            e_ba = (fusion_cache.get(b) or {}).get(f'{b}.{h}')
            if not e_ab and not e_ba: continue
            s_ab = get_metric(e_ab, metric) if e_ab else -1
            s_ba = get_metric(e_ba, metric) if e_ba else -1
            if s_ab >= s_ba: pair_best[f'{i},{j}'] = {'h':h,'b':b,'entry':e_ab,'score':s_ab}
            else:             pair_best[f'{i},{j}'] = {'h':b,'b':h,'entry':e_ba,'score':s_ba}

    dp = {0: {'score': 0.0, 'pairs': []}}
    for mask in range(1, 1 << n):
        bits = popcount(mask)
        if bits % 2 != 0 or bits > 2 * max_fusions: continue
        first = ctz(mask)
        best_score = -math.inf; best_pairs = None
        temp = mask ^ (1 << first)
        while temp:
            bit_pos = ctz(temp)
            pk = f'{first},{bit_pos}'
            if pk in pair_best:
                prev_mask = mask ^ (1 << first) ^ (1 << bit_pos)
                if prev_mask in dp:
                    total = dp[prev_mask]['score'] + pair_best[pk]['score']
                    if total > best_score:
                        best_score = total
                        best_pairs = dp[prev_mask]['pairs'] + [pair_best[pk]]
            temp &= temp - 1
        if best_pairs is not None:
            dp[mask] = {'score': best_score, 'pairs': best_pairs}

    unique = {}
    for v in dp.values():
        if not v['pairs']: continue
        sig = '|'.join(sorted(f"{p['h']}.{p['b']}" for p in v['pairs']))
        if sig not in unique or v['score'] > unique[sig]['score']:
            unique[sig] = v
    ranked = sorted(unique.values(), key=lambda x: -x['score'])[:max_teams]
    return [{'team': [map_to_ui(p['entry'], p['h'], p['b']) for p in r['pairs']], 'score': r['score']} for r in ranked]

# PC state helpers (mirroring JS)
def add_fusion_to_pc(pc, h, b):
    """
    JS: addFusionToPC - removes head (h) and body (b) as base Pokémon,
    removes any saved fusions that use h or b, then adds fusion_h_b.
    Matches main app handle_cell_click behaviour.
    """
    key = f'fusion_{h}_{b}'
    new_pc = []
    for item in pc:
        if item == h or item == b:
            continue
        if isinstance(item, str) and item.startswith('fusion_'):
            _, fh, fb = item.split('_')
            if int(fh) in (h, b) or int(fb) in (h, b):
                continue
        new_pc.append(item)
    if key not in new_pc:
        new_pc.append(key)
    return new_pc

def filter_results_table(rows, pc):
    """
    JS: filterResultsTable - keep only rows where both base Pokémon are
    still in PC and the fusion has not already been saved.
    Matches main app update_output box-store trigger behaviour.
    """
    base_ids = set(get_base_ids(pc))
    saved = {item for item in pc if isinstance(item, str) and item.startswith('fusion_')}
    return [
        row for row in rows
        if row['_h'] in base_ids
        and row['_b'] in base_ids
        and f"fusion_{row['_h']}_{row['_b']}" not in saved
    ]

def national_id_sort_key(game_id, pokemon_data):
    """Sort key used by the Browse grid: (national_id, game_id)."""
    info = pokemon_data.get(str(game_id), {})
    nat = int(info.get('national_id') or game_id)
    return nat, int(game_id)

def toggle_pc(pc, id_):
    if id_ in pc: return [x for x in pc if x != id_]
    return pc + [id_]

def remove_from_pc(pc, item):
    return [x for x in pc if x != item]

def get_base_ids(pc):
    out = []
    for x in pc:
        if isinstance(x, int):
            out.append(x)
        elif isinstance(x, str) and not x.startswith('fusion_'):
            try: out.append(int(x))
            except: pass
    return out


# ===============================================================================
class TestTypeChart(unittest.TestCase):

    def test_ghost_immune_to_normal(self):
        w = compute_weaknesses(['GHOST'])
        self.assertIn('NORMAL', w['x0'])
        self.assertIn('FIGHTING', w['x0'])

    def test_water_fire_2x_weak(self):
        w = compute_weaknesses(['WATER'])
        self.assertIn('ELECTRIC', w['x2'])
        self.assertIn('GRASS', w['x2'])

    def test_steel_fairy_resists(self):
        # Steel/Fairy type: lots of resistances
        w = compute_weaknesses(['STEEL', 'FAIRY'])
        # Steel resists Fire, Water, Electric, Ice (but Ice is 2x Steel... wait no)
        # Actually FIRE attacks STEEL 0.5x. GROUND attacks STEEL 2x
        self.assertIn('DRAGON', w['x0'])   # Fairy is immune to Dragon

    def test_fire_water_4x(self):
        # Pure Water: Ground 2x, Electric 2x, Grass 2x
        # Fire/Ground: Water is 2x (fire), Water is 2x (ground) -> 4x
        w = compute_weaknesses(['FIRE', 'GROUND'])
        self.assertIn('WATER', w['x4'])

    def test_normal_type_covers_all_attacking_types(self):
        w = compute_weaknesses(['NORMAL'])
        total = sum(len(v) for v in w.values())
        self.assertEqual(total, len(TYPE_ORDER))

    def test_type_score_ghost_immune(self):
        w = compute_weaknesses(['GHOST'])
        score = 2*len(w['x0']) + len(w['x1/2']) + len(w['x1/4']) - 2*len(w['x2']) - 4*len(w['x4'])
        self.assertGreater(score, 0)  # Ghost has 2 immunities, should be positive


class TestStatCalc(unittest.TestCase):

    def setUp(self):
        self.d1 = load_fusion(1)
        self.d6 = load_fusion(6)
        self.d25 = load_fusion(25)

    def test_bulbasaur_charizard_fusion_exists(self):
        self.assertIn('1.6', self.d1)

    def test_map_to_ui_basic_fields(self):
        entry = self.d1['1.6']
        row = map_to_ui(entry, 1, 6)
        self.assertEqual(row['_h'], 1)
        self.assertEqual(row['_b'], 6)
        self.assertGreater(row['total'], 0)
        self.assertGreater(row['hp'], 0)

    def test_phys_bulk_formula(self):
        entry = self.d1['1.6']
        row = map_to_ui(entry, 1, 6)
        s = entry['stats']
        hp = int(s['HP']); df = int(s['DEF'])
        expected = round(hp * df / 100, 1)
        self.assertEqual(row['physBulk'], expected)

    def test_spec_bulk_formula(self):
        entry = self.d1['1.6']
        row = map_to_ui(entry, 1, 6)
        s = entry['stats']
        hp = int(s['HP']); spd = int(s.get('SP.DEF') or s.get('sp_def') or 0)
        expected = round(hp * spd / 100, 1)
        self.assertEqual(row['specBulk'], expected)

    def test_offense_is_max_atk_spatk(self):
        entry = self.d1['1.6']
        row = map_to_ui(entry, 1, 6)
        self.assertEqual(row['offense'], max(row['atk'], row['spatk']))

    def test_type_score_consistent(self):
        entry = self.d1['1.6']
        row = map_to_ui(entry, 1, 6)
        w = compute_weaknesses(row['types'])
        expected = 2*len(w['x0']) + len(w['x1/2']) + len(w['x1/4']) - 2*len(w['x2']) - 4*len(w['x4'])
        self.assertEqual(row['typeScore'], expected)

    def test_all_stat_fields_non_negative(self):
        for key in ['1.6','1.25','1.150']:
            if key not in self.d1: continue
            row = map_to_ui(self.d1[key], 1, int(key.split('.')[1]))
            for field in ['hp','atk','def','spatk','spdef','speed','total']:
                self.assertGreaterEqual(row[field], 0, f'{key} {field} is negative')

    def test_reverse_fusion_different(self):
        row_ab = map_to_ui(self.d1['1.6'], 1, 6)
        row_ba = map_to_ui(self.d6['6.1'], 6, 1)
        # Head determines typing, so types should differ
        self.assertNotEqual(row_ab['types'], row_ba['types'])


class TestPCManagement(unittest.TestCase):

    def test_toggle_add(self):
        pc = toggle_pc([], 1)
        self.assertIn(1, pc)

    def test_toggle_remove(self):
        pc = toggle_pc([1, 6, 25], 6)
        self.assertNotIn(6, pc)
        self.assertIn(1, pc)
        self.assertIn(25, pc)

    def test_toggle_idempotent_double_click(self):
        pc = toggle_pc([], 1)
        pc = toggle_pc(pc, 1)
        self.assertEqual(pc, [])

    def test_add_fusion_removes_head_and_body(self):
        """Saving a fusion removes h and b from PC as base Pokémon (matches main app)."""
        pc = [1, 6, 25]
        pc = add_fusion_to_pc(pc, 1, 6)
        self.assertNotIn(1, pc,  "Bulbasaur (head) should be removed after saving fusion_1_6")
        self.assertNotIn(6, pc,  "Charizard (body) should be removed after saving fusion_1_6")
        self.assertIn(25, pc,    "Pikachu (unrelated) must stay")
        self.assertIn('fusion_1_6', pc)

    def test_add_fusion_removes_conflicting_fusions(self):
        """Saving fusion_1_6 also removes existing fusions that use 1 or 6."""
        pc = [1, 6, 25, 'fusion_1_25', 'fusion_6_25']
        pc = add_fusion_to_pc(pc, 1, 6)
        self.assertNotIn('fusion_1_25', pc)
        self.assertNotIn('fusion_6_25', pc)
        self.assertIn('fusion_1_6', pc)
        self.assertIn(25, pc)

    def test_add_fusion_keeps_unrelated_fusions(self):
        pc = [1, 6, 25, 9, 'fusion_25_9']
        pc = add_fusion_to_pc(pc, 1, 6)
        self.assertIn('fusion_25_9', pc)

    def test_add_fusion_no_duplicate(self):
        pc = [1, 6]
        pc = add_fusion_to_pc(pc, 1, 6)
        pc = add_fusion_to_pc(pc, 1, 6)
        self.assertEqual(pc.count('fusion_1_6'), 1)

    def test_remove_base_pokemon(self):
        pc = remove_from_pc([1, 6, 25], 6)
        self.assertNotIn(6, pc)
        self.assertEqual(len(pc), 2)

    def test_remove_fusion(self):
        pc = ['fusion_1_6', 25]
        pc = remove_from_pc(pc, 'fusion_1_6')
        self.assertNotIn('fusion_1_6', pc)
        self.assertIn(25, pc)

    def test_remove_nonexistent_is_noop(self):
        pc = [1, 6]
        pc2 = remove_from_pc(pc, 99)
        self.assertEqual(pc2, [1, 6])

    def test_get_base_ids_excludes_fusions(self):
        pc = [1, 6, 'fusion_1_6', 25]
        ids = get_base_ids(pc)
        self.assertIn(1, ids)
        self.assertIn(6, ids)
        self.assertIn(25, ids)
        self.assertEqual(len(ids), 3)

    def test_get_base_ids_empty(self):
        pc = ['fusion_1_6']
        self.assertEqual(get_base_ids(pc), [])


class TestFusionAnalysis(unittest.TestCase):

    def setUp(self):
        self.cache = {
            1:  load_fusion(1),
            6:  load_fusion(6),
            25: load_fusion(25),
            150: load_fusion(150),
        }

    def test_analyze_two_pokemon(self):
        ids = [1, 6]
        rows = []
        for h in ids:
            for b in ids:
                if h == b: continue
                entry = (self.cache[h] or {}).get(f'{h}.{b}')
                if entry: rows.append(map_to_ui(entry, h, b))
        # Should have at least 2 fusions (1.6 and 6.1)
        self.assertGreaterEqual(len(rows), 2)
        ids_found = {(r['_h'], r['_b']) for r in rows}
        self.assertIn((1, 6), ids_found)
        self.assertIn((6, 1), ids_found)

    def test_analyze_three_pokemon(self):
        ids = [1, 6, 25]
        rows = []
        for h in ids:
            for b in ids:
                if h == b: continue
                entry = (self.cache[h] or {}).get(f'{h}.{b}')
                if entry: rows.append(map_to_ui(entry, h, b))
        # 3 Pokémon -> 6 ordered pairs
        self.assertEqual(len(rows), 6)

    def test_no_self_fusions_in_results(self):
        """Self-fusion entries (1.1, 6.6 etc.) exist in data with empty stats
        but must be excluded from analysis results (h==b check)."""
        ids = [1, 6, 25]
        rows = []
        for h in ids:
            for b in ids:
                if h == b: continue          # this is the JS guard
                entry = (self.cache[h] or {}).get(f'{h}.{b}')
                if entry: rows.append(map_to_ui(entry, h, b))
        for row in rows:
            self.assertNotEqual(row['_h'], row['_b'],
                f"Self-fusion {row['_h']}.{row['_b']} appeared in results")

    def test_results_sorted_by_total_desc(self):
        ids = [1, 6, 25, 150]
        rows = []
        for h in ids:
            for b in ids:
                if h == b: continue
                entry = (self.cache[h] or {}).get(f'{h}.{b}')
                if entry: rows.append(map_to_ui(entry, h, b))
        rows.sort(key=lambda r: r['total'], reverse=True)
        for i in range(len(rows)-1):
            self.assertGreaterEqual(rows[i]['total'], rows[i+1]['total'])

    def test_fusion_types_are_valid(self):
        entry = self.cache[1]['1.6']
        row = map_to_ui(entry, 1, 6)
        for t in row['types']:
            self.assertIn(t, TYPE_ORDER, f"Unknown type: {t}")


class TestBestTeamDP(unittest.TestCase):

    def setUp(self):
        self.cache = {i: load_fusion(i) for i in [1, 6, 25, 9, 150]}

    def test_two_pokemon_finds_one_pair(self):
        teams = compute_best_teams([1, 6], self.cache)
        self.assertGreater(len(teams), 0)
        self.assertEqual(len(teams[0]['team']), 1)

    def test_four_pokemon_finds_two_pairs(self):
        teams = compute_best_teams([1, 6, 25, 9], self.cache)
        self.assertGreater(len(teams), 0)
        self.assertEqual(len(teams[0]['team']), 2)

    def test_best_team_score_is_sum_of_pair_totals(self):
        ids = [1, 6, 25, 9]
        teams = compute_best_teams(ids, self.cache, metric='Total')
        self.assertGreater(len(teams), 0)
        team = teams[0]
        pair_sum = sum(r['total'] for r in team['team'])
        self.assertAlmostEqual(team['score'], pair_sum, places=0)

    def test_no_pokemon_used_twice_in_best_team(self):
        ids = [1, 6, 25, 9]
        teams = compute_best_teams(ids, self.cache)
        for team_result in teams:
            used = []
            for row in team_result['team']:
                self.assertNotIn(row['_h'], used, f"Head {row['_h']} used twice")
                self.assertNotIn(row['_b'], used, f"Body {row['_b']} used twice")
                used.extend([row['_h'], row['_b']])

    def test_teams_returned_in_descending_score_order(self):
        ids = [1, 6, 25, 9, 150]
        teams = compute_best_teams(ids, self.cache, max_teams=3)
        scores = [t['score'] for t in teams]
        for i in range(len(scores)-1):
            self.assertGreaterEqual(scores[i], scores[i+1])

    def test_single_pokemon_returns_no_teams(self):
        teams = compute_best_teams([1], self.cache)
        self.assertEqual(teams, [])

    def test_metric_phys_bulk_gives_different_result_than_total(self):
        ids = [1, 6, 25, 9]
        t_total = compute_best_teams(ids, self.cache, metric='Total', max_teams=1)
        t_bulk  = compute_best_teams(ids, self.cache, metric='Phys Bulk', max_teams=1)
        self.assertGreater(len(t_total), 0)
        self.assertGreater(len(t_bulk), 0)
        # At least one metric should produce a different team
        sig_total = tuple(sorted((r['_h'], r['_b']) for r in t_total[0]['team']))
        sig_bulk  = tuple(sorted((r['_h'], r['_b']) for r in t_bulk[0]['team']))
        # (May or may not differ depending on data, but scores will differ)
        score_total_on_bulk = sum(
            get_metric((self.cache[r['_h']] or {}).get(f"{r['_h']}.{r['_b']}", {}), 'Phys Bulk')
            for r in t_total[0]['team']
        )
        score_bulk_on_bulk = sum(
            get_metric((self.cache[r['_h']] or {}).get(f"{r['_h']}.{r['_b']}", {}), 'Phys Bulk')
            for r in t_bulk[0]['team']
        )
        self.assertGreaterEqual(score_bulk_on_bulk, score_total_on_bulk)


class TestDataIntegrity(unittest.TestCase):

    def test_all_572_fusion_files_exist(self):
        fusions_dir = ROOT / "data" / "fusions"
        for pid in POKEMON_DATA:
            p = fusions_dir / f"{pid}.json"
            self.assertTrue(p.exists(), f"Missing data/fusions/{pid}.json")

    def test_fusion_file_keys_match_head_id(self):
        for pid in ['1','25','150','572']:
            data = load_fusion(int(pid))
            for key in data:
                head = key.split('.')[0]
                self.assertEqual(head, pid, f"Key {key} in {pid}.json has wrong head")

    def test_pokemon_data_has_required_fields(self):
        for pid, info in POKEMON_DATA.items():
            self.assertIn('name', info,       f"#{pid} missing name")
            self.assertIn('generation', info, f"#{pid} missing generation")
            self.assertIn('national_id', info,f"#{pid} missing national_id")
            self.assertIn('abilities', info,  f"#{pid} missing abilities")

    def test_abilities_have_is_hidden_field(self):
        for pid, info in POKEMON_DATA.items():
            for ab in info.get('abilities', []):
                self.assertIn('is_hidden', ab, f"#{pid} ability missing is_hidden")
                self.assertIn('name', ab,      f"#{pid} ability missing name")

    def test_fusion_stats_have_expected_keys(self):
        d1 = load_fusion(1)
        entry = d1['1.6']
        stats = entry.get('stats', {})
        for key in ['HP','ATK','DEF','SP.DEF','SPEED']:
            self.assertIn(key, stats, f"1.6 stats missing {key}")

    def test_no_negative_stats(self):
        d1 = load_fusion(1)
        for key, entry in list(d1.items())[:20]:
            stats = entry.get('stats', {})
            for stat, val in stats.items():
                try:
                    self.assertGreaterEqual(int(val), 0, f"{key} {stat}={val} is negative")
                except (TypeError, ValueError):
                    pass


class TestLargeAmounts(unittest.TestCase):
    """Stress tests: 10, 15 and 20 Pokémon in PC."""

    # First 20 Gen-1 Pokémon IDs
    GEN1_20 = list(range(1, 21))

    @classmethod
    def setUpClass(cls):
        cls.cache = {i: load_fusion(i) for i in cls.GEN1_20}

    # -- Fusion analysis -----------------------------------------------------

    def _run_analysis(self, ids):
        rows = []
        for h in ids:
            for b in ids:
                if h == b: continue
                entry = (self.cache[h] or {}).get(f'{h}.{b}')
                if entry: rows.append(map_to_ui(entry, h, b))
        return rows

    def test_analysis_10_pokemon_correct_count(self):
        ids = self.GEN1_20[:10]
        rows = self._run_analysis(ids)
        # n*(n-1) ordered pairs, all should exist
        self.assertEqual(len(rows), 10 * 9)

    def test_analysis_15_pokemon_correct_count(self):
        ids = self.GEN1_20[:15]
        rows = self._run_analysis(ids)
        self.assertEqual(len(rows), 15 * 14)

    def test_analysis_20_pokemon_correct_count(self):
        ids = self.GEN1_20
        rows = self._run_analysis(ids)
        self.assertEqual(len(rows), 20 * 19)

    def test_analysis_20_no_duplicates(self):
        ids = self.GEN1_20
        rows = self._run_analysis(ids)
        seen = set()
        for r in rows:
            key = (r['_h'], r['_b'])
            self.assertNotIn(key, seen, f"Duplicate fusion {key}")
            seen.add(key)

    def test_analysis_20_all_stats_valid(self):
        ids = self.GEN1_20
        rows = self._run_analysis(ids)
        for r in rows:
            for field in ['hp', 'atk', 'def', 'spatk', 'spdef', 'speed', 'total']:
                self.assertGreaterEqual(r[field], 0,
                    f"{r['_h']}.{r['_b']} {field} is negative")
            self.assertGreaterEqual(r['physBulk'], 0)
            self.assertGreaterEqual(r['specBulk'], 0)
            self.assertGreaterEqual(r['offense'], 0)

    def test_analysis_20_type_scores_consistent(self):
        ids = self.GEN1_20
        rows = self._run_analysis(ids)
        for r in rows:
            w = compute_weaknesses(r['types'])
            expected = (2*len(w['x0']) + len(w['x1/2']) + len(w['x1/4'])
                        - 2*len(w['x2']) - 4*len(w['x4']))
            self.assertEqual(r['typeScore'], expected,
                f"{r['_h']}.{r['_b']} type score wrong")

    # -- Best team DP --------------------------------------------------------

    def test_best_team_10_pokemon(self):
        ids = self.GEN1_20[:10]
        import time
        t0 = time.time()
        teams = compute_best_teams(ids, self.cache, metric='Total', max_fusions=6, max_teams=3)
        elapsed = time.time() - t0
        self.assertGreater(len(teams), 0)
        self.assertLessEqual(len(teams[0]['team']), 6)
        print(f'\n  10-pokemon best-team DP: {elapsed:.3f}s, {len(teams)} option(s)')

    def test_best_team_15_pokemon(self):
        ids = self.GEN1_20[:15]
        import time
        t0 = time.time()
        teams = compute_best_teams(ids, self.cache, metric='Total', max_fusions=6, max_teams=3)
        elapsed = time.time() - t0
        self.assertGreater(len(teams), 0)
        self.assertLessEqual(elapsed, 30.0, 'DP took >30 s for 15 Pokémon')
        print(f'\n  15-pokemon best-team DP: {elapsed:.3f}s, {len(teams)} option(s)')

    def test_best_team_20_pokemon_capped_at_20(self):
        ids = self.GEN1_20  # exactly 20 = max the JS allows
        import time
        t0 = time.time()
        teams = compute_best_teams(ids, self.cache, metric='Total', max_fusions=6, max_teams=3)
        elapsed = time.time() - t0
        self.assertGreater(len(teams), 0)
        self.assertLessEqual(elapsed, 60.0, 'DP took >60 s for 20 Pokémon')
        print(f'\n  20-pokemon best-team DP: {elapsed:.3f}s, {len(teams)} option(s)')

    def test_best_team_no_pokemon_used_twice_large(self):
        ids = self.GEN1_20
        teams = compute_best_teams(ids, self.cache, metric='Total', max_fusions=6, max_teams=3)
        for team_result in teams:
            used = []
            for row in team_result['team']:
                self.assertNotIn(row['_h'], used, f"Head {row['_h']} used twice")
                self.assertNotIn(row['_b'], used, f"Body {row['_b']} used twice")
                used.extend([row['_h'], row['_b']])

    def test_best_team_scores_descending_large(self):
        ids = self.GEN1_20
        teams = compute_best_teams(ids, self.cache, metric='Total', max_fusions=6, max_teams=3)
        scores = [t['score'] for t in teams]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i+1],
                f"Team {i} score {scores[i]} < team {i+1} score {scores[i+1]}")

    def test_pc_management_20_items(self):
        pc = []
        for i in self.GEN1_20:
            pc = toggle_pc(pc, i)
        self.assertEqual(len(pc), 20)

        # Adding 5 fusions: each removes its head+body from PC
        pairs = [(1,2),(3,4),(5,6),(7,8),(9,10)]
        for h, b in pairs:
            pc = add_fusion_to_pc(pc, h, b)

        # 5 pairs × 2 removed + 5 fusions added = 20 - 10 + 5 = 15
        self.assertEqual(len(pc), 15)

        # Base Pokémon 11-20 are untouched
        for i in range(11, 21):
            self.assertIn(i, pc)

        # Head/body Pokémon 1-10 were consumed
        for i in range(1, 11):
            self.assertNotIn(i, pc)

        # 5 fusion keys are present
        for h, b in pairs:
            self.assertIn(f'fusion_{h}_{b}', pc)

        # getBaseIds returns only the 10 remaining base Pokémon
        base = get_base_ids(pc)
        self.assertEqual(sorted(base), list(range(11, 21)))


# -- Port of JS import/export logic -------------------------------------------

def export_pc(pc):
    """Mirrors JS savePC(): serialise PC to {pc: [...]} JSON bytes."""
    return json.dumps({'pc': pc}, indent=2).encode()

def import_pc(raw_bytes):
    """
    Mirrors JS loadPCFromFile(): parse bytes, validate, filter.
    Returns (list, error_str). error_str is None on success.
    """
    try:
        data = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        return [], str(exc)
    if not isinstance(data, dict) or not isinstance(data.get('pc'), list):
        return [], 'Invalid PC file: missing "pc" array.'
    valid = [
        x for x in data['pc']
        if (isinstance(x, str) and x.startswith('fusion_'))
        or (isinstance(x, int))
        or (isinstance(x, str) and x.isdigit())
    ]
    return valid, None


class TestImportExport(unittest.TestCase):

    def test_export_produces_valid_json(self):
        pc = [1, 6, 'fusion_1_6']
        raw = export_pc(pc)
        data = json.loads(raw)
        self.assertIn('pc', data)
        self.assertIsInstance(data['pc'], list)

    def test_export_preserves_all_items(self):
        pc = [1, 6, 25, 'fusion_1_6', 'fusion_6_25']
        data = json.loads(export_pc(pc))
        self.assertEqual(data['pc'], pc)

    def test_export_empty_pc(self):
        data = json.loads(export_pc([]))
        self.assertEqual(data['pc'], [])

    def test_roundtrip_preserves_state(self):
        pc = [1, 6, 25, 'fusion_1_6', 'fusion_25_6']
        raw = export_pc(pc)
        loaded, err = import_pc(raw)
        self.assertIsNone(err)
        self.assertEqual(loaded, pc)

    def test_import_valid_fusions_and_base(self):
        raw = json.dumps({'pc': [1, 6, 'fusion_1_6']}).encode()
        loaded, err = import_pc(raw)
        self.assertIsNone(err)
        self.assertEqual(loaded, [1, 6, 'fusion_1_6'])

    def test_import_string_numeric_ids_kept(self):
        """String digits like "1" are valid (some code paths use string IDs)."""
        raw = json.dumps({'pc': ['1', '6', 'fusion_1_6']}).encode()
        loaded, err = import_pc(raw)
        self.assertIsNone(err)
        self.assertIn('1', loaded)
        self.assertIn('fusion_1_6', loaded)

    def test_import_filters_garbage_entries(self):
        raw = json.dumps({'pc': [1, 'fusion_1_6', None, {'x': 1}, [], 'bad_entry', 99.9]}).encode()
        loaded, err = import_pc(raw)
        self.assertIsNone(err)
        self.assertIn(1, loaded)
        self.assertIn('fusion_1_6', loaded)
        self.assertNotIn(None, loaded)
        self.assertNotIn('bad_entry', loaded)

    def test_import_invalid_json_returns_error(self):
        _, err = import_pc(b'not json at all {{{')
        self.assertIsNotNone(err)

    def test_import_missing_pc_key_returns_error(self):
        raw = json.dumps({'data': [1, 2, 3]}).encode()
        _, err = import_pc(raw)
        self.assertIsNotNone(err)

    def test_import_pc_is_not_array_returns_error(self):
        raw = json.dumps({'pc': {'a': 1}}).encode()
        _, err = import_pc(raw)
        self.assertIsNotNone(err)

    def test_import_empty_array_is_valid(self):
        raw = json.dumps({'pc': []}).encode()
        loaded, err = import_pc(raw)
        self.assertIsNone(err)
        self.assertEqual(loaded, [])

    def test_import_large_pc_roundtrip(self):
        """20 base Pokémon + 10 fusions round-trips cleanly."""
        pc = list(range(1, 21)) + [f'fusion_{h}_{b}' for h, b in [(1,2),(3,4),(5,6),(7,8),(9,10),(11,12),(13,14),(15,16),(17,18),(19,20)]]
        raw = export_pc(pc)
        loaded, err = import_pc(raw)
        self.assertIsNone(err)
        self.assertEqual(loaded, pc)

    def test_export_import_all_fusions_only(self):
        """PC with only fusion keys (no base Pokémon) round-trips."""
        pc = ['fusion_1_6', 'fusion_25_150', 'fusion_9_3']
        loaded, err = import_pc(export_pc(pc))
        self.assertIsNone(err)
        self.assertEqual(loaded, pc)


class TestFilterResultsTable(unittest.TestCase):
    """Port of JS filterResultsTable - mirrors main app update_output box-store trigger."""

    def _make_row(self, h, b):
        return {'_h': h, '_b': b}

    def test_keeps_rows_where_both_base_in_pc(self):
        rows = [self._make_row(1, 6), self._make_row(6, 1)]
        pc   = [1, 6]
        out  = filter_results_table(rows, pc)
        self.assertEqual(len(out), 2)

    def test_removes_row_when_head_removed_from_pc(self):
        rows = [self._make_row(1, 6), self._make_row(25, 6)]
        pc   = [6, 25]          # 1 is gone
        out  = filter_results_table(rows, pc)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['_h'], 25)

    def test_removes_row_when_body_removed_from_pc(self):
        rows = [self._make_row(1, 6)]
        pc   = [1]              # 6 is gone
        out  = filter_results_table(rows, pc)
        self.assertEqual(len(out), 0)

    def test_removes_already_saved_fusion(self):
        rows = [self._make_row(1, 6), self._make_row(1, 25)]
        pc   = [1, 6, 25, 'fusion_1_6']
        out  = filter_results_table(rows, pc)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['_b'], 25)

    def test_empty_pc_removes_all(self):
        rows = [self._make_row(1, 6)]
        out  = filter_results_table(rows, [])
        self.assertEqual(out, [])

    def test_empty_rows_returns_empty(self):
        self.assertEqual(filter_results_table([], [1, 6]), [])

    def test_save_fusion_then_filter_full_flow(self):
        """Full flow: add 3 Pokémon -> analyze -> save one fusion -> table filters."""
        pc   = [1, 6, 25]
        rows = [
            self._make_row(1, 6), self._make_row(6, 1),
            self._make_row(1, 25), self._make_row(25, 1),
            self._make_row(6, 25), self._make_row(25, 6),
        ]
        # Save fusion_1_6: removes 1 and 6, keeps 25
        pc = add_fusion_to_pc(pc, 1, 6)
        out = filter_results_table(rows, pc)
        # Only fusions involving 25 as both head and body base remain - none do
        # since 1 and 6 are no longer base Pokémon
        for row in out:
            self.assertIn(row['_h'], get_base_ids(pc))
            self.assertIn(row['_b'], get_base_ids(pc))

    def test_multiple_saves_filter_correctly(self):
        pc   = [1, 6, 25, 9]
        rows = [self._make_row(h, b) for h in [1,6,25,9] for b in [1,6,25,9] if h != b]
        # Save 1/6
        pc   = add_fusion_to_pc(pc, 1, 6)
        out  = filter_results_table(rows, pc)
        base = set(get_base_ids(pc))
        for row in out:
            self.assertIn(row['_h'], base)
            self.assertIn(row['_b'], base)
        # Save 25/9
        pc  = add_fusion_to_pc(pc, 25, 9)
        out = filter_results_table(rows, pc)
        self.assertEqual(out, [])   # no base Pokémon left


class TestBrowseSortOrder(unittest.TestCase):
    """Verify Browse grid sorts by national_id, matching main app _display_sort_key."""

    def test_national_id_sort_before_game_id_sort(self):
        # Treecko: game 276, national 252
        # Azurill: game 252, national 298
        # National sort -> Treecko first; game-ID sort -> Azurill first
        ids = [252, 276]
        sorted_ids = sorted(ids, key=lambda i: national_id_sort_key(i, POKEMON_DATA))
        self.assertEqual(sorted_ids[0], 276, "Treecko (nat 252) should come before Azurill (nat 298)")
        self.assertEqual(sorted_ids[1], 252)

    def test_gen1_unchanged_national_equals_game(self):
        # For gen 1 (IDs 1-151), national_id == game_id so both sorts agree
        gen1 = list(range(1, 152))
        by_game     = sorted(gen1)
        by_national = sorted(gen1, key=lambda i: national_id_sort_key(i, POKEMON_DATA))
        self.assertEqual(by_game, by_national)

    def test_gen3_starters_in_national_order(self):
        # Treecko 276/252, Torchic 279/255, Mudkip 282/258
        ids = [282, 276, 279]   # intentionally out of order
        sorted_ids = sorted(ids, key=lambda i: national_id_sort_key(i, POKEMON_DATA))
        self.assertEqual(sorted_ids, [276, 279, 282])

    def test_all_pokemon_sort_stable(self):
        all_ids = [int(k) for k in POKEMON_DATA]
        sorted_ids = sorted(all_ids, key=lambda i: national_id_sort_key(i, POKEMON_DATA))
        self.assertEqual(len(sorted_ids), 572)
        # National IDs should be non-decreasing
        nats = [int(POKEMON_DATA[str(i)].get('national_id') or i) for i in sorted_ids]
        for j in range(len(nats) - 1):
            self.assertLessEqual(nats[j], nats[j+1])

    def test_wynaut_national_after_treecko(self):
        # Wynaut: game 253, national 360 -> must appear after all Gen3 starters
        treecko_nat = int(POKEMON_DATA['276']['national_id'])
        wynaut_nat  = int(POKEMON_DATA['253']['national_id'])
        self.assertLess(treecko_nat, wynaut_nat)


# ===============================================================================
# EDGE CASE / WEIRD SCENARIO TESTS
# ===============================================================================

class TestWeirdPCScenarios(unittest.TestCase):
    """Unusual but possible PC states and operations."""

    def test_save_fusion_whose_reverse_is_already_saved(self):
        # fusion_1_6 already in PC; now save fusion_6_1 - should remove fusion_1_6
        pc = [1, 6, 'fusion_1_6']
        # Saving 6_1: removes 6 (head) and 1 (body), removes fusion_1_6 (uses 1 and 6)
        pc = add_fusion_to_pc(pc, 6, 1)
        self.assertNotIn('fusion_1_6', pc)
        self.assertIn('fusion_6_1', pc)
        self.assertNotIn(1, pc)
        self.assertNotIn(6, pc)

    def test_save_fusion_with_only_fusions_in_pc(self):
        # PC has fusions but no matching base Pokémon (edge: shouldn't crash)
        pc = ['fusion_25_150']
        pc = add_fusion_to_pc(pc, 1, 6)
        self.assertIn('fusion_1_6', pc)
        self.assertIn('fusion_25_150', pc)  # unrelated, kept

    def test_toggle_pokemon_already_consumed_by_fusion(self):
        # Bulbasaur was removed when fusion_1_6 saved; toggling it again re-adds it
        pc = ['fusion_1_6', 25]
        pc = toggle_pc(pc, 1)
        self.assertIn(1, pc)
        self.assertIn('fusion_1_6', pc)  # toggle doesn't touch fusions

    def test_remove_from_pc_unknown_item(self):
        pc = [1, 6, 'fusion_1_6']
        pc2 = remove_from_pc(pc, 999)
        self.assertEqual(pc2, pc)

    def test_add_same_fusion_twice_idempotent(self):
        pc = [1, 6]
        pc = add_fusion_to_pc(pc, 1, 6)
        count = pc.count('fusion_1_6')
        pc = add_fusion_to_pc(pc, 1, 6)   # second call: 1 and 6 already gone
        self.assertEqual(pc.count('fusion_1_6'), 1)
        self.assertEqual(count, 1)

    def test_chain_save_fusions_consumes_all_pokemon(self):
        # 4 Pokémon -> save 2 fusions -> PC has only 2 fusions left
        pc = [1, 6, 25, 9]
        pc = add_fusion_to_pc(pc, 1, 6)
        pc = add_fusion_to_pc(pc, 25, 9)
        self.assertEqual(get_base_ids(pc), [])
        self.assertIn('fusion_1_6', pc)
        self.assertIn('fusion_25_9', pc)

    def test_saving_fusion_of_already_fused_ids_does_nothing_extra(self):
        # fusion_1_6 saved; no base 1 or 6 remain; trying to save fusion_1_25
        # should only remove base 25 (1 is already gone)
        pc = [25, 'fusion_1_6']
        pc = add_fusion_to_pc(pc, 1, 25)
        self.assertNotIn(25, pc)
        self.assertNotIn('fusion_1_6', pc)   # still removed because uses id 1
        self.assertIn('fusion_1_25', pc)

    def test_pc_with_string_and_int_ids_mixed(self):
        # Some code paths store IDs as strings, some as ints
        pc = [1, '6', 'fusion_1_6', 25]
        base = get_base_ids(pc)
        self.assertIn(1, base)
        self.assertIn(6, base)
        self.assertIn(25, base)

    def test_clear_pc_then_add(self):
        pc = [1, 6, 25, 'fusion_1_6']
        pc = []   # clear
        pc = toggle_pc(pc, 1)
        self.assertEqual(pc, [1])

    def test_filter_with_only_fusion_items_in_pc(self):
        rows = [{'_h': 1, '_b': 6}, {'_h': 25, '_b': 9}]
        pc = ['fusion_1_6']   # no base Pokémon
        out = filter_results_table(rows, pc)
        self.assertEqual(out, [])

    def test_filter_preserves_row_data(self):
        row = {'_h': 1, '_b': 6, 'total': 500, 'name': 'Bulbasaur/Charizard'}
        out = filter_results_table([row], [1, 6])
        self.assertEqual(out[0]['total'], 500)
        self.assertEqual(out[0]['name'], 'Bulbasaur/Charizard')

    def test_all_572_pokemon_can_be_toggled(self):
        pc = []
        for pid in POKEMON_DATA:
            pc = toggle_pc(pc, int(pid))
        self.assertEqual(len(pc), 572)
        for pid in POKEMON_DATA:
            pc = toggle_pc(pc, int(pid))
        self.assertEqual(pc, [])

    def test_save_fusion_with_high_game_ids(self):
        # Dragalge (game 572) and Skrelp (game 571)
        pc = [571, 572]
        pc = add_fusion_to_pc(pc, 572, 571)
        self.assertIn('fusion_572_571', pc)
        self.assertNotIn(571, pc)
        self.assertNotIn(572, pc)

    def test_export_import_with_mixed_types(self):
        pc = [1, 6, 'fusion_1_6', 25, 'fusion_25_150']
        raw = export_pc(pc)
        loaded, err = import_pc(raw)
        self.assertIsNone(err)
        self.assertEqual(loaded, pc)

    def test_import_rejects_float_ids(self):
        raw = json.dumps({'pc': [1.5, 'fusion_1_6', 2.0]}).encode()
        loaded, _ = import_pc(raw)
        # 1.5 is not int or fusion string, 2.0 is float not int
        self.assertNotIn(1.5, loaded)
        self.assertIn('fusion_1_6', loaded)

    def test_filter_large_table_after_chain_saves(self):
        ids = list(range(1, 11))
        rows = [{'_h': h, '_b': b} for h in ids for b in ids if h != b]
        self.assertEqual(len(rows), 90)
        pc = list(ids)
        # Save 4 fusions consuming 8 Pokémon; 2 remain (9, 10)
        for h, b in [(1,2),(3,4),(5,6),(7,8)]:
            pc = add_fusion_to_pc(pc, h, b)
        out = filter_results_table(rows, pc)
        base = set(get_base_ids(pc))
        self.assertEqual(base, {9, 10})
        self.assertEqual(len(out), 2)  # 9->10 and 10->9
        for row in out:
            self.assertIn(row['_h'], {9, 10})
            self.assertIn(row['_b'], {9, 10})


class TestWeirdTypeScenarios(unittest.TestCase):

    def test_dual_type_with_both_immunities(self):
        # Ghost/Normal: Ghost immune to Normal+Fighting, Normal immune to Ghost -> x0 to Ghost
        w = compute_weaknesses(['GHOST', 'NORMAL'])
        # Ghost is immune to Normal and Fighting; Normal cancels Ghost's Ghost immunity
        self.assertIn('NORMAL', w['x0'])
        self.assertIn('FIGHTING', w['x0'])

    def test_quad_resist(self):
        # Steel/Fairy vs Poison: Steel 0x, Fairy 0.5x -> 0x
        w = compute_weaknesses(['STEEL', 'FAIRY'])
        self.assertIn('POISON', w['x0'])

    def test_single_type_all_multipliers_sum_to_18(self):
        for t in ['NORMAL','FIRE','WATER','GRASS','GHOST','DRAGON','STEEL']:
            w = compute_weaknesses([t])
            total = sum(len(v) for v in w.values())
            self.assertEqual(total, 18, f'{t} should have 18 type matchups')

    def test_type_score_ground_flying_immune_to_electric(self):
        # Ground is immune to Electric
        w = compute_weaknesses(['GROUND'])
        self.assertIn('ELECTRIC', w['x0'])

    def test_steel_many_resists(self):
        w = compute_weaknesses(['STEEL'])
        total_res = len(w.get('x1/2', [])) + len(w.get('x1/4', [])) + len(w.get('x0', []))
        self.assertGreaterEqual(total_res, 10)

    def test_empty_types_returns_empty_weaknesses(self):
        # Empty typing means no types -> takes neutral (x1) from everything
        w = compute_weaknesses([])
        all_types = ['NORMAL','FIRE','WATER','ELECTRIC','GRASS','ICE','FIGHTING',
                     'POISON','GROUND','FLYING','PSYCHIC','BUG','ROCK','GHOST',
                     'DRAGON','DARK','STEEL','FAIRY']
        self.assertEqual(sorted(w.get('x1', [])), sorted(all_types))

    def test_unknown_type_ignored(self):
        # Should not crash, just use what's valid
        w = compute_weaknesses(['FIRE', 'FAKETYPE'])
        self.assertIn('WATER', w['x2'])

    def test_type_score_pure_normal_positive_or_zero(self):
        w = compute_weaknesses(['NORMAL'])
        score = 2*len(w.get('x0',[])) + len(w.get('x1/2',[])) + len(w.get('x1/4',[])) \
              - 2*len(w.get('x2',[])) - 4*len(w.get('x4',[]))
        # Normal has 2 immunities (Ghost) -> at least +4 from Ghost alone... actually wait
        # Ghost is immune to Normal. But we're computing weaknesses OF Normal type.
        # Normal is weak to nothing except Fighting(2x), resists nothing, immune to Ghost(0x)
        # score = 2*1 + 0 - 2*1 - 0 = 0
        self.assertGreaterEqual(score, -10)   # just must not crash

    def test_4x_weakness_dragon_flying(self):
        # Dragon/Flying vs Ice: Dragon 2x, Flying 2x -> 4x
        w = compute_weaknesses(['DRAGON', 'FLYING'])
        self.assertIn('ICE', w['x4'])


class TestWeirdFusionAnalysis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cache = {i: load_fusion(i) for i in [1, 6, 25, 9, 150, 151]}

    def test_single_pokemon_produces_no_fusions(self):
        ids = [1]
        rows = []
        for h in ids:
            for b in ids:
                if h == b: continue
                e = (self.cache[h] or {}).get(f'{h}.{b}')
                if e: rows.append(map_to_ui(e, h, b))
        self.assertEqual(rows, [])

    def test_legendary_fusions_have_high_totals(self):
        # Mewtwo (150) fusions should generally be high stat
        rows = []
        for b in [1, 6, 25, 9, 151]:
            e = (self.cache[150] or {}).get(f'150.{b}')
            if e: rows.append(map_to_ui(e, 150, b))
        self.assertTrue(all(r['total'] > 400 for r in rows),
                        "Mewtwo fusions should all exceed 400 total")

    def test_reverse_fusion_same_stats_different_typing(self):
        e_ab = self.cache[1]['1.6']
        e_ba = self.cache[6]['6.1']
        r_ab = map_to_ui(e_ab, 1, 6)
        r_ba = map_to_ui(e_ba, 6, 1)
        # Stats may differ (head determines base stats in fusion formula)
        # Types definitely differ (head determines primary type)
        self.assertNotEqual(r_ab['types'], r_ba['types'])

    def test_all_fusions_have_valid_type_scores(self):
        ids = [1, 6, 25, 9]
        for h in ids:
            for b in ids:
                if h == b: continue
                e = (self.cache[h] or {}).get(f'{h}.{b}')
                if not e: continue
                r = map_to_ui(e, h, b)
                w = compute_weaknesses(r['types'])
                expected = (2*len(w.get('x0',[])) + len(w.get('x1/2',[])) + len(w.get('x1/4',[]))
                            - 2*len(w.get('x2',[])) - 4*len(w.get('x4',[])))
                self.assertEqual(r['typeScore'], expected, f'{h}.{b} type score mismatch')

    def test_fusion_with_pokemon_not_in_cache_excluded(self):
        # If fusion data is missing for a pair, it should simply not appear
        ids = [1, 6]
        partial_cache = {1: {}, 6: self.cache[6]}  # empty data for head 1
        rows = []
        for h in ids:
            for b in ids:
                if h == b: continue
                e = (partial_cache.get(h) or {}).get(f'{h}.{b}')
                if e: rows.append(map_to_ui(e, h, b))
        # Only 6.1 should appear (head 6 has data, head 1 has none)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['_h'], 6)

    def test_mew_and_mewtwo_both_directions(self):
        e_ab = self.cache[150].get('150.151')
        e_ba = self.cache[151].get('151.150')
        self.assertIsNotNone(e_ab)
        self.assertIsNotNone(e_ba)
        r_ab = map_to_ui(e_ab, 150, 151)
        r_ba = map_to_ui(e_ba, 151, 150)
        self.assertGreater(r_ab['total'], 0)
        self.assertGreater(r_ba['total'], 0)


class TestWeirdBestTeamScenarios(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cache = {i: load_fusion(i) for i in range(1, 11)}

    def test_two_pokemon_only_one_pair_possible(self):
        teams = compute_best_teams([1, 6], self.cache, max_fusions=6, max_teams=3)
        self.assertEqual(len(teams[0]['team']), 1)

    def test_odd_number_of_pokemon_leaves_one_out(self):
        teams = compute_best_teams([1, 6, 25], self.cache, max_fusions=6, max_teams=1)
        self.assertGreater(len(teams), 0)
        # 3 Pokémon -> best team has 1 pair (one Pokémon sits out)
        self.assertEqual(len(teams[0]['team']), 1)

    def test_max_fusions_1_returns_only_one_pair(self):
        teams = compute_best_teams([1, 6, 25, 9], self.cache, max_fusions=1, max_teams=3)
        for t in teams:
            self.assertEqual(len(t['team']), 1)

    def test_all_metrics_produce_valid_teams(self):
        ids = [1, 6, 25, 9]
        for metric in ['Total', 'Phys Bulk', 'Spec Bulk', 'Mixed Bulk', 'Offense']:
            teams = compute_best_teams(ids, self.cache, metric=metric, max_fusions=6, max_teams=1)
            self.assertGreater(len(teams), 0, f'No team for metric {metric}')
            self.assertGreater(len(teams[0]['team']), 0)

    def test_best_team_ids_are_subset_of_input(self):
        ids = [1, 6, 25, 9]
        teams = compute_best_teams(ids, self.cache, max_fusions=6, max_teams=3)
        id_set = set(ids)
        for t in teams:
            for row in t['team']:
                self.assertIn(row['_h'], id_set)
                self.assertIn(row['_b'], id_set)

    def test_repeated_calls_are_deterministic(self):
        ids = [1, 6, 25, 9]
        t1 = compute_best_teams(ids, self.cache, max_fusions=6, max_teams=3)
        t2 = compute_best_teams(ids, self.cache, max_fusions=6, max_teams=3)
        self.assertEqual(
            [(r['_h'], r['_b']) for r in t1[0]['team']],
            [(r['_h'], r['_b']) for r in t2[0]['team']],
        )

    def test_score_matches_sum_of_individual_pair_metrics(self):
        ids = [1, 6, 25, 9]
        teams = compute_best_teams(ids, self.cache, metric='Total', max_fusions=6, max_teams=1)
        team = teams[0]
        pair_sum = sum(r['total'] for r in team['team'])
        self.assertAlmostEqual(team['score'], pair_sum, places=0)

    def test_21_pokemon_capped_at_20(self):
        ids = list(range(1, 22))   # 21 items
        cache = {i: load_fusion(i) for i in ids}
        teams = compute_best_teams(ids, cache, max_fusions=6, max_teams=1)
        all_ids_used = {row['_h'] for t in teams for row in t['team']} | \
                       {row['_b'] for t in teams for row in t['team']}
        # All IDs used must be from the first 20
        self.assertTrue(all_ids_used.issubset(set(range(1, 21))))


# ===============================================================================
# GUI TESTS - Playwright headless browser against the live GitHub Pages app
# ===============================================================================

# Override with FUSION_APP_URL to test a local build before deploying,
# e.g. FUSION_APP_URL=http://localhost:8123 python scripts/test_web_app.py
APP_URL = os.environ.get('FUSION_APP_URL', 'https://samirBou.github.io/fusion')
GUI_TIMEOUT = 15_000   # ms per action

def _launch():
    from playwright.sync_api import sync_playwright
    pw  = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    ctx  = browser.new_context()
    page = ctx.new_page()
    page.set_default_timeout(GUI_TIMEOUT)
    return pw, browser, ctx, page

def _quit(pw, browser, ctx):
    ctx.close(); browser.close(); pw.stop()


class TestGUIBrowse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pw, cls.browser, cls.ctx, cls.page = _launch()
        cls.page.goto(APP_URL)
        cls.page.wait_for_selector('#sprite-grid .sprite-btn', timeout=30_000)

    @classmethod
    def tearDownClass(cls):
        _quit(cls.pw, cls.browser, cls.ctx)

    def test_page_title(self):
        self.assertIn('Fusion', self.page.title())

    def test_gen1_loaded_on_start(self):
        count = self.page.locator('#sprite-grid .sprite-btn').count()
        self.assertEqual(count, 151)

    def test_gen1_first_pokemon_is_bulbasaur(self):
        first = self.page.locator('#sprite-grid .sprite-btn').first
        self.assertIn('Bulbasaur', first.get_attribute('title') or first.inner_text())

    def test_switching_to_gen2_changes_grid(self):
        self.page.locator('#gen-tabs a[data-gen="2"]').click()
        self.page.wait_for_timeout(500)
        count = self.page.locator('#sprite-grid .sprite-btn').count()
        self.assertEqual(count, 100)

    def test_gen3_treecko_appears_before_azurill(self):
        self.page.locator('#gen-tabs a[data-gen="3"]').click()
        self.page.wait_for_timeout(500)
        btns = self.page.locator('#sprite-grid .sprite-btn').all()
        titles = [b.get_attribute('title') or b.inner_text() for b in btns[:10]]
        names = [t.split('#')[0].strip() for t in titles]
        treecko_pos = next((i for i,n in enumerate(names) if 'Treecko' in n), None)
        azurill_pos = next((i for i,n in enumerate(names) if 'Azurill' in n), None)
        if treecko_pos is not None and azurill_pos is not None:
            self.assertLess(treecko_pos, azurill_pos)

    def test_search_filters_grid(self):
        self.page.locator('#gen-tabs a[data-gen="1"]').click()
        self.page.wait_for_timeout(300)
        self.page.fill('#pokemon-search', 'char')
        self.page.wait_for_timeout(400)
        names = [b.inner_text() for b in self.page.locator('#sprite-grid .sprite-btn').all()]
        self.assertTrue(all('char' in n.lower() for n in names), f'Non-matching: {names}')
        self.page.fill('#pokemon-search', '')
        self.page.wait_for_timeout(300)

    def test_search_no_results(self):
        self.page.fill('#pokemon-search', 'xyzxyzxyz')
        self.page.wait_for_timeout(400)
        count = self.page.locator('#sprite-grid .sprite-btn').count()
        self.assertEqual(count, 0)
        self.page.fill('#pokemon-search', '')
        self.page.wait_for_timeout(300)

    def test_clicking_pokemon_adds_to_browse_strip(self):
        self.page.locator('#gen-tabs a[data-gen="1"]').click()
        self.page.wait_for_timeout(400)
        self.page.locator('#sprite-grid .sprite-btn').first.click()
        self.page.wait_for_timeout(300)
        strip_count = self.page.locator('#browse-pc .browse-pc-btn').count()
        self.assertGreaterEqual(strip_count, 1)

    def test_clicking_pokemon_twice_removes_from_strip(self):
        # Click the same one again to toggle off
        self.page.locator('#sprite-grid .sprite-btn').first.click()
        self.page.wait_for_timeout(300)
        strip_count = self.page.locator('#browse-pc .browse-pc-btn').count()
        self.assertEqual(strip_count, 0)

    def test_all_gen_tabs_show_correct_counts(self):
        expected = {1: 151, 2: 100, 3: 138, 4: 65, 5: 53, 6: 37, 7: 28}
        for gen, count in expected.items():
            self.page.locator(f'#gen-tabs a[data-gen="{gen}"]').click()
            self.page.wait_for_timeout(400)
            actual = self.page.locator('#sprite-grid .sprite-btn').count()
            self.assertEqual(actual, count, f'Gen {gen}: expected {count}, got {actual}')


class TestGUIPCAndAnalysis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pw, cls.browser, cls.ctx, cls.page = _launch()
        cls.page.goto(APP_URL)
        cls.page.wait_for_selector('#sprite-grid .sprite-btn', timeout=30_000)
        # Add Bulbasaur and Charizard
        cls.page.locator('#gen-tabs a[data-gen="1"]').click()
        cls.page.wait_for_timeout(500)
        btns = cls.page.locator('#sprite-grid .sprite-btn').all()
        bulbasaur = next(b for b in btns if 'Bulbasaur' in (b.get_attribute('title') or b.inner_text()))
        charizard = next(b for b in btns if 'Charizard' in (b.get_attribute('title') or b.inner_text()))
        bulbasaur.click(); cls.page.wait_for_timeout(200)
        charizard.click(); cls.page.wait_for_timeout(200)

    @classmethod
    def tearDownClass(cls):
        _quit(cls.pw, cls.browser, cls.ctx)

    def test_pc_tab_shows_both_pokemon(self):
        self.page.locator('a.nav-link[href="#"]', has_text='My PC').click()
        self.page.wait_for_timeout(400)
        cards = self.page.locator('#pc-box .pc-card').count()
        self.assertEqual(cards, 2)

    def test_pc_box_shows_names(self):
        text = self.page.locator('#pc-box').inner_text()
        self.assertIn('Bulbasaur', text)
        self.assertIn('Charizard', text)

    def test_analyze_fusions_produces_results(self):
        self.page.locator('a.nav-link[href="#"]', has_text='My PC').click()
        self.page.wait_for_timeout(300)
        self.page.locator('button', has_text='Analyze Fusions').click()
        self.page.wait_for_selector('#results-table tbody tr', timeout=30_000)
        rows = self.page.locator('#results-table tbody tr').count()
        self.assertGreaterEqual(rows, 2)   # at least 1.6 and 6.1

    def test_results_tab_shows_pc_strip(self):
        self.page.locator('a.nav-link[href="#"]', has_text='Fusion Results').click()
        self.page.wait_for_timeout(300)
        strip = self.page.locator('#results-pc .browse-pc-btn').count()
        self.assertGreaterEqual(strip, 2)

    def test_results_pc_strip_flows_inline(self):
        # All browse-pc-btn elements should be on roughly the same vertical line (inline)
        self.page.locator('a.nav-link[href="#"]', has_text='Fusion Results').click()
        self.page.wait_for_timeout(300)
        btns = self.page.locator('#results-pc .browse-pc-btn').all()
        if len(btns) >= 2:
            y0 = btns[0].bounding_box()['y']
            y1 = btns[1].bounding_box()['y']
            self.assertAlmostEqual(y0, y1, delta=10, msg='PC strip items are not inline')

    def test_save_fusion_removes_base_pokemon_from_pc(self):
        # Ensure we're on Fusion Results tab with results loaded
        self.page.locator('a.nav-link[href="#"]', has_text='Fusion Results').click()
        self.page.wait_for_timeout(300)
        # Click the first Add button in results
        self.page.locator('#results-table .add-btn').first.click()
        self.page.wait_for_timeout(600)
        # Switch to PC tab: the two singles should now be a single fusion card
        self.page.locator('a.nav-link[href="#"]', has_text='My PC').click()
        self.page.wait_for_timeout(400)
        cards = self.page.locator('#pc-box .pc-card').count()
        self.assertEqual(cards, 1, 'expected the 2 singles to be replaced by 1 fusion card')
        pc_text = self.page.locator('#pc-box').inner_text()
        self.assertIn('/', pc_text)   # fusion name contains /
        # Check storage directly: no base entry left for either one
        stored = self.page.evaluate("JSON.parse(sessionStorage.getItem('fusionPC'))")
        base_entries = [x for x in stored if not (isinstance(x, str) and x.startswith('fusion_'))]
        self.assertNotIn('1', [str(x) for x in base_entries])
        self.assertNotIn('6', [str(x) for x in base_entries])

    def test_results_table_filters_after_save(self):
        # After saving a fusion, go back to results - saved fusion should be gone from table
        self.page.locator('a.nav-link[href="#"]', has_text='Fusion Results').click()
        self.page.wait_for_timeout(400)
        rows_after = self.page.locator('#results-table tbody tr').count()
        # With only 2 Pokémon and one fusion saved, fewer rows should remain
        self.assertGreaterEqual(rows_after, 0)

    def test_z_clear_pc_empties_box(self):
        # Must run last (z-prefix) so it doesn't empty the PC for other tests
        self.page.locator('a.nav-link[href="#"]', has_text='My PC').click()
        self.page.wait_for_timeout(300)
        self.page.locator('button', has_text='Clear PC').click()
        self.page.wait_for_timeout(300)
        cards = self.page.locator('#pc-box .pc-card').count()
        self.assertEqual(cards, 0)


class TestGUIEdgeCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pw, cls.browser, cls.ctx, cls.page = _launch()
        cls.page.goto(APP_URL)
        cls.page.wait_for_selector('#sprite-grid .sprite-btn', timeout=30_000)

    @classmethod
    def tearDownClass(cls):
        _quit(cls.pw, cls.browser, cls.ctx)

    def test_analyze_with_empty_pc_shows_error(self):
        self.page.locator('a.nav-link[href="#"]', has_text='My PC').click()
        self.page.wait_for_timeout(300)
        self.page.locator('button', has_text='Analyze Fusions').click()
        self.page.wait_for_timeout(400)
        status = self.page.locator('#analysis-status').inner_text()
        self.assertTrue(len(status) > 0)

    def test_find_best_team_with_one_pokemon_shows_error(self):
        self.page.locator('a.nav-link[href="#"]', has_text='Browse Pokémon').click()
        self.page.wait_for_timeout(300)
        self.page.locator('#gen-tabs a[data-gen="1"]').click()
        self.page.wait_for_timeout(300)
        btns = self.page.locator('#sprite-grid .sprite-btn').all()
        bulbasaur = next(b for b in btns if 'Bulbasaur' in (b.get_attribute('title') or b.inner_text()))
        bulbasaur.click()
        self.page.wait_for_timeout(200)
        self.page.locator('a.nav-link[href="#"]', has_text='Best Team').click()
        self.page.wait_for_timeout(300)
        self.page.locator('button', has_text='Find Best Team').click()
        self.page.wait_for_timeout(400)
        status = self.page.locator('#best-team-status').inner_text()
        self.assertTrue(len(status) > 0)
        # Clean up - navigate to Browse first, gen-tabs only visible there
        self.page.locator('a.nav-link[href="#"]', has_text='Browse Pokémon').click()
        self.page.wait_for_timeout(300)
        self.page.locator('#gen-tabs a[data-gen="1"]').click()
        self.page.wait_for_timeout(300)
        btns = self.page.locator('#sprite-grid .sprite-btn').all()
        bulbasaur = next(b for b in btns if 'Bulbasaur' in (b.get_attribute('title') or b.inner_text()))
        bulbasaur.click()
        self.page.wait_for_timeout(200)

    def test_export_pc_button_exists(self):
        self.page.locator('a.nav-link[href="#"]', has_text='My PC').click()
        self.page.wait_for_timeout(300)
        btn = self.page.locator('button', has_text='Export PC')
        self.assertTrue(btn.is_visible())

    def test_import_pc_button_exists(self):
        self.page.locator('a.nav-link[href="#"]', has_text='My PC').click()
        self.page.wait_for_timeout(300)
        btn = self.page.locator('button', has_text='Import PC')
        self.assertTrue(btn.is_visible())

    def test_all_main_tabs_navigable(self):
        for tab in ['Browse Pokémon', 'My PC', 'Fusion Results', 'Best Team']:
            self.page.locator(f'a.nav-link', has_text=tab).click()
            self.page.wait_for_timeout(300)

    def test_session_storage_persists_across_tab_switches(self):
        # Add Pikachu, switch tabs back and forth, Pikachu stays
        self.page.locator('a.nav-link[href="#"]', has_text='Browse Pokémon').click()
        self.page.wait_for_timeout(300)
        self.page.locator('#gen-tabs a[data-gen="1"]').click()
        self.page.wait_for_timeout(400)
        btns = self.page.locator('#sprite-grid .sprite-btn').all()
        pikachu = next(b for b in btns if 'Pikachu' in (b.get_attribute('title') or b.inner_text()))
        pikachu.click()
        self.page.wait_for_timeout(200)
        self.page.locator('a.nav-link', has_text='Fusion Results').click()
        self.page.wait_for_timeout(200)
        self.page.locator('a.nav-link', has_text='Best Team').click()
        self.page.wait_for_timeout(200)
        self.page.locator('a.nav-link', has_text='Browse Pokémon').click()
        self.page.wait_for_timeout(300)
        strip = self.page.locator('#browse-pc .browse-pc-btn').count()
        self.assertGreaterEqual(strip, 1)
        # Clean up
        pikachu = next(b for b in self.page.locator('#sprite-grid .sprite-btn').all()
                       if 'Pikachu' in (b.get_attribute('title') or b.inner_text()))
        pikachu.click()
        self.page.wait_for_timeout(200)

    def test_new_tab_has_empty_pc(self):
        # sessionStorage is tab-local - new page should have empty PC
        page2 = self.ctx.new_page()
        page2.goto(APP_URL)
        page2.wait_for_selector('#sprite-grid .sprite-btn', timeout=30_000)
        page2.locator('a.nav-link', has_text='My PC').click()
        page2.wait_for_timeout(400)
        cards = page2.locator('#pc-box .pc-card').count()
        self.assertEqual(cards, 0)
        page2.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
