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
            body { background: #E3F2FD; font-size: 13px; }
            .dash-table-container img { width: 44px; height: 44px; object-fit: contain; }
            /* Header hover darkening */
            .dash-table-container th.dash-header:hover { background-color: #146c43 !important; }
            /* Sort icon sizing */
            .dash-table-container .column-header--sort { font-size: 10px; margin-left: 3px; vertical-align: middle; }
            /* Hide ↕ (both-arrows) on unsorted columns; ↑ / ↓ on sorted columns stays visible */
            .dash-table-container .column-header--sort .fa-sort,
            .dash-table-container .column-header--sort svg[data-icon="sort"] { opacity: 0 !important; }
            /* Show faintly on header hover so the user knows columns are sortable */
            .dash-table-container th.dash-header:hover .column-header--sort .fa-sort,
            .dash-table-container th.dash-header:hover .column-header--sort svg[data-icon="sort"] { opacity: 0.45 !important; }
        </style>
        <script>
        (function () {
            /* Set loading="lazy" on every img before the browser initiates requests.
               MutationObserver fires synchronously after React's DOM commit, which is
               before the browser paint/load phase, so lazy is honoured for off-screen
               images even though the attribute is set after insertion. */
            function _lazy(img) {
                if (!img.hasAttribute('loading')) img.setAttribute('loading', 'lazy');
            }
            function _lazyAll(root) {
                root.querySelectorAll('img').forEach(_lazy);
            }
            var _mo = new MutationObserver(function (muts) {
                muts.forEach(function (m) {
                    m.addedNodes.forEach(function (n) {
                        if (n.nodeType !== 1) return;
                        if (n.tagName === 'IMG') _lazy(n);
                        else _lazyAll(n);
                    });
                });
            });
            document.addEventListener('DOMContentLoaded', function () {
                _lazyAll(document);
                _mo.observe(document.body, { childList: true, subtree: true });
            });
        })();
        </script>
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
