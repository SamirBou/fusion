import requests
from bs4 import BeautifulSoup
import logging
import os
import json
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_URL = "https://infinitefusiondex.com/details/"
MAX_WORKERS = int(os.environ.get('MAX_FUSION_WORKERS', '10'))
LOG_DIR = "logs"
CACHE_FILE = "all_fusions_data.json"
SPRITES_DIR = os.path.join("data", "sprites")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "fusion_analyzer.log"), mode='w'),
        logging.StreamHandler()
    ]
)

_fusion_cache = {}
_cache_file_exists = os.path.exists(CACHE_FILE)

if os.environ.get('WEB_DEPLOYMENT', '0') == '1':
    MAX_WORKERS = min(MAX_WORKERS, 5)

if _cache_file_exists:
    try:
        with open(CACHE_FILE, 'r') as f:
            _fusion_cache = json.load(f)
        logging.info(f"Loaded {len(_fusion_cache)} fusions from local data")
    except Exception as e:
        logging.warning(f"Could not load local data: {e}")
        _fusion_cache = {}

def save_to_cache(new_data):
    if os.environ.get('WEB_DEPLOYMENT', '0') == '1' or not new_data:
        return
    try:
        cache_data = {}
        if _cache_file_exists:
            try:
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
            except Exception as e:
                logging.warning(f"Error loading existing cache: {e}")
        cache_data.update(new_data)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        logging.info(f"Saved {len(new_data)} fusions to cache")
    except Exception as e:
        logging.error(f"Error saving to cache: {e}")

def download_sprite_if_needed(sprite_url, fusion_key):
    if not sprite_url:
        return None
    
    try:
        os.makedirs(SPRITES_DIR, exist_ok=True)
        filename = f"{fusion_key.replace('#', '')}.png"
        filepath = os.path.join(SPRITES_DIR, filename)
        
        if os.path.exists(filepath):
            return filepath
        
        response = requests.get(sprite_url, timeout=5)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filepath
    except Exception as e:
        logging.warning(f"Failed to download sprite for {fusion_key}: {e}")
        return None

def parse_stats(soup):
    stats_data = {"fusion1": {}, "fusion2": {}}
    try:
        stats_accordion = soup.find('h2', class_='accordion-header', string='Stats')
        if not stats_accordion:
            logging.error("Could not find Stats accordion.")
            return None

        stats_accordion_body = stats_accordion.find_next('div', class_='accordion-body')
        if not stats_accordion_body:
            logging.error("Could not find Stats accordion body.")
            return None

        stat_rows = stats_accordion_body.find_all('div', class_='g-1')

        for row in stat_rows:
            stat_name_elem = row.find('div', class_='font-gray subheader text-center')
            if not stat_name_elem:
                continue
            
            stat_name_raw = stat_name_elem.text.strip()
            if 'SPEED' in stat_name_raw:
                stat_name = 'SPEED'
            elif 'SP.ATK' in stat_name_raw or 'SPA' in stat_name_raw:
                stat_name = 'SP.ATK'
            elif 'SP.DEF' in stat_name_raw or 'SPD' in stat_name_raw:
                stat_name = 'SP.DEF'
            elif 'TOTAL' in stat_name_raw or 'TOT' in stat_name_raw:
                stat_name = 'TOTAL'
            else:
                stat_name = stat_name_raw
            
            all_cols = row.find_all('div', recursive=False)
            
            values = []
            for col in all_cols:
                section = col.find('div', class_='section')
                if section:
                    text = section.text.strip().split('(')[0].strip()
                    if text != 'X':
                        try:
                            values.append(int(text))
                        except ValueError:
                            continue
            
            if len(values) >= 2:
                stats_data['fusion1'][stat_name] = values[0]
                stats_data['fusion2'][stat_name] = values[1]

        return stats_data
    except Exception as e:
        logging.error(f"Error parsing stats: {e}")
        return None

def parse_weaknesses(soup):
    weaknesses_data = {"fusion1": {}, "fusion2": {}}
    try:
        weaknesses_button = None
        buttons = soup.find_all('button', class_='accordion-button')
        for button in buttons:
            if 'Weaknesses' in button.text:
                weaknesses_button = button
                break
        
        if not weaknesses_button:
            logging.warning("Weaknesses accordion not found")
            return weaknesses_data

        weaknesses_accordion_body = weaknesses_button.find_next('div', class_='accordion-body')
        if not weaknesses_accordion_body:
            logging.warning("Weaknesses accordion body not found")
            return weaknesses_data

        main_row = weaknesses_accordion_body.find('div', class_='row')
        if not main_row:
            return weaknesses_data
            
        all_cols = main_row.find_all('div', recursive=False)
        
        i = 0
        while i < len(all_cols):
            multiplier_elem = all_cols[i].find('div', class_='subheader')
            if not multiplier_elem:
                i += 1
                continue
            
            multiplier_text = multiplier_elem.text.strip().replace('\n', '').replace(' ', '')
            multiplier = multiplier_text
            i += 1
            
            if i < len(all_cols):
                type_container1 = all_cols[i].find('div', class_='section')
                if type_container1:
                    type_imgs1 = type_container1.find_all('img', class_='elemental-type')
                    types1 = [img['alt'] for img in type_imgs1 if 'alt' in img.attrs and img['alt'] != '-']
                    if types1:
                        if multiplier not in weaknesses_data['fusion1']:
                            weaknesses_data['fusion1'][multiplier] = []
                        weaknesses_data['fusion1'][multiplier].extend(types1)
                i += 1
            
            if i < len(all_cols):
                type_container2 = all_cols[i].find('div', class_='section')
                if type_container2:
                    type_imgs2 = type_container2.find_all('img', class_='elemental-type')
                    types2 = [img['alt'] for img in type_imgs2 if 'alt' in img.attrs and img['alt'] != '-']
                    if types2:
                        if multiplier not in weaknesses_data['fusion2']:
                            weaknesses_data['fusion2'][multiplier] = []
                        weaknesses_data['fusion2'][multiplier].extend(types2)
                i += 1
            
            # Skip duplicate subheader if present
            if i < len(all_cols):
                next_elem = all_cols[i].find('div', class_='subheader')
                if next_elem and next_elem.text.strip().replace('\n', '').replace(' ', '') == multiplier:
                    i += 1

        return weaknesses_data
    except Exception as e:
        logging.error(f"Error parsing weaknesses: {e}")
        return weaknesses_data


def fetch_fusion_data(pokemon_ids, pokemon_data):
    id1, id2 = sorted(pokemon_ids)
    url = f"{BASE_URL}{id1}.{id2}"
    fusion_data = {}

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        details_stack = soup.find('div', id='details-stack')
        if not details_stack:
            logging.warning(f"Could not find details-stack at {url}")
            return None

        fusion_displays = details_stack.find_all('div', class_='fusionDisplay')
        if len(fusion_displays) < 2:
            logging.warning(f"Could not find two fusion displays at {url}")
            return None

        stats_data = parse_stats(soup)
        weaknesses_data = parse_weaknesses(soup)

        if not stats_data:
            logging.warning(f"Could not parse stats at {url}")
            return None

        panel1 = fusion_displays[0]
        name1_element = panel1.find('span', class_='px-0')
        sprite1_element = panel1.find('img', class_='sprite')
        if name1_element:
            name1 = name1_element.text.strip().replace('/wbr>', '/')
            types1 = [img['alt'] for img in panel1.find_all('img', class_='elemental-type')]
            sprite1_url = sprite1_element['src'] if sprite1_element else None
            
            fusion_data[f"#{id1}.{id2}"] = {
                "name": name1,
                "types": types1,
                "stats": stats_data.get("fusion1"),
                "weaknesses": weaknesses_data.get("fusion1"),
                "sprite_url": sprite1_url,
                "fusion_url": url
            }

        panel2 = fusion_displays[1]
        name2_element = panel2.find('span', class_='px-0')
        sprite2_element = panel2.find('img', class_='sprite')
        if name2_element:
            name2 = name2_element.text.strip().replace('/wbr>', '/')
            types2 = [img['alt'] for img in panel2.find_all('img', class_='elemental-type')]
            sprite2_url = sprite2_element['src'] if sprite2_element else None
            
            fusion_data[f"#{id2}.{id1}"] = {
                "name": name2,
                "types": types2,
                "stats": stats_data.get("fusion2"),
                "weaknesses": weaknesses_data.get("fusion2"),
                "sprite_url": sprite2_url,
                "fusion_url": url
            }

        logging.info(f"Successfully fetched data for {id1}.{id2}")
        return fusion_data

    except requests.RequestException as e:
        logging.error(f"HTTP request failed for {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred for {url}: {e}")
        return None


def analyze_fusions(pokemon_ids):
    logging.info(f"Analyzing fusions for: {pokemon_ids}")

    import pokemon_data
    invalid_ids = [pid for pid in pokemon_ids if str(pid) not in pokemon_data.POKEMON_DATA]
    if invalid_ids:
        logging.warning(f"Ignoring invalid Pokemon IDs: {invalid_ids}")
        pokemon_ids = [pid for pid in pokemon_ids if str(pid) in pokemon_data.POKEMON_DATA]
    
    if not pokemon_ids:
        logging.warning("No valid Pokemon IDs provided")
        return []

    fusion_combinations = list(combinations(pokemon_ids, 2))
    logging.info(f"Generated {len(fusion_combinations)} fusion combinations")

    all_fusion_data = {}
    missing_combinations = []
    
    for combo in fusion_combinations:
        id1, id2 = sorted(combo)
        key1 = f"#{id1}.{id2}"
        key2 = f"#{id2}.{id1}"
        
        if key1 in _fusion_cache and key2 in _fusion_cache:
            all_fusion_data[key1] = _fusion_cache[key1]
            all_fusion_data[key2] = _fusion_cache[key2]
        else:
            missing_combinations.append(combo)
    
    if all_fusion_data:
        logging.info(f"Found {len(all_fusion_data)} fusions in local data")
    
    newly_fetched_data = {}
    if missing_combinations:
        logging.info(f"Fetching {len(missing_combinations)} combinations from web")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_fusion = {
                executor.submit(fetch_fusion_data, combo, None): combo 
                for combo in missing_combinations
            }
            
            for future in future_to_fusion:
                result = future.result()
                if result:
                    all_fusion_data.update(result)
                    newly_fetched_data.update(result)

    for key, data in newly_fetched_data.items():
        sprite_url = data.get('sprite_url')
        if sprite_url:
            local = download_sprite_if_needed(sprite_url, key)
            if local:
                data['local_sprite'] = local

    if newly_fetched_data:
        save_to_cache(newly_fetched_data)

    fusion_list = []
    for key, value in all_fusion_data.items():
        if not value or not value.get('stats'):
            continue
        
        weaknesses = value.get('weaknesses', {})
        stats = value['stats']
        sprite_url = value.get('sprite_url')
        fusion_url = value.get('fusion_url')
        
        local_sprite = None
        if sprite_url:
            sprite_filename = sprite_url.split('/')[-1]
            local_sprite_path = os.path.join(SPRITES_DIR, sprite_filename)
            if os.path.exists(local_sprite_path):
                local_sprite = local_sprite_path
        
        hp = stats.get('HP', 0)
        atk = stats.get('ATK', 0)
        defense = stats.get('DEF', 0)
        sp_atk = stats.get('SP.ATK', 0)
        sp_def = stats.get('SP.DEF', 0)
        speed = stats.get('SPEED', 0)
        total_stats = stats.get('TOTAL', 0)
        
        immunities_count = len(weaknesses.get('x0', []))
        double_resist_count = len(weaknesses.get('x1/4', []))
        resistances_count = len(weaknesses.get('x1/2', []))
        double_weak_count = len(weaknesses.get('x4', []))
        weaknesses_2x_count = len(weaknesses.get('x2', []))
        
        physical_bulk = hp * defense
        special_bulk = hp * sp_def
        avg_bulk = (physical_bulk + special_bulk) / 2
        
        type_score = (
            (immunities_count * 3.0) + 
            (double_resist_count * 1.5) + 
            (resistances_count * 0.5) - 
            (double_weak_count * 4.0) - 
            (weaknesses_2x_count * 1.0)
        )
        
        bulk_factor = (avg_bulk / 10000) * 10
        total_defensive = type_score + bulk_factor
        
        sprite_display = ''
        fusion_url = value.get('fusion_url')
        if local_sprite:
            sprite_display = f'[![Sprite]({local_sprite})]({fusion_url})' if fusion_url else f'![Sprite]({local_sprite})'
        elif sprite_url:
            sprite_display = f'[![Sprite]({sprite_url})]({fusion_url})' if fusion_url else f'![Sprite]({sprite_url})'
        
        fusion_info = {
            'Sprite': sprite_display,
            'Local Sprite': local_sprite,
            'Fusion ID': key,
            'Fusion URL': fusion_url,
            'Name': value.get('name', 'N/A'),
            'Types': ', '.join(value.get('types', [])),
            'Total': total_stats,
            'Defensive': round(total_defensive, 1),
            'Bulk': round(avg_bulk / 100, 1),
            'HP': hp,
            'ATK': atk,
            'DEF': defense,
            'SP.ATK': sp_atk,
            'SP.DEF': sp_def,
            'SPEED': speed,
            'Immunities': immunities_count,
            'Resists': resistances_count + double_resist_count,
            '2x Weak': weaknesses_2x_count,
            '4x Weak': double_weak_count,
        }
        
        for mult, types in weaknesses.items():
            fusion_info[mult] = ', '.join(types) if types else ''
        
        fusion_list.append(fusion_info)

    fusion_list.sort(key=lambda x: (x['Total'], x['Defensive']), reverse=True)
    
    logging.info(f"Analysis complete. Found {len(fusion_list)} valid fusions.")
    return fusion_list

