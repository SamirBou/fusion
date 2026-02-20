import logging
from pathlib import Path

import dash
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.index_string = '''
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
'''

server = app.server
app.config.suppress_callback_exceptions = True

grid_cache = {}
sprite_rel_cache = {}

def get_repo_root() -> Path:
    return Path(__file__).parent.parent

fusion_pokemon_data = {}
gen_ranges = {}
try:
    data_file = get_repo_root() / "data" / "fusion_pokemon_data.json"
    if data_file.exists():
        import json

        fusion_pokemon_data = json.load(data_file.open())
        by_gen = {}
        for fid, info in fusion_pokemon_data.items():
            gen = info.get("generation", 0)
            by_gen.setdefault(gen, []).append(int(fid))
        for gid, ids in by_gen.items():
            if ids:
                gen_ranges[f"gen{gid}"] = (min(ids), max(ids))
        # Provide sensible defaults if not present
        gen_ranges = {
            "gen1": (1, 151),
            "gen2": (152, 251),
            "gen3": (252, 386),
            "gen4": (387, 493),
            "gen5": (494, 649),
            "gen6": (650, 721),
            "gen7": (722, 809),
        }
except Exception:
    fusion_pokemon_data = {}
    gen_ranges = {
        "gen1": (1, 151),
        "gen2": (152, 251),
        "gen3": (252, 386),
        "gen4": (387, 493),
        "gen5": (494, 649),
        "gen6": (650, 721),
        "gen7": (722, 809),
    }
