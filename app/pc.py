import logging
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html

from app import pokemon_data

from . import fusion_pokemon_data, gen_ranges, grid_cache, sprite_rel_cache
from .sprites import find_sprite_relpath, get_sprite_base64

logger = logging.getLogger(__name__)


def create_pokemon_sprite_grid(page=1, box_data=None, search=None, gen="all"):
    if box_data is None:
        box_data = []

    cache_key = None
    if not box_data and not search:
        cache_key = f"{gen}_no_box_no_search"
        if cache_key in grid_cache:
            return grid_cache[cache_key]

    try:
        all_pokemon = sorted(list(pokemon_data.POKEMON_DATA.items()), key=lambda x: int(x[0]))

        if search:
            search_lower = str(search).lower()
            all_pokemon = [
                (pid, name)
                for pid, name in all_pokemon
                if search_lower in name.lower() or search_lower in pid
            ]

    except Exception as e:
        return html.Div(f"Error building sprite grid: {e}")

    if not search and gen != "all":
        try:
            gen_num = int(str(gen).lstrip("gen"))
        except Exception:
            gen_num = None

        if gen_num is not None:
            filtered = []
            try:
                for pid, name in all_pokemon:
                    try:
                        if gen_num == fusion_pokemon_data.get(pid, {}).get("generation", 0):
                            filtered.append((pid, name))
                    except Exception:
                        continue
                
            except Exception as e:
                logger.warning(f"Error filtering gen {gen_num}: {e}")
                filtered = []

            if filtered:
                all_pokemon = filtered
            else:
                gr = globals().get("gen_ranges", gen_ranges)
                min_id, max_id = gr.get(gen, (1, 1010))
                all_pokemon = [(pid, name) for pid, name in all_pokemon if min_id <= int(pid) <= max_id]

    if search:
        search_lower = search.lower()
        all_pokemon = [
            (pid, name) for pid, name in all_pokemon if search_lower in name.lower() or search_lower in pid
        ]

    pokemon_list = all_pokemon
    buttons = []

    for pid, name in pokemon_list:
        rel = find_sprite_relpath(pid)
        if rel:
            img_src = f"/sprites/{rel}"
        else:
            img_src = f"/sprites/{pid}.png"

        img_el = html.Img(src=img_src, style={"width": "36px", "height": "36px", "objectFit": "contain"})

        content = html.Div([
            img_el,
            html.Div(
                name,
                style={
                    "fontSize": "10px",
                    "textAlign": "center",
                    "width": "60px",
                    "overflow": "hidden",
                    "whiteSpace": "nowrap",
                    "textOverflow": "ellipsis",
                    "marginTop": "4px",
                    "lineHeight": "12px",
                },
            ),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center", "minWidth": "60px"})

        try:
            gen_val = None
            info = fusion_pokemon_data.get(str(pid)) or fusion_pokemon_data.get(pid)
            if isinstance(info, dict):
                gen_val = info.get("generation")
            if gen_val is None:
                try:
                    pid_num = int(pid)
                    for gk, rng in gen_ranges.items():
                        if isinstance(rng, tuple) and len(rng) == 2:
                            if rng[0] <= pid_num <= rng[1]:
                                gen_val = int(str(gk).lstrip("gen"))
                                break
                except Exception:
                    gen_val = None
        except Exception:
            gen_val = None

        button = dbc.Button(content, id={"type": "sprite-btn", "index": int(pid)}, color="light", size="sm",
                            style={"width": "64px", "height": "88px", "margin": "4px", "padding": "0", "boxSizing": "border-box",
                                   "border": ("2px solid #2E86AB" if int(pid) in box_data else "2px solid #ccc"),
                                   "overflow": "hidden", "whiteSpace": "nowrap"})

        gen_class = f"fusion-gen-{gen_val}" if gen_val is not None else "fusion-gen-all"
        wrapper = html.Div(button, **{"data-gen": str(gen_val) if gen_val is not None else ""}, className=gen_class,
                           style={"display": "inline-block"})
        buttons.append(wrapper)

    grid = html.Div(buttons, style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"})
    result = html.Div(grid, style={"padding": "8px"})
    if cache_key:
        grid_cache[cache_key] = result
    return result


def render_pc_summary(box):
    if not box:
        return html.Div("(empty)", style={"color": "#6C757D", "fontStyle": "italic"})

    items = []
    for item in box:
        try:
            if isinstance(item, str) and item.startswith("fusion_"):
                _, id1, id2 = item.split("_")
                pid = f"{int(id1)}.{int(id2)}"
                rel = find_sprite_relpath(pid)
                if rel:
                    base64_src = get_sprite_base64(rel)
                    img_src = base64_src if base64_src else f"/sprites/{rel}"
                    content = html.Img(src=img_src, style={"width": "40px", "height": "40px", "objectFit": "contain"})
                else:
                    content = html.Div(f"#{pid}", style={"width": "40px", "height": "40px", "display": "flex", "alignItems": "center", "justifyContent": "center", "fontSize": "10px"})
            else:
                pid = str(item)
                rel = find_sprite_relpath(pid)
                if rel:
                    base64_src = get_sprite_base64(rel)
                    img_src = base64_src if base64_src else f"/sprites/{rel}"
                    content = html.Img(src=img_src, style={"width": "40px", "height": "40px", "objectFit": "contain"})
                else:
                    name = pokemon_data.POKEMON_DATA.get(pid, f"#{pid}")
                    content = html.Div(f"#{pid}", title=name, style={"width": "40px", "height": "40px", "display": "flex", "alignItems": "center", "justifyContent": "center", "fontSize": "10px"})

            btn = dbc.Button(content, id={"type": "pc-item", "id": pid}, color="light", size="sm",
                             style={"padding": "2px", "margin": "3px", "minWidth": "40px", "minHeight": "40px"})
            items.append(btn)
        except Exception:
            continue
    return html.Div(items, style={"display": "flex", "flexWrap": "wrap", "alignItems": "center"})


def display_box(box, selected_pokemon):
    if not box:
        return html.Div("Your Fusion PC is empty. Add some Pokémon and analyze fusions to save pairs you like!", style={"textAlign": "center", "color": "#6C757D", "fontStyle": "italic"})
    cards = []
    singles = [int(x) for x in box if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
    singles_sorted = sorted(set(singles))
    fusions = [x for x in box if isinstance(x, str) and x.startswith("fusion_")]

    def fusion_sort_key(s):
        parts = s.replace("fusion_", "").split("_")
        try:
            return (int(parts[0]), int(parts[1]))
        except:
            return (99999, 99999)

    fusions_sorted = sorted(set(fusions), key=fusion_sort_key)
    ordered_box = [p for p in singles_sorted] + fusions_sorted

    for i, item in enumerate(ordered_box):
        is_selected = item in (selected_pokemon or [])
        if isinstance(item, str) and item.startswith("fusion_"):
            try:
                _, id1, id2 = item.split("_")
                id1, id2 = int(id1), int(id2)
                name1 = pokemon_data.POKEMON_DATA.get(str(id1), f"#{id1}")
                name2 = pokemon_data.POKEMON_DATA.get(str(id2), f"#{id2}")
                fusion_name = f"{name1}/{name2}"
                rel = find_sprite_relpath(f"{id1}.{id2}")
                if rel:
                    base64_src = get_sprite_base64(rel)
                    img_src = base64_src if base64_src else f"/sprites/{rel}"
                    sprite_element = html.Img(src=img_src, style={"width": "36px", "height": "36px", "objectFit": "contain"})
                else:
                    sprite_element = html.Div(f"#{id1}.{id2}", style={"width": "60px", "height": "60px", "background": "#E9ECEF", "borderRadius": "50%", "display": "flex", "alignItems": "center", "justifyContent": "center", "fontSize": "16px"})

                card = dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(sprite_element, style={"textAlign": "center", "marginBottom": "5px"}),
                            html.H6(fusion_name, className="card-title", style={"textAlign": "center", "fontSize": "10px"}),
                            html.Div(f"#{id1}.{id2}", style={"textAlign": "center", "fontSize": "10px", "color": "#666"}),
                            dbc.Button("Remove", id={"type": "remove-btn", "item": item}, color="danger", size="sm", style={"width": "100%"}),
                        ], style={"padding": "8px"}),
                    ], style={"border": ("2px solid #FF6B6B" if is_selected else "2px solid #2E86AB"), "borderRadius": "10px"}),
                ], width=1, className="mb-3")
            except:
                continue
        else:
            pokemon_id = item
            name = pokemon_data.POKEMON_DATA.get(str(pokemon_id), f"#{pokemon_id}")
            rel = find_sprite_relpath(str(pokemon_id))
            if rel:
                base64_src = get_sprite_base64(rel)
                img_src = base64_src if base64_src else f"/sprites/{rel}"
                sprite_element = html.Img(src=img_src, style={"width": "48px", "height": "48px", "objectFit": "contain"})
            else:
                sprite_element = html.Div(f"#{pokemon_id}", style={"width": "60px", "height": "60px", "background": "#E9ECEF", "borderRadius": "6px", "display": "flex", "alignItems": "center", "justifyContent": "center", "fontSize": "16px"})

            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div(sprite_element, style={"textAlign": "center", "marginBottom": "5px"}),
                        html.H6(name, className="card-title", style={"textAlign": "center", "fontSize": "10px"}),
                        dbc.Button("Remove", id={"type": "remove-btn", "item": item}, color="danger", size="sm", style={"width": "100%"}),
                    ], style={"padding": "8px"}),
                ], style={"border": ("2px solid #FF6B6B" if is_selected else "2px solid #2E86AB"), "borderRadius": "10px"}),
            ], width=1, className="mb-3")
        cards.append(card)

    return dbc.Row(cards, justify="start")
