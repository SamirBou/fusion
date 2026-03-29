import json
import logging
from pathlib import Path

import dash
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .dash-table-container img { width: 48px !important; height: 48px !important; object-fit: contain; }
            .dash-table-container .dash-table-container .dash-table-cell { font-size: 12px; }
            body { font-size: 13px; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

server = app.server
app.config.suppress_callback_exceptions = True

grid_cache = {}


def get_repo_root() -> Path:
    return Path(__file__).parent.parent


fusion_pokemon_data = {}
gen_ranges = {}


def _init_gen_ranges() -> None:
    try:
        data_file = get_repo_root() / "data" / "fusion_pokemon_data.json"
        if data_file.exists():
            with data_file.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            fusion_pokemon_data.update(raw)
            by_gen: dict[int, list[int]] = {}
            for fid, info in raw.items():
                gen = info.get("generation", 0)
                by_gen.setdefault(gen, []).append(int(fid))
            for gid, ids in by_gen.items():
                if ids:
                    gen_ranges[f"gen{gid}"] = (min(ids), max(ids))
            defaults = {
                "gen1": (1, 151),
                "gen2": (152, 251),
                "gen3": (252, 386),
                "gen4": (387, 493),
                "gen5": (494, 649),
                "gen6": (650, 721),
                "gen7": (722, 809),
            }
            for key, value in defaults.items():
                gen_ranges.setdefault(key, value)
    except Exception:
        gen_ranges.update(
            {
                "gen1": (1, 151),
                "gen2": (152, 251),
                "gen3": (252, 386),
                "gen4": (387, 493),
                "gen5": (494, 649),
                "gen6": (650, 721),
                "gen7": (722, 809),
            }
        )


_init_gen_ranges()
