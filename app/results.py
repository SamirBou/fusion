import logging

from app import fusion_analyzer, pokemon_data

logger = logging.getLogger(__name__)


def get_style_conditions():

    style_conditions = [
        {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        {
            "if": {"filter_query": "{Total} >= 600", "column_id": "Total"},
            "backgroundColor": "#d4edda",
            "color": "#155724",
            "fontWeight": "bold",
        },
        {
            "if": {
                "filter_query": "{Total} >= 550 && {Total} < 600",
                "column_id": "Total",
            },
            "backgroundColor": "#d1e7dd",
            "color": "#0f5132",
        },
        {
            "if": {
                "filter_query": "{Total} >= 500 && {Total} < 550",
                "column_id": "Total",
            },
            "backgroundColor": "#fff3cd",
            "color": "#856404",
        },
        {"if": {"filter_query": "{Total} < 500", "column_id": "Total"}, "backgroundColor": "#f8d7da", "color": "#842029"},
        {
            "if": {"filter_query": "{Defensive} >= 50", "column_id": "Defensive"},
            "backgroundColor": "#d4edda",
            "color": "#155724",
            "fontWeight": "bold",
        },
        {
            "if": {
                "filter_query": "{Defensive} >= 30 && {Defensive} < 50",
                "column_id": "Defensive",
            },
            "backgroundColor": "#d1e7dd",
            "color": "#0f5132",
        },
        {
            "if": {
                "filter_query": "{Defensive} < 30 && {Defensive} >= 0",
                "column_id": "Defensive",
            },
            "backgroundColor": "#fff3cd",
            "color": "#856404",
        },
        {
            "if": {"filter_query": "{Bulk} >= 100", "column_id": "Bulk"},
            "backgroundColor": "#cff4fc",
            "color": "#055160",
            "fontWeight": "bold",
        },
        {"if": {"filter_query": "{4x Weak} > 0", "column_id": "4x Weak"}, "backgroundColor": "#f8d7da", "color": "#842029", "fontWeight": "bold"},
        {"if": {"filter_query": "{Immunities} > 0", "column_id": "Immunities"}, "backgroundColor": "#fff3cd", "color": "#856404", "fontWeight": "bold"},
        {"if": {"filter_query": "{Resists} >= 5", "column_id": "Resists"}, "backgroundColor": "#cff4fc", "color": "#055160"},
        {
            "if": {"column_id": "Add"},
            "backgroundColor": "#28A745",
            "color": "#ffffff",
            "fontWeight": "bold",
            "cursor": "pointer",
            "textAlign": "center",
            "fontSize": "18px",
        },
        {"if": {"column_id": "Sprite"}, "cursor": "pointer"},
    ]

    style_cell_conditional = [
        {"if": {"column_id": "Add"}, "width": "44px", "minWidth": "44px", "maxWidth": "44px"},
        {"if": {"column_id": "Sprite"}, "width": "60px", "minWidth": "60px", "maxWidth": "60px", "textAlign": "center", "padding": "2px"},
        {"if": {"column_id": "Name"}, "minWidth": "100px", "width": "120px"},
        {"if": {"column_id": "Types"}, "minWidth": "80px"},
        {"if": {"column_id": "Rating"}, "width": "70px", "textAlign": "center", "fontWeight": "bold"},
        {"if": {"column_id": "Offense"}, "width": "70px", "textAlign": "center"},
        {"if": {"column_id": "Defense"}, "width": "70px", "textAlign": "center"},
        {"if": {"column_id": "Speed Tier"}, "width": "80px", "textAlign": "center"},
        {"if": {"column_id": "Total"}, "width": "60px", "textAlign": "center"},
        {"if": {"column_id": "HP"}, "width": "50px", "textAlign": "center"},
        {"if": {"column_id": "ATK"}, "width": "50px", "textAlign": "center"},
        {"if": {"column_id": "DEF"}, "width": "50px", "textAlign": "center"},
        {"if": {"column_id": "SP.ATK"}, "width": "55px", "textAlign": "center"},
        {"if": {"column_id": "SP.DEF"}, "width": "55px", "textAlign": "center"},
        {"if": {"column_id": "SPEED"}, "width": "55px", "textAlign": "center"},
    ]

    return style_conditions + style_cell_conditional


def get_style_cell():
    return {
        "backgroundColor": "#ffffff",
        "color": "#000000",
        "textAlign": "left",
        "padding": "6px",
        "border": "1px solid #dee2e6",
        "minWidth": "40px",
        "whiteSpace": "normal",
        "height": "auto",
        "fontSize": "12px",
    }


def get_style_header():
    return {
        "backgroundColor": "#198754",
        "color": "#ffffff",
        "fontWeight": "bold",
        "border": "1px solid #198754",
        "textAlign": "center",
        "fontSize": "12px",
    }


def get_tooltips(length):
    return [
        {
            "Add": {"value": "Click to save this fusion to your PC", "type": "text"},
            "Sprite": {"value": "Click to view on Infinite Fusion Dex", "type": "text"},
            "Rating": {
                "value": "Overall competitive viability (0-100). Considers offense, defense, speed, typing, and stat distribution.",
                "type": "markdown",
            },
            "Offense": {"value": "Offensive capability: highest attack stat + mixed offense bonus + speed factor", "type": "markdown"},
            "Defense": {"value": "Defensive capability: (HP × DEF/100 + HP × SP.DEF/100)/2 + type effectiveness", "type": "markdown"},
            "Speed Tier": {"value": "Speed tier bonus: 25 (130+), 20 (110+), 15 (90+), 10 (70+), 5 (50+), 0 (<50)", "type": "markdown"},
        }
        for _ in range(length)
    ]


def build_pair_score_map(pokemon_ids):
    """Return a dict mapping frozenset({a,b}) -> score (Total + Defensive) using fusion_analyzer."""

    scores = {}

    try:
        fusion_list = fusion_analyzer.analyze_fusions(pokemon_ids)

        for f in fusion_list:
            fid = f.get("Fusion ID")
            if not fid:
                continue
            parts = fid.replace("#", "").split(".")
            if len(parts) != 2:
                continue
            a, b = int(parts[0]), int(parts[1])
            key = frozenset({a, b})
            total = f.get("Total", 0) or 0
            defensive = f.get("Defensive", 0) or 0
            scores[key] = total + defensive
    except Exception as e:
        logger.warning(f"Error building pair scores: {e}")

    return scores
