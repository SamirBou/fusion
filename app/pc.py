import logging
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html

from app import pokemon_data

from . import fusion_pokemon_data, grid_cache
from .sprites import sprite_url

logger = logging.getLogger(__name__)


def _display_sort_key(item):
    pid, _name = item
    info = fusion_pokemon_data.get(str(pid), {})
    try:
        national_id = int(info.get("national_id") or pid)
    except (TypeError, ValueError):
        national_id = int(pid)
    return national_id, int(pid)


def create_pokemon_sprite_grid(search=None, gen="all"):
    cache_key = f"{gen}_{search or ''}"
    if cache_key in grid_cache:
        return grid_cache[cache_key]

    try:
        all_pokemon = sorted(
            list(pokemon_data.POKEMON_DATA.items()),
            key=_display_sort_key,
        )

        if search:
            search_lower = str(search).lower()
            all_pokemon = [
                (pid, name)
                for pid, name in all_pokemon
                if search_lower in name.lower() or search_lower in pid
            ]

        if gen and gen != "all":
            gen_num = int(gen.replace("gen", ""))
            all_pokemon = [
                (pid, name)
                for pid, name in all_pokemon
                if fusion_pokemon_data.get(str(pid), {}).get("generation") == gen_num
            ]

    except Exception as e:
        return html.Div(f"Error building sprite grid: {e}")

    buttons = []

    for pid, name in all_pokemon:
        img_el = html.Img(
            src=sprite_url(pid),
            style={"width": "36px", "height": "36px", "objectFit": "contain"},
        )

        content = html.Div(
            [
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
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",
                "minWidth": "60px",
            },
        )

        button = dbc.Button(
            content,
            id={"type": "sprite-btn", "index": int(pid)},
            color="light",
            size="sm",
            style={
                "width": "64px",
                "height": "88px",
                "margin": "4px",
                "padding": "0",
                "boxSizing": "border-box",
                "border": "2px solid #ccc",
                "overflow": "hidden",
                "whiteSpace": "nowrap",
            },
        )

        wrapper = html.Div(
            button,
            **{"data-pid": str(int(pid))},
            style={"display": "inline-block"},
        )
        buttons.append(wrapper)

    grid = html.Div(
        buttons,
        style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"},
    )
    result = html.Div(grid, style={"padding": "8px"})
    grid_cache[cache_key] = result
    return result


def _sprite_src(pid_str):
    return sprite_url(pid_str)


def render_pc_summary(box):
    if not box:
        return html.Div("(empty)", style={"color": "#6C757D", "fontStyle": "italic"})

    items = []
    for item in box:
        try:
            if isinstance(item, str) and item.startswith("fusion_"):
                _, id1, id2 = item.split("_")
                pid = f"{int(id1)}.{int(id2)}"
            else:
                pid = str(item)

            content = html.Img(
                src=_sprite_src(pid),
                style={"width": "40px", "height": "40px", "objectFit": "contain"},
            )
            btn = dbc.Button(
                content,
                id={"type": "pc-item", "id": pid},
                color="light",
                size="sm",
                style={
                    "padding": "2px",
                    "margin": "3px",
                    "minWidth": "40px",
                    "minHeight": "40px",
                },
            )
            items.append(btn)
        except Exception:
            continue
    return html.Div(
        items, style={"display": "flex", "flexWrap": "wrap", "alignItems": "center"}
    )


def display_box(box, selected_pokemon):
    if not box:
        return html.Div(
            "Your Fusion PC is empty. Add some Pokémon and analyze fusions to save pairs you like!",
            style={"textAlign": "center", "color": "#6C757D", "fontStyle": "italic"},
        )
    cards = []
    singles = [
        int(x)
        for x in box
        if isinstance(x, int) or (isinstance(x, str) and x.isdigit())
    ]
    singles_sorted = sorted(set(singles))
    fusions = [x for x in box if isinstance(x, str) and x.startswith("fusion_")]

    def fusion_sort_key(s):
        parts = s.replace("fusion_", "").split("_")
        try:
            return (int(parts[0]), int(parts[1]))
        except Exception:
            return (99999, 99999)

    fusions_sorted = sorted(set(fusions), key=fusion_sort_key)
    ordered_box = list(singles_sorted) + fusions_sorted

    for item in ordered_box:
        is_selected = item in (selected_pokemon or [])
        if isinstance(item, str) and item.startswith("fusion_"):
            try:
                _, id1, id2 = item.split("_")
                id1, id2 = int(id1), int(id2)
                name1 = pokemon_data.POKEMON_DATA.get(str(id1), f"#{id1}")
                name2 = pokemon_data.POKEMON_DATA.get(str(id2), f"#{id2}")
                label = f"{name1}/{name2}"
                sprite_element = html.Img(
                    src=_sprite_src(f"{id1}.{id2}"),
                    style={"width": "36px", "height": "36px", "objectFit": "contain"},
                )
                sub_label = html.Div(
                    f"#{id1}.{id2}",
                    style={"textAlign": "center", "fontSize": "10px", "color": "#666"},
                )
            except Exception:
                continue
        else:
            pokemon_id = item
            label = pokemon_data.POKEMON_DATA.get(str(pokemon_id), f"#{pokemon_id}")
            sprite_element = html.Img(
                src=_sprite_src(str(pokemon_id)),
                style={"width": "48px", "height": "48px", "objectFit": "contain"},
            )
            sub_label = None

        body_children = [
            html.Div(sprite_element, style={"textAlign": "center", "marginBottom": "5px"}),
            html.H6(label, className="card-title", style={"textAlign": "center", "fontSize": "10px"}),
        ]
        if sub_label:
            body_children.append(sub_label)
        body_children.append(
            dbc.Button(
                "Remove",
                id={"type": "remove-btn", "item": item},
                color="danger",
                size="sm",
                style={"width": "100%"},
            )
        )

        card = dbc.Col(
            dbc.Card(
                dbc.CardBody(body_children, style={"padding": "8px"}),
                style={
                    "border": f"2px solid {'#FF6B6B' if is_selected else '#2E86AB'}",
                    "borderRadius": "10px",
                },
            ),
            width=1,
            className="mb-3",
        )
        cards.append(card)

    return dbc.Row(cards, justify="start")
