import json
import logging
from datetime import datetime
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dash_table, dcc, html, no_update

from app import fusion_analyzer, pokemon_data
from app.pokemon_data import POKEMON_NAME_TO_ID as _NAME_TO_ID

logger = logging.getLogger(__name__)
try:
    LOG_DIR = Path(__file__).parent / "logs"
    LOG_DIR.mkdir(exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / "app.log", mode="a", encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    if not any(
        isinstance(h, logging.FileHandler)
        and getattr(h, "baseFilename", None) == str(LOG_DIR / "app.log")
        for h in logger.handlers
    ):
        logger.addHandler(fh)
    logger.setLevel(logging.INFO)
except OSError:
    pass
logger.setLevel(logging.INFO)

from app import app, gen_ranges, grid_cache
from app.pc import create_pokemon_sprite_grid as pc_create_pokemon_sprite_grid
from app.pc import display_box as pc_display_box
from app.pc import render_pc_summary as pc_render_pc_summary
from app.results import (
    COLUMN_TOOLTIPS,
    get_style_cell,
    get_style_conditions,
    get_style_header,
)



app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                [
                    html.H1(
                        "Pokémon Fusion PC",
                        className="text-center my-2",
                        style={"color": "#2E86AB"},
                    ),
                    html.P(
                        "Infinite Fusion stat analyser & team builder",
                        className="text-center text-muted mb-3",
                        style={"fontSize": "14px"},
                    ),
                ]
            )
        ),
        dcc.Tabs(
            id="main-tabs",
            value="browse",
            children=[
                dcc.Tab(
                    label="Browse Pokemon",
                    value="browse",
                    children=[
                        html.H5(
                            "Click a Pokémon to add to PC", style={"color": "#2E86AB"}
                        ),
                        html.Div(
                            id="browse-pc",
                            style={
                                "minHeight": "60px",
                                "display": "flex",
                                "flexWrap": "wrap",
                            },
                        ),
                        dcc.Tabs(
                            id="generation-tabs",
                            value="gen1",
                            children=(
                                [dcc.Tab(label="All", value="all")]
                                + [
                                    dcc.Tab(
                                        label=f"Gen {int(k.replace('gen',''))}", value=k
                                    )
                                    for k in sorted(
                                        gen_ranges.keys(),
                                        key=lambda x: int(x.replace("gen", "")),
                                    )
                                ]
                            ),
                        ),
                        dcc.Input(
                            id="pokemon-search",
                            type="text",
                            placeholder="Search by name or ID...",
                            debounce=True,
                            style={"width": "100%"},
                        ),
                        html.Div(id="pokemon-sprite-grid"),
                    ],
                ),
                dcc.Tab(
                    label="My PC",
                    value="pc",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.H4(
                                        "Your Fusion PC", style={"color": "#2E86AB"}
                                    ),
                                    width=8,
                                ),
                                dbc.Col(
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                "Save PC",
                                                id="save-pc-button",
                                                color="success",
                                                size="sm",
                                            ),
                                            dbc.Button(
                                                "Clear PC",
                                                id="clear-pc-button",
                                                color="danger",
                                                size="sm",
                                            ),
                                        ],
                                        size="sm",
                                    ),
                                    width=4,
                                    style={"textAlign": "right", "paddingTop": "6px"},
                                ),
                            ]
                        ),
                        html.Div(
                            id="box-display",
                            style={
                                "minHeight": "200px",
                                "background": "#f8fbff",
                                "border": "2px solid #cfe6fb",
                                "padding": "12px",
                                "borderRadius": "10px",
                            },
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Button(
                                        "Analyze Fusions",
                                        id="analyze-button",
                                        color="success",
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    html.Div(
                                        id="analysis-status",
                                        style={
                                            "minHeight": "24px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    html.Div(
                                        id="global-pc-summary",
                                        style={"marginTop": "8px", "color": "#6C757D"},
                                    ),
                                    style={"display": "flex", "alignItems": "center"},
                                ),
                            ],
                            align="center",
                            style={"marginTop": "8px"},
                        ),
                    ],
                ),
                dcc.Tab(
                    label="Fusion Results",
                    value="results",
                    children=[
                        html.Div(
                            [
                                html.H6("Your Fusion PC", style={"color": "#2E86AB"}),
                                html.Div(id="results-box-display"),
                            ]
                        ),
                        html.Div(
                            dbc.Row(
                                dbc.Col(
                                    dcc.Loading(
                                        id="loading-output",
                                        children=dash_table.DataTable(
                                            id="table",
                                            columns=[
                                                {
                                                    "name": "Fusion Results",
                                                    "id": "message",
                                                }
                                            ],
                                            data=[
                                                {
                                                    "message": "Please add some Pokémon to your box and click 'Analyze Fusions'."
                                                }
                                            ],
                                            sort_action="native",
                                            sort_by=[{"column_id": "Total", "direction": "desc"}],
                                            style_table={
                                                "overflowX": "auto",
                                                "minWidth": "100%",
                                            },
                                            tooltip_delay=0,
                                            tooltip_duration=3000,
                                            tooltip_data=[],
                                        ),
                                        type="default",
                                    )
                                )
                            ),
                            style={"overflowX": "auto", "width": "100%"},
                        ),
                    ],
                ),
                dcc.Tab(
                    label="Best Team",
                    value="best-team",
                    children=[
                        html.Div(
                            [
                                html.H6("Your Fusion PC", style={"color": "#2E86AB"}),
                                html.Div(id="best-team-box-display"),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="best-team-metric",
                                        options=[
                                            {"label": "Total Stats", "value": "Total"},
                                            {"label": "Composite (Total + Typing)", "value": "Composite"},
                                            {"label": "Mixed Bulk", "value": "Mixed Bulk"},
                                            {"label": "Phys Bulk", "value": "Phys Bulk"},
                                            {"label": "Spec Bulk", "value": "Spec Bulk"},
                                            {"label": "Offense (best Atk)", "value": "Offense"},
                                            {"label": "Type Score", "value": "Type Score"},
                                            {"label": "Attack", "value": "ATK"},
                                            {"label": "Sp. Attack", "value": "SP.ATK"},
                                            {"label": "Speed", "value": "SPEED"},
                                        ],
                                        value="Total",
                                        clearable=False,
                                        style={"width": "220px"},
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "Find Best Team",
                                        id="find-best-team-button",
                                        color="primary",
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    html.Div(
                                        id="best-team-status",
                                        style={
                                            "minHeight": "24px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    width="auto",
                                ),
                            ],
                            align="center",
                            style={"marginTop": "8px", "marginBottom": "8px"},
                        ),
                        html.Div(
                            dbc.Row(
                                dbc.Col(
                                    dcc.Loading(
                                        id="loading-best-team",
                                        children=dash_table.DataTable(
                                            id="best-team-table",
                                            columns=[
                                                {
                                                    "name": "Best Team",
                                                    "id": "message",
                                                }
                                            ],
                                            data=[
                                                {
                                                    "message": "Add Pokémon to your box and click 'Analyze Fusions' to auto-compute teams."
                                                }
                                            ],
                                            sort_action="native",
                                            style_table={
                                                "overflowX": "auto",
                                                "minWidth": "100%",
                                            },
                                            tooltip_delay=0,
                                            tooltip_duration=4000,
                                            tooltip_data=[],
                                        ),
                                        type="default",
                                    )
                                )
                            ),
                            style={"overflowX": "auto", "width": "100%"},
                        ),
                    ],
                ),
                dcc.Tab(
                    label="❓ How to Use",
                    value="guide",
                    children=[
                        dbc.Row(
                            dbc.Col(
                                [
                                    html.H5("How to use Pokémon Fusion PC", className="mb-3", style={"color": "#2E86AB"}),
                                    dbc.Card([
                                        dbc.CardHeader(html.Strong("1 — Browse & build your PC")),
                                        dbc.CardBody([
                                            html.P("Open the Browse Pokémon tab. Use the generation buttons or the search box to find Pokémon.", className="mb-1"),
                                            html.P("Click any sprite to add it to your PC — it highlights blue. Click again to remove it. The strip above the grid always shows your current PC.", className="mb-1"),
                                            html.P("You can add Pokémon from multiple generations to the same PC.", className="mb-0"),
                                        ]),
                                    ], className="mb-3"),
                                    dbc.Card([
                                        dbc.CardHeader(html.Strong("2 — Analyze fusions")),
                                        dbc.CardBody([
                                            html.P("Switch to the My PC tab and click Analyze Fusions. This computes every head→body combination for the Pokémon in your PC.", className="mb-1"),
                                            html.P("Results appear in the Fusion Results tab as a sortable table. Click any column header to sort.", className="mb-1"),
                                            html.P(["Click the sprite image in the Sprite column to open that fusion's page on ", html.A("Infinite Fusion Dex", href="https://infinitefusiondex.com", target="_blank", rel="noopener"), " in a new tab."], className="mb-0"),
                                        ]),
                                    ], className="mb-3"),
                                    dbc.Card([
                                        dbc.CardHeader(html.Strong("3 — Save fusions to your PC")),
                                        dbc.CardBody([
                                            html.P(["In the Fusion Results table, click the ", html.Strong("💾 button"), " on any row to save that fusion pair. The two base Pokémon are automatically removed and replaced with the fusion."], className="mb-0"),
                                        ]),
                                    ], className="mb-3"),
                                    dbc.Card([
                                        dbc.CardHeader(html.Strong("4 — Find the Best Team")),
                                        dbc.CardBody([
                                            html.P("Switch to the Best Team tab. Choose a metric from the dropdown:", className="mb-1"),
                                            html.Ul([
                                                html.Li([html.Strong("Total Stats"), " — raw base stat sum"]),
                                                html.Li([html.Strong("Composite"), " — Total + 20×Type Score; rewards good typing alongside power (recommended)"]),
                                                html.Li([html.Strong("Mixed / Phys / Spec Bulk"), " — tankiness metrics"]),
                                                html.Li([html.Strong("Offense"), " — best of ATK vs SP.ATK"]),
                                                html.Li([html.Strong("Type Score"), " — 2×immunities + resists − 2×(2× weak) − 4×(4× weak)"]),
                                            ], className="mb-2"),
                                            html.P("Click Find Best Team to run the bitmask DP algorithm over all your PC Pokémon (up to 20) and return the top 5 fusion team combinations.", className="mb-0"),
                                        ]),
                                    ], className="mb-3"),
                                    dbc.Card([
                                        dbc.CardHeader(html.Strong("5 — Export & import")),
                                        dbc.CardBody([
                                            html.P(["In the My PC tab, use ", html.Strong("Save PC"), " to download your PC as a JSON file. Reload it by dragging it back in or using the file input."], className="mb-0"),
                                        ]),
                                    ], className="mb-3"),
                                ],
                                lg=8,
                                className="mx-auto",
                            ),
                            className="mt-3",
                        ),
                    ],
                ),
            ],
        ),
        dcc.Store(id="box-store", data=[]),
        dcc.Store(id="selected-pokemon", data=[]),
        dcc.Store(id="fusion-data-store", data=[]),
        dcc.Store(id="analysis-request", data=None),
        dcc.Store(id="best-team-request", data=None),
        dcc.Store(id="best-team-store", data=[]),
        dcc.Store(id="box-highlight-dummy", data=None),
        dcc.Store(id="sprite-open-dummy", data=None),
        dcc.Store(id="best-team-sprite-dummy", data=None),
        dcc.Download(id="download-pc"),
    ],
    fluid=True,
    style={"backgroundColor": "#E3F2FD"},
)


@app.callback(
    Output("box-display", "children"),
    Input("box-store", "data"),
    Input("selected-pokemon", "data"),
)
def display_box(box, selected_pokemon):
    return pc_display_box(box, selected_pokemon)


@app.callback(
    Output("pokemon-sprite-grid", "children"),
    Input("pokemon-search", "value"),
    Input("generation-tabs", "value"),
)
def update_sprite_grid(search, gen):
    try:
        return pc_create_pokemon_sprite_grid(search=search, gen=gen or "all")
    except Exception as e:
        logger.exception(f"Error in update_sprite_grid: {e}")
        return html.Div(f"Error: {e}")


app.clientside_callback(
    """
function(box) {
    var inBox = {};
    if (box) {
        box.forEach(function(pid) { inBox[String(pid)] = true; });
    }
    document.querySelectorAll('[data-pid]').forEach(function(el) {
        var pid = el.getAttribute('data-pid');
        var btn = el.querySelector('button');
        if (btn) {
            btn.style.border = inBox[pid] ? '2px solid #2E86AB' : '2px solid #ccc';
        }
    });
    return null;
}
""",
    Output("box-highlight-dummy", "data"),
    Input("box-store", "data"),
)


app.clientside_callback(
    """
function(active_cell, fusion_rows) {
    if (!active_cell || active_cell.column_id !== 'Sprite' || !fusion_rows) {
        return window.dash_clientside.no_update;
    }
    var row = fusion_rows[active_cell.row];
    if (!row) {
        return window.dash_clientside.no_update;
    }
    var fusionId = row['Fusion ID'] || '';
    var cleanId = String(fusionId).replace(/^#/, '');
    if (!cleanId) {
        return window.dash_clientside.no_update;
    }
    window.open('https://infinitefusiondex.com/details/' + cleanId, '_blank', 'noopener,noreferrer');
    return cleanId;
}
""",
    Output("sprite-open-dummy", "data"),
    Input("table", "active_cell"),
    State("fusion-data-store", "data"),
    prevent_initial_call=True,
)


app.clientside_callback(
    """
function(active_cell, best_team_rows) {
    if (!active_cell || active_cell.column_id !== 'Sprite' || !best_team_rows) {
        return window.dash_clientside.no_update;
    }
    var row = best_team_rows[active_cell.row];
    if (!row) return window.dash_clientside.no_update;
    var fusionId = row['Fusion ID'] || '';
    var cleanId = String(fusionId).replace(/^#/, '');
    if (!cleanId) return window.dash_clientside.no_update;
    window.open('https://infinitefusiondex.com/details/' + cleanId, '_blank', 'noopener,noreferrer');
    return cleanId;
}
""",
    Output("best-team-sprite-dummy", "data"),
    Input("best-team-table", "active_cell"),
    State("best-team-store", "data"),
    prevent_initial_call=True,
)

@app.callback(
    Output("box-store", "data", allow_duplicate=True),
    Input({"type": "sprite-btn", "index": ALL}, "n_clicks"),
    State("box-store", "data"),
    prevent_initial_call=True,
)
def add_from_sprite(n_clicks, box):
    try:
        if not any(n_clicks):
            return no_update
    except Exception:
        if not n_clicks:
            return no_update

    if box is None:
        box = []

    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    added = False
    for trig in ctx.triggered:
        prop = trig.get("prop_id")
        if not prop:
            continue
        button_id = prop.split(".")[0]
        try:
            pokemon_id = json.loads(button_id)["index"]
        except Exception:
            continue

        if not any(str(x) == str(pokemon_id) for x in box):
            try:
                box = box + [int(pokemon_id)]
            except Exception:
                box = box + [pokemon_id]
            added = True

    return box if added else no_update


@app.callback(
    Output("browse-pc", "children"),
    Output("global-pc-summary", "children"),
    Input("box-store", "data"),
)
def update_pc_summaries(box):
    summary = pc_render_pc_summary(box)
    if not box:
        global_text = " (empty)"
    else:
        labels = []
        for i, it in enumerate(box):
            if i >= 6:
                break
            if isinstance(it, str) and it.startswith("fusion_"):
                _, id1, id2 = it.split("_")
                labels.append(f"#{id1}.{id2}")
            else:
                name = pokemon_data.POKEMON_DATA.get(str(it), f"#{it}")
                labels.append(name)
        global_text = f" ({', '.join(labels)})"
        if len(box) > 6:
            global_text += f" +{len(box)-6} more"
    return summary, global_text


@app.callback(
    Output("box-store", "data", allow_duplicate=True),
    Input({"type": "pc-item", "id": ALL}, "n_clicks"),
    State("box-store", "data"),
    prevent_initial_call=True,
)
def pc_item_clicked(n_clicks, box):
    if not any(n_clicks):
        return no_update

    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    try:
        pid = json.loads(button_id)["id"]
    except Exception:
        return no_update

    pid_str = str(pid)
    if "." in pid_str:
        box_key = f'fusion_{pid_str.replace(".", "_")}'
    else:
        try:
            box_key = int(pid_str)
        except Exception:
            box_key = pid_str

    if box_key in box:
        box = [x for x in box if x != box_key]
    else:
        box = box + [box_key]

    return box


@app.callback(
    Output("results-box-display", "children"),
    Input("box-store", "data"),
    Input("selected-pokemon", "data"),
)
def update_results_box(box, selected_pokemon):
    return pc_display_box(box, selected_pokemon)


@app.callback(
    Output("best-team-box-display", "children"),
    Input("box-store", "data"),
    Input("selected-pokemon", "data"),
)
def update_best_team_box(box, selected_pokemon):
    return pc_display_box(box, selected_pokemon)


@app.callback(
    Output("analysis-request", "data"),
    Output("analysis-status", "children"),
    Output("best-team-request", "data", allow_duplicate=True),
    Output("best-team-status", "children", allow_duplicate=True),
    Input("analyze-button", "n_clicks"),
    State("box-store", "data"),
    State("best-team-metric", "value"),
    prevent_initial_call=True,
)
def queue_analysis(n_clicks, box, metric):
    pokemon_ids = [
        item
        for item in (box or [])
        if isinstance(item, int)
        or (isinstance(item, str) and not item.startswith("fusion_"))
    ]

    if not pokemon_ids:
        return (
            no_update,
            html.Span(
                "Add some Pokemon to your box first.",
                style={"color": "#842029", "fontWeight": "600"},
            ),
            no_update,
            no_update,
        )

    ts = datetime.now().isoformat()
    spinner = dbc.Spinner(size="sm", color="primary")
    return (
        {"requested_at": ts, "box": box or [], "n_clicks": n_clicks},
        html.Div(
            [spinner, html.Span("Calculating fusion results...", style={"marginLeft": "8px", "fontWeight": "600", "color": "#0d6efd"})],
            style={"display": "flex", "alignItems": "center"},
        ),
        {
            "requested_at": ts,
            "box": box or [],
            "metric": metric or "Total",
            "option_count": 10,
            "n_clicks": n_clicks,
        },
        html.Div(
            [spinner, html.Span("Finding best teams...", style={"marginLeft": "8px", "fontWeight": "600", "color": "#0d6efd"})],
            style={"display": "flex", "alignItems": "center"},
        ),
    )


@app.callback(
    Output("best-team-request", "data"),
    Output("best-team-status", "children"),
    Input("find-best-team-button", "n_clicks"),
    State("box-store", "data"),
    State("best-team-metric", "value"),
    prevent_initial_call=True,
)
def queue_best_team(n_clicks, box, metric):
    pokemon_ids = [
        item
        for item in (box or [])
        if isinstance(item, int)
        or (isinstance(item, str) and not item.startswith("fusion_"))
    ]
    if len(pokemon_ids) < 2:
        return (
            no_update,
            html.Span(
                "Add at least 2 Pokemon to your box first.",
                style={"color": "#842029", "fontWeight": "600"},
            ),
        )
    return (
        {
            "requested_at": datetime.now().isoformat(),
            "box": box or [],
            "metric": metric or "Total",
            "option_count": 5,
            "n_clicks": n_clicks,
        },
        html.Div(
            [
                dbc.Spinner(size="sm", color="primary"),
                html.Span(
                    "Finding best team...",
                    style={"marginLeft": "8px", "fontWeight": "600", "color": "#0d6efd"},
                ),
            ],
            style={"display": "flex", "alignItems": "center"},
        ),
    )


def _build_table_rows_and_tooltips(fusion_list):
    ordered_data = []
    tooltip_data = []
    for f in fusion_list:
        row = {}
        if "Option" in f:
            row["Option"] = f.get("Option")
        if "Team Score" in f:
            row["Team Score"] = f.get("Team Score")
        row["Add"] = "💾"
        local = f.get("Local Sprite")
        row["Sprite"] = f"![Sprite]({local})" if isinstance(local, str) and local else f.get("Fusion ID", "")
        row["Name"] = f.get("Name")
        raw_types = f.get("Types")
        row["Types"] = ", ".join(map(str, raw_types)) if isinstance(raw_types, (list, tuple)) else raw_types
        for col in ("Ability 1", "Ability 2", "Hidden Ability"):
            row[col] = f.get(col, "—")
        row["Total"] = f.get("Total")
        row["Phys Bulk"] = f.get("Phys Bulk")
        row["Spec Bulk"] = f.get("Spec Bulk")
        row["Mixed Bulk"] = f.get("Mixed Bulk")
        row["Offense"] = f.get("Offense")
        row["HP"] = f.get("HP")
        row["ATK"] = f.get("ATK")
        row["DEF"] = f.get("DEF")
        row["SP.ATK"] = f.get("SP.ATK")
        row["SP.DEF"] = f.get("SP.DEF")
        row["SPEED"] = f.get("SPEED")
        for k in ("Immunities", "Resists", "2x Weak", "4x Weak"):
            v = f.get(k)
            row[k] = len(v) if isinstance(v, (list, tuple)) else v
        row["Type Score"] = f.get("Type Score")
        ordered_data.append(row)
        ab1_desc = f.get("_ab1_desc", "")
        ab2_desc = f.get("_ab2_desc", "")
        abH_desc = f.get("_abH_desc", "")
        tt = {}
        if ab1_desc:
            tt["Ability 1"] = {"value": ab1_desc, "type": "text"}
        if ab2_desc:
            tt["Ability 2"] = {"value": ab2_desc, "type": "text"}
        if abH_desc:
            tt["Hidden Ability"] = {"value": abH_desc, "type": "text"}
        tooltip_data.append(tt)
    return ordered_data, tooltip_data


_BASE_COLUMNS = [
    "Add", "Sprite", "Name", "Types",
    "Ability 1", "Ability 2", "Hidden Ability",
    "Total", "Phys Bulk", "Spec Bulk", "Mixed Bulk", "Offense",
    "HP", "ATK", "DEF", "SP.ATK", "SP.DEF", "SPEED",
    "Type Score", "Immunities", "Resists", "2x Weak", "4x Weak",
]
_PRIVATE_KEYS = {"Sprite", "Local Sprite", "Fusion ID", "_ab1_desc", "_ab2_desc", "_abH_desc"}


def _build_columns(fusion_list):
    leading_columns = [
        col for col in ("Option", "Team Score")
        if any(col in f for f in fusion_list)
    ]
    extra_keys = []
    for f in fusion_list:
        for k in f.keys():
            if k not in leading_columns and k not in _BASE_COLUMNS and k not in _PRIVATE_KEYS and k not in extra_keys:
                extra_keys.append(k)
    cols = []
    for c in leading_columns + _BASE_COLUMNS + extra_keys:
        if c == "Sprite":
            cols.append({"name": c, "id": c, "presentation": "markdown"})
        else:
            cols.append({"name": c, "id": c})
    return cols


_OPTION_PALETTE = [
    "#dbeafe",
    "#dcfce7",
    "#fef9c3",
    "#fce7f3",
    "#ede9fe",
]
_OPTION_TEXT_COLORS = [
    "#1e40af",
    "#166534",
    "#854d0e",
    "#9d174d",
    "#5b21b6",
]


def _option_group_styles(ordered_data):
    styles = []
    for row_idx, row in enumerate(ordered_data):
        opt_label = row.get("Option", "Option 1")
        try:
            opt_num = int(opt_label.split()[-1]) - 1
        except (ValueError, IndexError):
            opt_num = 0
        bg = _OPTION_PALETTE[opt_num % len(_OPTION_PALETTE)]
        fg = _OPTION_TEXT_COLORS[opt_num % len(_OPTION_TEXT_COLORS)]
        styles.append({"if": {"row_index": row_idx}, "backgroundColor": bg})
        styles.append({
            "if": {"row_index": row_idx, "column_id": "Option"},
            "color": fg,
            "fontWeight": "bold",
            "fontSize": "13px",
        })
        styles.append({
            "if": {"row_index": row_idx, "column_id": "Team Score"},
            "fontWeight": "bold",
            "color": fg,
        })
    return styles


def _flatten_team_options(team_options):
    flat_rows = []
    for idx, (team, score) in enumerate(team_options, start=1):
        option_label = f"Option {idx}"
        for fusion in team:
            row = dict(fusion)
            row["Option"] = option_label
            row["Team Score"] = round(score, 1)
            flat_rows.append(row)
    return flat_rows


@app.callback(
    Output("best-team-table", "data"),
    Output("best-team-table", "columns"),
    Output("best-team-table", "style_data_conditional"),
    Output("best-team-table", "style_cell"),
    Output("best-team-table", "style_header"),
    Output("best-team-table", "tooltip_header"),
    Output("best-team-table", "tooltip_data"),
    Output("best-team-store", "data"),
    Output("best-team-status", "children", allow_duplicate=True),
    Input("best-team-request", "data"),
    prevent_initial_call=True,
)
def compute_best_team(request):
    if not request:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    box = request.get("box", [])
    metric = request.get("metric", "Total")
    option_count = max(1, int(request.get("option_count", 3) or 3))

    pokemon_ids = [
        item for item in box
        if isinstance(item, int) or (isinstance(item, str) and not item.startswith("fusion_"))
    ]

    if len(pokemon_ids) < 2:
        msg = [{"message": "Need at least 2 Pokemon to find a team."}]
        cols = [{"name": "Best Team", "id": "message"}]
        return msg, cols, [], {"textAlign": "center", "padding": "20px"}, {}, COLUMN_TOOLTIPS, [], [], ""

    team_options = fusion_analyzer.find_best_teams(
        pokemon_ids,
        metric=metric,
        max_fusions=6,
        max_teams=option_count,
    )

    if not team_options:
        msg = [{"message": "No fusions found for the selected Pokemon."}]
        cols = [{"name": "Best Team", "id": "message"}]
        return msg, cols, [], {"textAlign": "center", "padding": "20px"}, {}, COLUMN_TOOLTIPS, [], [], ""

    flat_team_options = _flatten_team_options(team_options)
    ordered_data, tooltip_data = _build_table_rows_and_tooltips(flat_team_options)
    columns = _build_columns(flat_team_options)
    option_styles = _option_group_styles(ordered_data)
    base_styles = get_style_conditions(row_alternation=False)
    combined_styles = option_styles + base_styles

    return (
        ordered_data,
        columns,
        combined_styles,
        get_style_cell(),
        get_style_header(),
        COLUMN_TOOLTIPS,
        tooltip_data,
        flat_team_options,
        "",
    )


@app.callback(
    Output("box-store", "data", allow_duplicate=True),
    Input({"type": "remove-btn", "item": ALL}, "n_clicks"),
    State("box-store", "data"),
    prevent_initial_call=True,
)
def remove_from_box(n_clicks, box):
    if not any(n_clicks):
        return no_update

    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    item_to_remove = json.loads(button_id)["item"]
    return [i for i in box if i != item_to_remove]


@app.callback(
    Output("box-store", "data", allow_duplicate=True),
    Input("table", "active_cell"),
    State("table", "data"),
    State("box-store", "data"),
    prevent_initial_call=True,
)
def handle_cell_click(active_cell, table_data, box):
    if not active_cell or not table_data:
        return no_update
    if active_cell["column_id"] != "Add":
        return no_update

    row_index = active_cell["row"]
    if row_index >= len(table_data):
        return no_update

    fusion_row = table_data[row_index]
    fusion_name = fusion_row.get("Name", "")
    if "/" not in fusion_name:
        return no_update

    try:
        parts = fusion_name.split("/")
        pokemon1_name = parts[0].strip()
        pokemon2_name = parts[1].strip()
        id1 = _NAME_TO_ID.get(pokemon1_name)
        id2 = _NAME_TO_ID.get(pokemon2_name)
        if id1 is None or id2 is None:
            return no_update

        fusion_key = f"fusion_{id1}_{id2}"
        new_box = []
        for item in box:
            if item == fusion_key:
                continue
            if item in (id1, id2):
                continue
            if isinstance(item, str) and item.startswith("fusion_"):
                fparts = item.replace("fusion_", "").split("_")
                if len(fparts) == 2:
                    try:
                        fid1, fid2 = int(fparts[0]), int(fparts[1])
                        if fid1 in (id1, id2) or fid2 in (id1, id2):
                            continue
                    except Exception:
                        pass
            new_box.append(item)
        new_box.append(fusion_key)
        return new_box
    except Exception:
        return no_update


@app.callback(
    Output("table", "data"),
    Output("table", "columns"),
    Output("table", "style_data_conditional"),
    Output("table", "style_cell"),
    Output("table", "style_header"),
    Output("table", "tooltip_header"),
    Output("table", "tooltip_data"),
    Output("fusion-data-store", "data"),
    Output("analysis-status", "children", allow_duplicate=True),
    Input("analysis-request", "data"),
    Input("table", "active_cell"),
    Input("box-store", "data"),
    State("table", "data"),
    State("fusion-data-store", "data"),
    prevent_initial_call="initial_duplicate",
)
def update_output(analysis_request, active_cell, box, current_table_data, fusion_data_store):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    _empty = (
        [{"message": "Please add some Pokémon to your box and click 'Analyze Fusions'."}],
        [{"name": "Fusion Results", "id": "message"}],
        [],
        {"textAlign": "center", "padding": "20px"},
        {},
        COLUMN_TOOLTIPS,
        [],
        [],
        "",
    )

    if trigger == "box-store" and not box:
        return _empty

    if trigger == "box-store" and current_table_data and box:
        saved_fusions = {
            item for item in box if isinstance(item, str) and item.startswith("fusion_")
        }
        available_pokemon = set()
        for item in box:
            if isinstance(item, int):
                available_pokemon.add(item)

        filtered_data = []
        filtered_store = []
        for i, row in enumerate(current_table_data):
            if row.get("Name", "").count("/") == 1:
                parts = row["Name"].split("/")
                pokemon1_name = parts[0].strip()
                pokemon2_name = parts[1].strip()
                id1 = _NAME_TO_ID.get(pokemon1_name)
                id2 = _NAME_TO_ID.get(pokemon2_name)
                fusion_key = f"fusion_{id1}_{id2}" if id1 and id2 else ""
                if (
                    id1 in available_pokemon
                    and id2 in available_pokemon
                    and fusion_key not in saved_fusions
                ):
                    row_copy = row.copy()
                    row_copy["Add"] = "💾"
                    filtered_data.append(row_copy)
                    if i < len(fusion_data_store or []):
                        filtered_store.append(fusion_data_store[i])
            else:
                filtered_data.append(row)
                if i < len(fusion_data_store or []):
                    filtered_store.append(fusion_data_store[i])

        columns = [{"name": "💾", "id": "Add"}]
        if filtered_data:
            for col in filtered_data[0].keys():
                if col != "Add":
                    if col == "Sprite":
                        columns.append({"name": col, "id": col, "presentation": "markdown"})
                    else:
                        columns.append({"name": col, "id": col})

        return (
            filtered_data,
            columns,
            get_style_conditions(),
            get_style_cell(),
            get_style_header(),
            COLUMN_TOOLTIPS,
            [],
            filtered_store,
            "",
        )

    if trigger == "table":
        return (no_update,) * 9

    if trigger == "analysis-request" and analysis_request:
        analysis_box = analysis_request.get("box") if isinstance(analysis_request, dict) else box
        pokemon_ids = [
            item for item in (analysis_box or [])
            if isinstance(item, int) or (isinstance(item, str) and not item.startswith("fusion_"))
        ]
        if not pokemon_ids:
            return _empty

        fusion_list = fusion_analyzer.analyze_fusions(pokemon_ids)
        if not fusion_list:
            return (
                [{"message": "No data found for the selected Pokémon."}],
                [{"name": "Fusion Results", "id": "message"}],
                [],
                {"textAlign": "center", "padding": "20px"},
                {},
                COLUMN_TOOLTIPS,
                [],
                [],
                "",
            )

        ordered_data, tooltip_data = _build_table_rows_and_tooltips(fusion_list)
        columns = _build_columns(fusion_list)

        return (
            ordered_data,
            columns,
            get_style_conditions(),
            get_style_cell(),
            get_style_header(),
            COLUMN_TOOLTIPS,
            tooltip_data,
            fusion_list,
            "",
        )

    return _empty


@app.callback(
    Output("download-pc", "data"),
    Input("save-pc-button", "n_clicks"),
    State("box-store", "data"),
    prevent_initial_call=True,
)
def save_pc_to_file(n_clicks, box):
    if not box:
        return None

    pokemon_list = []
    fusion_list = []
    for item in box:
        if isinstance(item, int):
            pokemon_list.append(item)
        elif isinstance(item, str) and item.startswith("fusion_"):
            fusion_list.append(item)
        elif isinstance(item, str) and item.isdigit():
            pokemon_list.append(int(item))
        elif isinstance(item, str):
            fusion_list.append(item)

    pc_data = {
        "pokemon": pokemon_list,
        "fusions": fusion_list,
        "timestamp": datetime.now().isoformat(),
    }
    return dict(
        content=json.dumps(pc_data, indent=2),
        filename="pokemon_pc.json",
        type="application/json",
    )


@app.callback(
    Output("box-store", "data", allow_duplicate=True),
    Output("selected-pokemon", "data", allow_duplicate=True),
    Input("clear-pc-button", "n_clicks"),
    prevent_initial_call=True,
)
def clear_pc(n_clicks):
    return [], []


if __name__ == "__main__":
    def _pre_cache_grids():
        try:
            from app.pc import create_pokemon_sprite_grid
            # Pre-cache the default tab (gen1) so first render is instant.
            gen1_key = "gen1_"
            if gen1_key not in grid_cache:
                grid_cache[gen1_key] = create_pokemon_sprite_grid(search=None, gen="gen1")
        except Exception as e:
            logger.warning(f"_pre_cache_grids failed: {e}")

    _pre_cache_grids()

    app.run(
        debug=False,
        port=8051,
        threaded=True,
    )
