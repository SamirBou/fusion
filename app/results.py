import logging

logger = logging.getLogger(__name__)

COLUMN_TOOLTIPS = {
    "Option": {"value": "Ranked team option label", "type": "text"},
    "Team Score": {"value": "Total score for this team option under the selected metric", "type": "text"},
    "Add": {"value": "Save this fusion to your PC", "type": "text"},
    "Sprite": {"value": "Click to open on Infinite Fusion Dex", "type": "text"},
    "Name": {
        "value": "Head/Body — head determines typing and base stats",
        "type": "text",
    },
    "Types": {"value": "Pokémon typing of this fusion", "type": "text"},
    "Ability 1": {
        "value": "Head Pokémon's slot-1 ability — hover a cell for the description",
        "type": "text",
    },
    "Ability 2": {
        "value": "Body Pokémon's slot-1 ability — hover a cell for the description",
        "type": "text",
    },
    "Hidden Ability": {
        "value": "Head Pokémon's hidden ability — hover a cell for the description",
        "type": "text",
    },
    "Total": {
        "value": "Sum of all 6 base stats (HP + ATK + DEF + SP.ATK + SP.DEF + SPEED)",
        "type": "text",
    },
    "Phys Bulk": {
        "value": "HP × DEF ÷ 100 — Smogon physical bulk product: how well this fusion tanks physical hits",
        "type": "text",
    },
    "Spec Bulk": {
        "value": "HP × SP.DEF ÷ 100 — Smogon special bulk product: how well this fusion tanks special hits",
        "type": "text",
    },
    "Mixed Bulk": {
        "value": "HP × (DEF + SP.DEF) ÷ 200 — average of physical and special bulk: overall damage-sponge rating",
        "type": "text",
    },
    "Offense": {
        "value": "max(ATK, SP.ATK) — best offensive stat regardless of attack type; higher = harder hitting",
        "type": "text",
    },
    "Type Score": {
        "value": "2×Immunities + Resists − 2×(2x Weak) − 4×(4x Weak) — net defensive typing quality; positive = good coverage",
        "type": "text",
    },
    "HP": {"value": "Hit Points — how much damage can be absorbed", "type": "text"},
    "ATK": {"value": "Attack — power of physical moves", "type": "text"},
    "DEF": {"value": "Defense — physical damage reduction", "type": "text"},
    "SP.ATK": {"value": "Special Attack — power of special moves", "type": "text"},
    "SP.DEF": {"value": "Special Defense — special damage reduction", "type": "text"},
    "SPEED": {"value": "Speed — higher speed moves first each turn", "type": "text"},
    "2x Weak": {
        "value": "Number of types that deal 2× damage to this fusion",
        "type": "text",
    },
    "4x Weak": {
        "value": "Number of types that deal 4× damage — double weakness",
        "type": "text",
    },
    "Resists": {"value": "Number of types that deal ½× or ¼× damage", "type": "text"},
    "Immunities": {
        "value": "Number of types that deal 0× damage — full immunity",
        "type": "text",
    },
}


def get_style_conditions(row_alternation: bool = True):

    _data_conditions = [
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
        {
            "if": {"filter_query": "{Total} < 500", "column_id": "Total"},
            "backgroundColor": "#f8d7da",
            "color": "#842029",
        },
        {
            "if": {"filter_query": "{Phys Bulk} >= 100", "column_id": "Phys Bulk"},
            "backgroundColor": "#d4edda",
            "color": "#155724",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": "{Phys Bulk} >= 60 && {Phys Bulk} < 100", "column_id": "Phys Bulk"},
            "backgroundColor": "#d1e7dd",
            "color": "#0f5132",
        },
        {
            "if": {"filter_query": "{Phys Bulk} < 30 && {Phys Bulk} >= 0", "column_id": "Phys Bulk"},
            "backgroundColor": "#fff3cd",
            "color": "#856404",
        },
        {
            "if": {"filter_query": "{Spec Bulk} >= 100", "column_id": "Spec Bulk"},
            "backgroundColor": "#d4edda",
            "color": "#155724",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": "{Spec Bulk} >= 60 && {Spec Bulk} < 100", "column_id": "Spec Bulk"},
            "backgroundColor": "#d1e7dd",
            "color": "#0f5132",
        },
        {
            "if": {"filter_query": "{Spec Bulk} < 30 && {Spec Bulk} >= 0", "column_id": "Spec Bulk"},
            "backgroundColor": "#fff3cd",
            "color": "#856404",
        },
        {
            "if": {"filter_query": "{Mixed Bulk} >= 100", "column_id": "Mixed Bulk"},
            "backgroundColor": "#cff4fc",
            "color": "#055160",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": "{Mixed Bulk} >= 60 && {Mixed Bulk} < 100", "column_id": "Mixed Bulk"},
            "backgroundColor": "#d1ecf1",
            "color": "#0c5460",
        },
        {
            "if": {"filter_query": "{Mixed Bulk} < 30 && {Mixed Bulk} >= 0", "column_id": "Mixed Bulk"},
            "backgroundColor": "#fff3cd",
            "color": "#856404",
        },
        {
            "if": {"filter_query": "{Offense} >= 130", "column_id": "Offense"},
            "backgroundColor": "#f8d7da",
            "color": "#842029",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": "{Offense} >= 100 && {Offense} < 130", "column_id": "Offense"},
            "backgroundColor": "#ffe5d0",
            "color": "#7b3f00",
        },
        {
            "if": {"filter_query": "{Offense} >= 80 && {Offense} < 100", "column_id": "Offense"},
            "backgroundColor": "#fff3cd",
            "color": "#856404",
        },
        {
            "if": {"filter_query": "{Type Score} >= 8", "column_id": "Type Score"},
            "backgroundColor": "#d4edda",
            "color": "#155724",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": "{Type Score} >= 4 && {Type Score} < 8", "column_id": "Type Score"},
            "backgroundColor": "#d1e7dd",
            "color": "#0f5132",
        },
        {
            "if": {"filter_query": "{Type Score} < 0", "column_id": "Type Score"},
            "backgroundColor": "#f8d7da",
            "color": "#842029",
        },
        {
            "if": {"filter_query": "{4x Weak} > 0", "column_id": "4x Weak"},
            "backgroundColor": "#f8d7da",
            "color": "#842029",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": "{Immunities} > 0", "column_id": "Immunities"},
            "backgroundColor": "#fff3cd",
            "color": "#856404",
            "fontWeight": "bold",
        },
        {
            "if": {"filter_query": "{Resists} >= 5", "column_id": "Resists"},
            "backgroundColor": "#cff4fc",
            "color": "#055160",
        },
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
        {"if": {"column_id": "Ability 1"}, "color": "#0f5132", "fontStyle": "italic"},
        {"if": {"column_id": "Ability 2"}, "color": "#0f5132", "fontStyle": "italic"},
        {"if": {"column_id": "Hidden Ability"}, "color": "#6f42c1", "fontStyle": "italic"},
    ]

    style_conditions = (
        [{"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}] if row_alternation else []
    ) + _data_conditions

    style_cell_conditional = [
        {
            "if": {"column_id": "Add"},
            "width": "44px",
            "minWidth": "44px",
            "maxWidth": "44px",
        },
        {
            "if": {"column_id": "Sprite"},
            "width": "60px",
            "minWidth": "60px",
            "maxWidth": "60px",
            "textAlign": "center",
            "padding": "2px",
        },
        {"if": {"column_id": "Option"}, "width": "80px", "minWidth": "80px"},
        {"if": {"column_id": "Team Score"}, "width": "90px", "minWidth": "90px", "textAlign": "center"},
        {"if": {"column_id": "Name"}, "minWidth": "100px", "width": "120px"},
        {"if": {"column_id": "Types"}, "minWidth": "80px"},
        {"if": {"column_id": "Ability 1"}, "minWidth": "90px", "width": "110px"},
        {"if": {"column_id": "Ability 2"}, "minWidth": "90px", "width": "110px"},
        {"if": {"column_id": "Hidden Ability"}, "minWidth": "100px", "width": "120px"},
        {"if": {"column_id": "Total"}, "width": "60px", "textAlign": "center"},
        {"if": {"column_id": "Phys Bulk"}, "width": "70px", "textAlign": "center"},
        {"if": {"column_id": "Spec Bulk"}, "width": "70px", "textAlign": "center"},
        {"if": {"column_id": "Mixed Bulk"}, "width": "75px", "textAlign": "center"},
        {"if": {"column_id": "Offense"}, "width": "65px", "textAlign": "center"},
        {"if": {"column_id": "Type Score"}, "width": "75px", "textAlign": "center"},
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
