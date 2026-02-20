import base64
import json
import logging
import threading
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dash_table, dcc, html, no_update
from flask import Response, abort, send_from_directory

from app import fusion_analyzer, pokemon_data

logger = logging.getLogger(__name__)
try:
    LOG_DIR = Path(__file__).parent / "logs"
    LOG_DIR.mkdir(exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / "desktop_app.log", mode="a", encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(LOG_DIR / "desktop_app.log") for h in logger.handlers):
        logger.addHandler(fh)
    logger.setLevel(logging.INFO)
except Exception:
    pass
logging.getLogger().setLevel(logging.INFO)

from app import app, gen_ranges, grid_cache, server, sprite_rel_cache
from app.pc import create_pokemon_sprite_grid as pc_create_pokemon_sprite_grid
from app.pc import display_box as pc_display_box
from app.pc import render_pc_summary as pc_render_pc_summary
from app.results import (build_pair_score_map, get_style_cell,
                         get_style_conditions, get_style_header, get_tooltips)
from app.sprites import find_sprite_relpath as _find_sprite_relpath
from app.sprites import get_sprite_base64 as _get_sprite_base64


def _safe_str(x):
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Pokémon Fusion PC", className="text-center my-4", style={"color": "#2E86AB"}))),
    dcc.Tabs(id="main-tabs", value="browse", children=[
        dcc.Tab(label="Browse Pokemon", value="browse", children=[
            html.H5("Click a Pokémon to add to PC", style={"color": "#2E86AB"}),
            html.Div(id="browse-pc", style={"minHeight": "60px", "display": "flex", "flexWrap": "wrap"}),
            dcc.Tabs(
                id="generation-tabs",
                value="gen1",
                children=(
                    [dcc.Tab(label="All", value="all")] +
                    [dcc.Tab(label=f"Gen {int(k.replace('gen',''))}", value=k) for k in sorted(gen_ranges.keys(), key=lambda x: int(x.replace('gen','')))]
                ),
            ),
            dcc.Input(id="pokemon-search", type="text", placeholder="Search by name or ID...", style={"width":"100%"}),
            html.Div(id="pokemon-sprite-grid"),
        ]),
        dcc.Tab(label="My PC", value="pc", children=[
            dbc.Row([
                dbc.Col(html.H4("Your Fusion PC", style={"color": "#2E86AB"}), width=8),
                dbc.Col(
                    dbc.ButtonGroup(
                        [
                            dbc.Button("Save PC", id="save-pc-button", color="success", size="sm"),
                            dbc.Button("Clear PC", id="clear-pc-button", color="danger", size="sm"),
                        ],
                        size="sm",
                    ),
                    width=4,
                    style={"textAlign": "right", "paddingTop": "6px"},
                ),
            ]),
            html.Div(id="box-display", style={"minHeight": "200px", "background": "#f8fbff", "border": "2px solid #cfe6fb", "padding": "12px", "borderRadius": "10px"}),
            dbc.Row([
                dbc.Col(dbc.Button("Analyze Fusions", id="analyze-button", color="success"), width="auto"),
                dbc.Col(html.Div(id="global-pc-summary", style={"marginTop": "8px", "color": "#6C757D"}), style={"display": "flex", "alignItems": "center"}),
            ], align="center", style={"marginTop": "8px"}),
        ]),
        dcc.Tab(label="Fusion Results", value="results", children=[
            html.Div([html.H6("Your Fusion PC", style={"color": "#2E86AB"}), html.Div(id="results-box-display")]),
            dbc.Row(dbc.Col(dcc.Loading(id="loading-output", children=dash_table.DataTable(id="table", columns=[{"name": "Fusion Results", "id": "message"}], data=[{"message": "Please add some Pokémon to your box and click 'Analyze Fusions'."}]), type="default"))),
        ])
    ]),
    dcc.Store(id="box-store", data=[]),
    dcc.Store(id="selected-pokemon", data=[]),
    dcc.Store(id="fusion-data-store", data=[]),
    dcc.Download(id="download-pc"),
    dcc.Location(id="url-redirect", refresh=False),
], fluid=True, style={"backgroundColor": "#E3F2FD"})

@app .callback (
Output ("box-display","children"),
Input ("box-store","data"),
Input ("selected-pokemon","data"),
)

def display_box (box ,selected_pokemon ):

    if not box :

        return html .Div (
        "Your Fusion PC is empty. Add some Pokémon and analyze fusions to save pairs you like!",
        style ={"textAlign":"center","color":"#6C757D","fontStyle":"italic"},
        )

    cards =[]

    singles =[
    int (x )
    for x in box
    if isinstance (x ,int )or (isinstance (x ,str )and x .isdigit ())
    ]

    singles_sorted =sorted (set (singles ))

    fusions =[x for x in box if isinstance (x ,str )and x .startswith ("fusion_")]

    def fusion_sort_key (s ):

        parts =s .replace ("fusion_","").split ("_")

        try :

            return (int (parts [0 ]),int (parts [1 ]))

        except :

            return (99999 ,99999 )

    fusions_sorted =sorted (set (fusions ),key =fusion_sort_key )

    ordered_box =[p for p in singles_sorted ]+fusions_sorted

    for i ,item in enumerate (ordered_box ):

        is_selected =item in selected_pokemon

        if isinstance (item ,str )and item .startswith ("fusion_"):

            try :

                _ ,id1 ,id2 =item .split ("_")

                id1 ,id2 =int (id1 ),int (id2 )

                name1 =pokemon_data .POKEMON_DATA .get (str (id1 ),f"#{id1}")

                name2 =pokemon_data .POKEMON_DATA .get (str (id2 ),f"#{id2}")

                fusion_name =f"{name1}/{name2}"

                rel =_find_sprite_relpath (f"{id1}.{id2}")

                if rel :

                    base64_src =_get_sprite_base64 (rel )
                    img_src =base64_src if base64_src else f"/sprites/{rel}"

                    sprite_element =html .Img (
                    src =img_src ,
                    style ={
                    "width":"36px",
                    "height":"36px",
                    "objectFit":"contain",
                    },
                    )

                else :

                    sprite_element =html .Div (
                    f"#{id1}.{id2}",
                    style ={
                    "width":"60px",
                    "height":"60px",
                    "background":"#E9ECEF",
                    "borderRadius":"50%",
                    "display":"flex",
                    "alignItems":"center",
                    "justifyContent":"center",
                    "fontSize":"16px",
                    },
                    )

                card =dbc .Col (
                [
                dbc .Card (
                [
                dbc .CardBody (
                [
                html .Div (
                sprite_element ,
                style ={
                "textAlign":"center",
                "marginBottom":"5px",
                },
                ),
                html .H6 (
                fusion_name ,
                className ="card-title",
                style ={
                "textAlign":"center",
                "fontSize":"10px",
                },
                ),
                html .Div (
                f"#{id1}.{id2}",
                style ={
                "textAlign":"center",
                "fontSize":"10px",
                "color":"#666",
                },
                ),
                dbc .Button (
                "Remove",
                id ={"type":"remove-btn","item":item },
                color ="danger",
                size ="sm",
                style ={"width":"100%"},
                ),
                ],
                style ={"padding":"8px"},
                )
                ],
                style ={
                "border":(
                "2px solid #FF6B6B"
                if is_selected
                else "2px solid #2E86AB"
                ),
                "borderRadius":"10px",
                },
                )
                ],
                width =1 ,
                className ="mb-3",
                )

            except :

                continue

        else :

            pokemon_id =item

            name =pokemon_data .POKEMON_DATA .get (str (pokemon_id ),f"#{pokemon_id}")

            rel =_find_sprite_relpath (str (pokemon_id ))

            if rel :

                base64_src =_get_sprite_base64 (rel )
                img_src =base64_src if base64_src else f"/sprites/{rel}"

                sprite_element =html .Img (
                src =img_src ,
                style ={"width":"48px","height":"48px","objectFit":"contain"},
                )

            else :

                sprite_element =html .Div (
                f"#{pokemon_id}",
                style ={
                "width":"60px",
                "height":"60px",
                "background":"#E9ECEF",
                "borderRadius":"6px",
                "display":"flex",
                "alignItems":"center",
                "justifyContent":"center",
                "fontSize":"16px",
                },
                )

            card =dbc .Col (
            [
            dbc .Card (
            [
            dbc .CardBody (
            [
            html .Div (
            sprite_element ,
            style ={
            "textAlign":"center",
            "marginBottom":"5px",
            },
            ),
            html .H6 (
            name ,
            className ="card-title",
            style ={
            "textAlign":"center",
            "fontSize":"10px",
            },
            ),
            dbc .Button (
            "Remove",
            id ={"type":"remove-btn","item":item },
            color ="danger",
            size ="sm",
            style ={"width":"100%"},
            ),
            ],
            style ={"padding":"8px"},
            )
            ],
            style ={
            "border":(
            "2px solid #FF6B6B"
            if is_selected
            else "2px solid #2E86AB"
            ),
            "borderRadius":"10px",
            },
            )
            ],
            width =1 ,
            className ="mb-3",
            )

        cards .append (card )

    return dbc .Row (cards ,justify ="start")

def render_pc_summary (box ):

    if not box :

        return html .Div ("(empty)",style ={"color":"#6C757D","fontStyle":"italic"})

    items =[]

    for item in box :

        try :

            if isinstance (item ,str )and item .startswith ("fusion_"):

                _ ,id1 ,id2 =item .split ("_")

                pid =f"{int(id1)}.{int(id2)}"

                rel =_find_sprite_relpath (pid )

                if rel :

                    base64_src =_get_sprite_base64 (rel )
                    img_src =base64_src if base64_src else f"/sprites/{rel}"

                    content =html .Img (
                    src =img_src ,
                    style ={
                    "width":"40px",
                    "height":"40px",
                    "objectFit":"contain",
                    },
                    )

                else :

                    content =html .Div (
                    f"#{pid}",
                    style ={
                    "width":"40px",
                    "height":"40px",
                    "display":"flex",
                    "alignItems":"center",
                    "justifyContent":"center",
                    "fontSize":"10px",
                    },
                    )

            else :

                pid =str (item )

                rel =_find_sprite_relpath (pid )

                if rel :

                    base64_src =_get_sprite_base64 (rel )
                    img_src =base64_src if base64_src else f"/sprites/{rel}"

                    content =html .Img (
                    src =img_src ,
                    style ={
                    "width":"40px",
                    "height":"40px",
                    "objectFit":"contain",
                    },
                    )

                else :

                    name =pokemon_data .POKEMON_DATA .get (pid ,f"#{pid}")

                    content =html .Div (
                    f"#{pid}",
                    title =name ,
                    style ={
                    "width":"40px",
                    "height":"40px",
                    "display":"flex",
                    "alignItems":"center",
                    "justifyContent":"center",
                    "fontSize":"10px",
                    },
                    )

            btn =dbc .Button (
            content ,
            id ={"type":"pc-item","id":pid },
            color ="light",
            size ="sm",
            style ={
            "padding":"2px",
            "margin":"3px",
            "minWidth":"40px",
            "minHeight":"40px",
            },
            )

            items .append (btn )

        except Exception :

            continue

    return html .Div (
    items ,style ={"display":"flex","flexWrap":"wrap","alignItems":"center"}
    )

@app .callback (
Output ("pokemon-sprite-grid","children"),
Input ("generation-tabs","value"),
Input ("box-store","data"),
Input ("pokemon-search","value"),
)

def update_sprite_grid (generation_value ,box ,search ):

    effective_gen =generation_value or "all"

    logger .info (
    f"update_sprite_grid called with gen={_safe_str(effective_gen)}, search={_safe_str(search)}"
    )

    try :
        return pc_create_pokemon_sprite_grid(page=1, box_data=box, search=search, gen=effective_gen)
    except Exception as e :
        logger .exception (f"Error in update_sprite_grid: {e}")
        return html .Div (f"Error: {e}")

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Input ({"type":"sprite-btn","index":ALL },"n_clicks"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def add_from_sprite (n_clicks ,box ):

    try:
        if not any(n_clicks):
            return no_update
    except Exception:
        if not n_clicks:
            return no_update

    if box is None :

        box =[]

    ctx =dash .callback_context

    try:
        if not ctx.triggered:
            return no_update
    except Exception:
        return no_update

    added =False

    for trig in ctx .triggered :

        prop =trig .get ("prop_id")

        if not prop :

            continue

        button_id =prop .split (".")[0 ]
        try:
            pokemon_id = eval(button_id)["index"]
        except Exception:
            continue

        exists =any (str (x )==str (pokemon_id )for x in box )

        if not exists :

            try :

                box =box +[int (pokemon_id )]

            except Exception :

                box =box +[pokemon_id ]

            added =True

        else :

            pass

    return box if added else no_update

@app .callback (
Output ("browse-pc","children"),
Output ("global-pc-summary","children"),
Input ("box-store","data"),
)

def update_pc_summaries (box ):

    summary =pc_render_pc_summary(box)

    logger .info (f"Updating PC summaries; box={box}")

    if not box :

        global_text =" (empty)"

    else :

        labels =[]

        for i ,it in enumerate (box ):

            if i >=6 :

                break

            if isinstance (it ,str )and it .startswith ("fusion_"):

                _ ,id1 ,id2 =it .split ("_")

                labels .append (f"#{id1}.{id2}")

            else :

                name =pokemon_data .POKEMON_DATA .get (str (it ),f"#{it}")

                labels .append (name )

        global_text =f" ({', '.join(labels)})"

        if len (box )>6 :

            global_text +=f" +{len(box)-6} more"

    return summary ,global_text

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Input ({"type":"pc-item","id":ALL },"n_clicks"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def pc_item_clicked (n_clicks ,box ):

    try :

        logger .info (
        f"pc_item_clicked triggered: n_clicks={n_clicks} box={box} ctx={repr(dash.callback_context.triggered)}"
        )

    except Exception :

        pass

    if not any (n_clicks ):

        return no_update

    ctx =dash .callback_context

    if not ctx .triggered :

        return no_update

    button_id =ctx .triggered [0 ]["prop_id"].split (".")[0 ]

    try :

        pid =eval (button_id )["id"]

    except Exception :

        return no_update

    logger .info (f"PC item clicked: {button_id} -> {pid}; box before: {box}")

    if pid in box :

        try :

            box =[x for x in box if str (x )!=str (pid )]

        except Exception :

            pass

    else :

        try :

            if "."in str (pid ):

                box =box +[f'fusion_{pid.replace(".", "_")}']

            else :

                box =box +[int (pid )]

        except Exception :

            pass

    return box

@app .callback (
Output ("results-box-display","children"),
Input ("box-store","data"),
Input ("selected-pokemon","data"),
)

def update_results_box (box ,selected_pokemon ):

    return display_box (box ,selected_pokemon )

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Input ({"type":"remove-btn","item":ALL },"n_clicks"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def remove_from_box (n_clicks ,box ):

    if not any (n_clicks ):

        return box

    ctx =dash .callback_context

    if not ctx .triggered :

        return box

    button_id =ctx .triggered [0 ]["prop_id"].split (".")[0 ]

    item_to_remove =eval (button_id )["item"]

    box =[i for i in box if i !=item_to_remove ]

    return box

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Input ("table","active_cell"),
State ("table","data"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def handle_cell_click (active_cell ,table_data ,box ):
    """Handle clicking on 'Add to PC' column to save fusion and remove individual Pokemon"""

    try :

        logger .info (
        f"handle_cell_click triggered: active_cell={active_cell} table_rows={len(table_data) if table_data else 0} box={box}"
        )

    except Exception :

        pass

    if not active_cell or not table_data :

        return no_update

    if active_cell ["column_id"]!="Add":

        return no_update

    row_index =active_cell ["row"]

    if row_index >=len (table_data ):

        return no_update

    fusion_row =table_data [row_index ]

    fusion_name =fusion_row .get ("Name","")

    row_id =fusion_row .get ("_row_id")

    if "/"not in fusion_name :

        return no_update

    try :

        parts =fusion_name .split ("/")

        pokemon1_name =parts [0 ].strip ()

        pokemon2_name =parts [1 ].strip ()

        id1 =None

        id2 =None

        for pid ,pname in pokemon_data .POKEMON_DATA .items ():

            if pname ==pokemon1_name :

                id1 =int (pid )

            if pname ==pokemon2_name :

                id2 =int (pid )

        if id1 is None or id2 is None :

            return no_update

        fusion_key =f"fusion_{id1}_{id2}"

        if fusion_key not in box :

            box .append (fusion_key )

        new_box =[]

        for item in box :

            if item ==fusion_key :

                new_box .append (item )

            elif item in [id1 ,id2 ]:

                continue

            elif isinstance (item ,str )and item .startswith ("fusion_"):

                parts =item .replace ("fusion_","").split ("_")

                if len (parts )==2 :

                    try :

                        fusion_id1 =int (parts [0 ])

                        fusion_id2 =int (parts [1 ])

                        if fusion_id1 not in [id1 ,id2 ]and fusion_id2 not in [
                        id1 ,
                        id2 ,
                        ]:

                            new_box .append (item )

                    except :

                        new_box .append (item )

            else :

                new_box .append (item )

        box =new_box

    except Exception as e :

        print (f"Error parsing fusion: {e}")

        return no_update

    return box

@app .callback (
Output ('table','data'),
Output ('table','columns'),
Output ('table','style_data_conditional'),
Output ('table','style_cell'),
Output ('table','style_header'),
Output ('table','tooltip_data'),
Output ('fusion-data-store','data'),
Input ('analyze-button','n_clicks'),
Input ('table','active_cell'),
Input ('box-store','data'),
State ('table','data'),
State ('fusion-data-store','data'),
prevent_initial_call =False
)

def update_output (n_clicks ,active_cell ,box ,current_table_data ,fusion_data_store ):
    ctx =dash .callback_context
    trigger =ctx .triggered [0 ]['prop_id'].split ('.')[0 ]if ctx .triggered else None

    if trigger =='box-store'and not box :
        return ([{"message":"Please add some Pokémon to your box and click 'Analyze Fusions'."}],[{"name":"Fusion Results","id":"message"}],[],{'textAlign':'center','padding':'20px'},{},[],[])

    if trigger =='box-store'and current_table_data and box :
        saved_fusions ={item for item in box if isinstance (item ,str )and item .startswith ('fusion_')}
        available_pokemon =set ()
        for item in box :
            if isinstance (item ,int ):
                available_pokemon .add (item )

        filtered_data =[]
        filtered_store =[]
        for i ,row in enumerate (current_table_data ):
            if row .get ('Name','').count ('/')==1 :
                parts =row ['Name'].split ('/')
                pokemon1_name =parts [0 ].strip ()
                pokemon2_name =parts [1 ].strip ()

                id1 =id2 =None
                for pid ,pname in pokemon_data .POKEMON_DATA .items ():
                    if pname ==pokemon1_name :
                        id1 =int (pid )
                    if pname ==pokemon2_name :
                        id2 =int (pid )

                fusion_key =f'fusion_{id1}_{id2}'if id1 and id2 else ''
                if (id1 in available_pokemon and id2 in available_pokemon and fusion_key not in saved_fusions ):
                    row_copy =row .copy ()
                    row_copy ['Add']='💾'
                    filtered_data .append (row_copy )
                    if i <len (fusion_data_store or []):
                        filtered_store .append (fusion_data_store [i ])
            else :
                filtered_data .append (row )
                if i <len (fusion_data_store or []):
                    filtered_store .append (fusion_data_store [i ])

        style_conditions =get_style_conditions ()
        style_conditions .append ({'if':{'filter_query':'{Add} = "✅"','column_id':'Add'},'backgroundColor':'#DC3545','color':'#ffffff','fontWeight':'bold','cursor':'default','textAlign':'center','fontSize':'18px'})

        columns =[{"name":"💾","id":"Add"}]
        if filtered_data and len (filtered_data )>0 :
            for col in filtered_data [0 ].keys ():
                if col !='Add':
                    if col =='Sprite':
                        columns .append ({"name":col ,"id":col ,"presentation":"markdown"})
                    else :
                        columns .append ({"name":col ,"id":col })

        return filtered_data ,columns ,style_conditions ,get_style_cell (),get_style_header (),get_tooltips (len (filtered_data )),filtered_store

    if trigger =='table'and active_cell and active_cell .get ('column_id')=='Sprite'and current_table_data and fusion_data_store :
        row_index =active_cell ['row']
        if row_index <len (fusion_data_store or []):
            fusion_url =fusion_data_store [row_index ].get ('Fusion URL','')
            if fusion_url :
                import webbrowser
                webbrowser .open (fusion_url )
        return no_update

    if trigger =='table':
        return no_update

    if trigger =='analyze-button'and n_clicks :
        pokemon_ids =[item for item in (box or [])if isinstance (item ,int )or (isinstance (item ,str )and not item .startswith ('fusion_'))]
        if not pokemon_ids :
            return ([{"message":"Please add some Pokémon to your box and click 'Analyze Fusions'."}],[{"name":"Fusion Results","id":"message"}],[],{'textAlign':'center','padding':'20px'},{},[],[])

        fusion_list =fusion_analyzer .analyze_fusions (pokemon_ids )
        if not fusion_list :
            return ([{"message":"No data found for the selected Pokémon."}],[{"name":"Fusion Results","id":"message"}],[],{'textAlign':'center','padding':'20px'},{},[],[])

        base_cols =["Add","Sprite","Name","Types","Total","Defensive","Bulk","HP","ATK","DEF","SP.ATK","SP.DEF","SPEED","Immunities","Resists","2x Weak","4x Weak"]

        extra_keys =[]
        for f in fusion_list :
            for k in f .keys ():
                if k not in ("Sprite","Local Sprite","Fusion ID","Fusion URL","Name","Types","Total","Defensive","Bulk","HP","ATK","DEF","SP.ATK","SP.DEF","SPEED","Immunities","Resists","2x Weak","4x Weak"):
                    if k not in extra_keys :
                        extra_keys .append (k )

        columns =[]
        for c in base_cols +extra_keys :
            if c =="Sprite":
                columns .append ({"name":c ,"id":c ,"presentation":"markdown"})
            else :
                columns .append ({"name":c ,"id":c })

        ordered_data =[]
        for f in fusion_list :
            row ={}

            row ["Add"]="💾"

            provided_sprite =f .get ("Sprite")
            if isinstance (provided_sprite ,str )and provided_sprite .strip ().startswith (("!","[")):
                row ["Sprite"]=provided_sprite
            else :
                local =f .get ("local_sprite")or f .get ("Local Sprite")or f .get ("LocalSprite")
                sprite_url =f .get ("sprite_url")or f .get ("Sprite")

                use_src =None
                if isinstance (local ,str )and local :
                    use_src =local
                elif isinstance (sprite_url ,str )and sprite_url :
                    use_src =sprite_url

                if use_src :

                    try :
                        s =str (use_src ).replace ('\\','/').lstrip ()

                        if s .startswith ('/sprites/')or s .startswith ('http'):
                            src =s
                        else :

                            if 'data/sprites/'in s :
                                rel =s .split ('data/sprites/')[-1 ]
                                src ='/'+rel .lstrip ('/')
                                if not src .startswith ('/sprites/'):
                                    src ='/sprites/'+src .lstrip ('/')
                            else :

                                filename =s .split ('/')[-1 ]
                                rel =None
                                try :
                                    rel =_find_sprite_relpath (filename )
                                    if not rel :
                                        stem =filename .rsplit ('.',1 )[0 ]
                                        rel =_find_sprite_relpath (stem )
                                except Exception :
                                    rel =None
                                if rel :
                                    src =f"/sprites/{rel}"
                                else :

                                    src =s if s .startswith ('/')or s .startswith ('http')else '/'+s .lstrip ('./')
                    except Exception :
                        src =use_src
                    row ["Sprite"]=f"![Sprite]({src})"
                else :
                    row ["Sprite"]=""

            row ["Name"]=f .get ("Name")
            raw_types = f.get("Types")
            if isinstance(raw_types, (list, tuple)):
                row["Types"] = ", ".join(map(str, raw_types))
            else:
                row["Types"] = raw_types
            row ["Total"]=f .get ("Total")
            row ["Defensive"]=f .get ("Defensive")
            row ["Bulk"]=f .get ("Bulk")
            row ["HP"]=f .get ("HP")
            row ["ATK"]=f .get ("ATK")
            row ["DEF"]=f .get ("DEF")
            row ["SP.ATK"]=f .get ("SP.ATK")
            row ["SP.DEF"]=f .get ("SP.DEF")
            row ["SPEED"]=f .get ("SPEED")
            for k in ("Immunities", "Resists", "2x Weak", "4x Weak"):
                v = f.get(k)
                if isinstance(v, (list, tuple)):
                    row[k] = ", ".join(map(str, v))
                else:
                    row[k] = v

            for k in extra_keys :
                v = f.get(k)
                if isinstance(v, (list, tuple)):
                    row[k] = ", ".join(map(str, v))
                else:
                    row[k] = v

            row ["_row_id"]=len (ordered_data )

            ordered_data .append (row )

        return ordered_data ,columns ,get_style_conditions (),get_style_cell (),get_style_header (),get_tooltips (len (ordered_data )),fusion_list

    return ([{"message":"Please add some Pokémon to your box and click 'Analyze Fusions'."}],[{"name":"Fusion Results","id":"message"}],[],{'textAlign':'center','padding':'20px'},{},[],[])

def get_style_conditions ():

    style_conditions =[
    {"if":{"row_index":"odd"},"backgroundColor":"#f8f9fa"},
    {
    "if":{"filter_query":"{Total} >= 600","column_id":"Total"},
    "backgroundColor":"#d4edda",
    "color":"#155724",
    "fontWeight":"bold",
    },
    {
    "if":{
    "filter_query":"{Total} >= 550 && {Total} < 600",
    "column_id":"Total",
    },
    "backgroundColor":"#d1e7dd",
    "color":"#0f5132",
    },
    {
    "if":{
    "filter_query":"{Total} >= 500 && {Total} < 550",
    "column_id":"Total",
    },
    "backgroundColor":"#fff3cd",
    "color":"#856404",
    },
    {
    "if":{"filter_query":"{Total} < 500","column_id":"Total"},
    "backgroundColor":"#f8d7da",
    "color":"#842029",
    },
    {
    "if":{"filter_query":"{Defensive} >= 50","column_id":"Defensive"},
    "backgroundColor":"#d4edda",
    "color":"#155724",
    "fontWeight":"bold",
    },
    {
    "if":{
    "filter_query":"{Defensive} >= 30 && {Defensive} < 50",
    "column_id":"Defensive",
    },
    "backgroundColor":"#d1e7dd",
    "color":"#0f5132",
    },
    {
    "if":{
    "filter_query":"{Defensive} < 30 && {Defensive} >= 0",
    "column_id":"Defensive",
    },
    "backgroundColor":"#fff3cd",
    "color":"#856404",
    },
    {
    "if":{"filter_query":"{Bulk} >= 100","column_id":"Bulk"},
    "backgroundColor":"#cff4fc",
    "color":"#055160",
    "fontWeight":"bold",
    },
    {
    "if":{"filter_query":"{4x Weak} > 0","column_id":"4x Weak"},
    "backgroundColor":"#f8d7da",
    "color":"#842029",
    "fontWeight":"bold",
    },
    {
    "if":{"filter_query":"{Immunities} > 0","column_id":"Immunities"},
    "backgroundColor":"#fff3cd",
    "color":"#856404",
    "fontWeight":"bold",
    },
    {
    "if":{"filter_query":"{Resists} >= 5","column_id":"Resists"},
    "backgroundColor":"#cff4fc",
    "color":"#055160",
    },
    {
    "if":{"column_id":"Add"},
    "backgroundColor":"#28A745",
    "color":"#ffffff",
    "fontWeight":"bold",
    "cursor":"pointer",
    "textAlign":"center",
    "fontSize":"18px",
    },
    {"if":{"column_id":"Sprite"},"cursor":"pointer"},
    ]

    style_cell_conditional =[
    {
    "if":{"column_id":"Add"},
    "width":"44px",
    "minWidth":"44px",
    "maxWidth":"44px",
    },
    {
    "if":{"column_id":"Sprite"},
    "width":"60px",
    "minWidth":"60px",
    "maxWidth":"60px",
    "textAlign":"center",
    "padding":"2px",
    },
    {"if":{"column_id":"Name"},"minWidth":"100px","width":"120px"},
    {"if":{"column_id":"Types"},"minWidth":"80px"},
    {
    "if":{"column_id":"Rating"},
    "width":"70px",
    "textAlign":"center",
    "fontWeight":"bold",
    },
    {"if":{"column_id":"Offense"},"width":"70px","textAlign":"center"},
    {"if":{"column_id":"Defense"},"width":"70px","textAlign":"center"},
    {"if":{"column_id":"Speed Tier"},"width":"80px","textAlign":"center"},
    {"if":{"column_id":"Total"},"width":"60px","textAlign":"center"},
    {"if":{"column_id":"HP"},"width":"50px","textAlign":"center"},
    {"if":{"column_id":"ATK"},"width":"50px","textAlign":"center"},
    {"if":{"column_id":"DEF"},"width":"50px","textAlign":"center"},
    {"if":{"column_id":"SP.ATK"},"width":"55px","textAlign":"center"},
    {"if":{"column_id":"SP.DEF"},"width":"55px","textAlign":"center"},
    {"if":{"column_id":"SPEED"},"width":"55px","textAlign":"center"},
    ]

    return style_conditions +style_cell_conditional

def get_style_cell ():

    return {
    "backgroundColor":"#ffffff",
    "color":"#000000",
    "textAlign":"left",
    "padding":"6px",
    "border":"1px solid #dee2e6",
    "minWidth":"40px",
    "whiteSpace":"normal",
    "height":"auto",
    "fontSize":"12px",
    }

def get_style_header ():

    return {
    "backgroundColor":"#198754",
    "color":"#ffffff",
    "fontWeight":"bold",
    "border":"1px solid #198754",
    "textAlign":"center",
    "fontSize":"12px",
    }

def get_tooltips (length ):

    return [
    {
    "Add":{"value":"Click to save this fusion to your PC","type":"text"},
    "Sprite":{"value":"Click to view on Infinite Fusion Dex","type":"text"},
    "Rating":{
    "value":"Overall competitive viability (0-100). Considers offense, defense, speed, typing, and stat distribution.",
    "type":"markdown",
    },
    "Offense":{
    "value":"Offensive capability: highest attack stat + mixed offense bonus + speed factor",
    "type":"markdown",
    },
    "Defense":{
    "value":"Defensive capability: (HP × DEF/100 + HP × SP.DEF/100)/2 + type effectiveness",
    "type":"markdown",
    },
    "Speed Tier":{
    "value":"Speed tier bonus: 25 (130+), 20 (110+), 15 (90+), 10 (70+), 5 (50+), 0 (<50)",
    "type":"markdown",
    },
    }
    for _ in range (length )
    ]

def build_pair_score_map (pokemon_ids ):
    """Return a dict mapping frozenset({a,b}) -> score (Total + Defensive) using fusion_analyzer."""

    scores ={}

    try :

        fusion_list =fusion_analyzer .analyze_fusions (pokemon_ids )

        for f in fusion_list :

            fid =f .get ("Fusion ID")

            if not fid :

                continue

            parts =fid .replace ("#","").split (".")

            if len (parts )!=2 :

                continue

            a ,b =int (parts [0 ]),int (parts [1 ])

            key =frozenset ({a ,b })

            total =f .get ("Total",0 )or 0

            defensive =f .get ("Defensive",0 )or 0

            scores [key ]=total +defensive

    except Exception as e :

        logger .warning (f"Error building pair scores: {e}")

    return scores

@app .callback (
Output ("selected-pokemon","data"),
Input ({"type":"pokemon-select","index":ALL },"n_clicks"),
State ("box-store","data"),
State ("selected-pokemon","data"),
prevent_initial_call =True ,
)

def toggle_pokemon_selection (n_clicks ,box ,selected_pokemon ):

    if not any (n_clicks ):

        return selected_pokemon

    ctx =dash .callback_context

    if not ctx .triggered :

        return selected_pokemon

    button_id =ctx .triggered [0 ]["prop_id"].split (".")[0 ]

    index =eval (button_id )["index"]

    sorted_unique_box =sorted (set (box ),key =lambda x :str (x ))

    if index <len (sorted_unique_box ):

        item =sorted_unique_box [index ]

        if item in selected_pokemon :

            selected_pokemon .remove (item )

        else :

            selected_pokemon .append (item )

    return selected_pokemon

@app .callback (
Output ("download-pc","data"),
Input ("save-pc-button","n_clicks"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def save_pc_to_file (n_clicks ,box ):

    if not box :

        return None

    pokemon_list =[]

    fusion_list =[]

    for item in box :

        if isinstance (item ,int ):

            pokemon_list .append (item )

        elif isinstance (item ,str )and item .startswith ("fusion_"):

            fusion_list .append (item )

        elif isinstance (item ,str )and item .isdigit ():

            pokemon_list .append (int (item ))

        elif isinstance (item ,str ):

            fusion_list .append (item )

    pc_data ={
    "pokemon":pokemon_list ,
    "fusions":fusion_list ,
    "timestamp":"2025-10-12",
    }

    return dict (
    content =json .dumps (pc_data ,indent =2 ),
    filename ="pokemon_pc.json",
    type ="application/json",
    )

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Output ("upload-pc","contents"),
Input ("upload-pc","contents"),
State ("upload-pc","filename"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def load_pc_from_file (contents ,filename ,current_box ):

    if contents is None :

        print ("Load PC: No contents provided")

        return no_update ,no_update

    try :

        content_string =contents .split (",")[1 ]

        import base64

        decoded =base64 .b64decode (content_string )

        pc_data =json .loads (decoded .decode ("utf-8"))

        loaded_items =[]

        if "pokemon"in pc_data :

            for item in pc_data ["pokemon"]:

                if isinstance (item ,int ):

                    loaded_items .append (item )

                elif isinstance (item ,str )and item .isdigit ():

                    loaded_items .append (int (item ))

        if "fusions"in pc_data :

            for item in pc_data ["fusions"]:

                if isinstance (item ,str ):

                    loaded_items .append (item )

        return loaded_items ,None

    except Exception as e :

        print (f"Error loading PC: {e}")

        import traceback

        traceback .print_exc ()

        return no_update ,no_update

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Output ("selected-pokemon","data",allow_duplicate =True ),
Input ("clear-pc-button","n_clicks"),
prevent_initial_call =True ,
)

def clear_pc (n_clicks ):

    return [],[]

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Output ("selected-pokemon","data",allow_duplicate =True ),
Input ("move-selected-button","n_clicks"),
State ("box-store","data"),
State ("selected-pokemon","data"),
prevent_initial_call =True ,
)

def move_selected_pokemon (n_clicks ,box ,selected_pokemon ):

    if not selected_pokemon :

        return box ,selected_pokemon

    remaining_box =[pid for pid in box if pid not in selected_pokemon ]

    return remaining_box ,[]

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Input ("table","selected_rows"),
State ("table","data"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def save_pair_from_table (selected_rows ,table_data ,box ):

    try :

        logger .info (
        f"save_pair_from_table triggered: selected_rows={selected_rows} box={box}"
        )

    except Exception :

        pass

    if not selected_rows or not table_data :

        return box

    selected_row_index =selected_rows [0 ]

    if selected_row_index <len (table_data ):

        selected_row =table_data [selected_row_index ]

        pair_str =selected_row .get ("Save Pair","")

        if pair_str and pair_str .startswith ("#"):

            try :

                ids =pair_str [1 :].split (".")

                id1 ,id2 =int (ids [0 ]),int (ids [1 ])

                fusion_key =f"fusion_{id1}_{id2}"

                if fusion_key not in box :

                    box .append (fusion_key )

                return box

            except :

                pass

    return box

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Input ({"type":"team-member-add","pid":ALL },"n_clicks"),
State ("box-store","data"),
prevent_initial_call =True ,
)

def add_team_member (n_clicks ,box ):

    try :

        logger .info (
        f"add_team_member triggered: n_clicks={n_clicks} box={box} ctx={repr(dash.callback_context.triggered)}"
        )

    except Exception :

        pass

    if not any (n_clicks ):

        return no_update

    ctx =dash .callback_context

    if not ctx .triggered :

        return no_update

    button_id =ctx .triggered [0 ]["prop_id"].split (".")[0 ]

    try :

        pid =eval (button_id )["pid"]

    except Exception :

        return no_update

    try :

        if int (pid )not in box :

            box =box +[int (pid )]

            logger .info (f"add_team_member: added pid={pid} -> new box={box}")

    except Exception :

        pass

    return box

@app .callback (
Output ("box-store","data",allow_duplicate =True ),
Output ("fusion-data-store","data",allow_duplicate =True ),
Input ({"type":"add-team","index":ALL },"n_clicks"),
State ("team-data-store","data"),
State ("box-store","data"),
State ("fusion-data-store","data"),
prevent_initial_call =True ,
)

def add_team_to_box (n_clicks ,teams_store ,box ,fusion_store ):

    if not any (n_clicks ):

        return no_update ,no_update

    ctx =dash .callback_context

    if not ctx .triggered :

        return no_update ,no_update

    button_id =ctx .triggered [0 ]["prop_id"].split (".")[0 ]

    try :

        idx =int (eval (button_id )["index"])

    except Exception :

        return no_update ,no_update

    if not teams_store or idx >=len (teams_store ):

        return no_update ,no_update

    team =teams_store [idx ]

    pairs =team .get ("pairs",[])

    if box is None :

        box =[]

    if fusion_store is None :

        fusion_store =[]

    added =False

    for p in pairs :

        a ,b =int (p ["a"]),int (p ["b"])

        key =f"fusion_{a}_{b}"

        if key not in box :

            box .append (key )

            added =True

    try :

        added_pids =set ()

        for p in pairs :

            try :

                added_pids .add (int (p ["a"]))

                added_pids .add (int (p ["b"]))

            except Exception :

                continue

        if added_pids :

            box =[
            item
            for item in box
            if not (isinstance (item ,int )and item in added_pids )
            ]

    except Exception :

        pass

    try :

        new_fstore =[]

        for row in fusion_store :

            fid =row .get ("Fusion ID","")

            if fid and fid .startswith ("#"):

                parts =fid .replace ("#","").split (".")

                try :

                    ia ,ib =int (parts [0 ]),int (parts [1 ])

                except Exception :

                    new_fstore .append (row )

                    continue

                if any (
                (ia ==int (p ["a"])and ib ==int (p ["b"]))
                or (ia ==int (p ["b"])and ib ==int (p ["a"]))
                for p in pairs
                ):

                    continue

                else :

                    new_fstore .append (row )

            else :

                new_fstore .append (row )

    except Exception :

        new_fstore =fusion_store

    return box if added else no_update ,new_fstore

@app .callback (
Output ("team-builder-output","children"),
Output ("team-data-store","data"),
Input ("generate-teams","n_clicks"),
State ("box-store","data"),
State ("team-size","value"),
State ("max-teams","value"),
prevent_initial_call =True ,
)

def render_generated_teams (n_clicks ,box ,team_size ,max_teams ):

    try :

        logger .info (
        f"render_generated_teams triggered: n_clicks={n_clicks} box={box} team_size={team_size} max_teams={max_teams}"
        )

        if not box :

            return html .Div ("Your PC is empty. Add Pokémon to generate teams."),[]

        pool =[
        int (x )
        for x in box
        if isinstance (x ,int )or (isinstance (x ,str )and x .isdigit ())
        ]

        if not pool :

            return html .Div ("No eligible Pokémon in PC to generate teams."),[]

        try :

            ts =int (team_size )if team_size else 6

        except Exception :

            ts =6

        try :

            mt =int (max_teams )if max_teams else 20

        except Exception :

            mt =20

        teams =generate_teams_from_pool (pool ,team_size =ts ,max_teams =mt )

    except Exception as e :

        logger .exception (f"Error generating teams: {e}")

        return html .Div (f"Error generating teams: {e}"),[]

    if not teams :

        return html .Div ("No teams generated."),[]

    try :

        pair_scores =build_pair_score_map (pool )

    except Exception :

        pair_scores ={}

    cards =[]

    from itertools import combinations

    for idx ,t in enumerate (teams ):

        members =(
        list (t ["members"])
        if isinstance (t ["members"],(list ,tuple ))
        else [t ["members"]]
        )

        pairs_for_team =[]

        try :

            import networkx as nx

            Gt =nx .Graph ()

            for m in members :

                Gt .add_node (int (m ))

            for a ,b in combinations (members ,2 ):

                a_i ,b_i =int (a ),int (b )

                w =pair_scores .get (frozenset ({a_i ,b_i }),0 )

                if w :

                    Gt .add_edge (a_i ,b_i ,weight =w )

            matching =nx .algorithms .matching .max_weight_matching (
            Gt ,maxcardinality =False
            )

            for a ,b in matching :

                w =pair_scores .get (frozenset ({a ,b }),0 )

                pairs_for_team .append ({"a":int (a ),"b":int (b ),"score":w })

        except Exception :

            used =set ()

            all_pairs =[]

            for a ,b in combinations (members ,2 ):

                a_i ,b_i =int (a ),int (b )

                all_pairs .append ((pair_scores .get (frozenset ({a_i ,b_i }),0 ),a_i ,b_i ))

            all_pairs .sort (key =lambda x :x [0 ],reverse =True )

            for s ,a ,b in all_pairs :

                if a in used or b in used :

                    continue

                pairs_for_team .append ({"a":a ,"b":b ,"score":s })

                used .update ((a ,b ))

        pair_labels =[]

        paired_ids =set ()

        for p in pairs_for_team :

            a ,b =int (p ["a"]),int (p ["b"])

            paired_ids .update ((a ,b ))

            name_a =pokemon_data .POKEMON_DATA .get (str (a ),f"#{a}")

            name_b =pokemon_data .POKEMON_DATA .get (str (b ),f"#{b}")

            rel =_find_sprite_relpath (f"{a}.{b}")

            if rel :

                img =html .Img (
                src =f"/sprites/{rel}",
                style ={
                "width":"40px",
                "height":"40px",
                "objectFit":"contain",
                "marginRight":"6px",
                "borderRadius":"6px",
                },
                )

            else :

                img =html .Div (
                f"#{a}.{b}",
                style ={
                "width":"40px",
                "height":"40px",
                "display":"flex",
                "alignItems":"center",
                "justifyContent":"center",
                "fontSize":"12px",
                "marginRight":"6px",
                },
                )

            pair_labels .append (
            html .Div (
            [img ,html .Div (f"{name_a} / {name_b}",style ={"fontSize":"12px"})],
            style ={
            "display":"flex",
            "alignItems":"center",
            "marginRight":"8px",
            "marginBottom":"6px",
            },
            )
            )

        member_buttons =[]

        for pid in members :

            if int (pid )in paired_ids :

                continue

            name =pokemon_data .POKEMON_DATA .get (str (pid ),f"#{pid}")

            member_buttons .append (
            dbc .Button (
            name ,
            id ={"type":"team-member-add","pid":str (pid )},
            n_clicks =0 ,
            color ="secondary",
            size ="sm",
            style ={"marginRight":"6px","marginBottom":"4px"},
            )
            )

        pairs =[]

        for a ,b in combinations (members ,2 ):

            a_i ,b_i =int (a ),int (b )

            key =frozenset ({a_i ,b_i })

            score =pair_scores .get (key ,0 )

            pairs .append ({"a":a_i ,"b":b_i ,"score":score })

        pairs =sorted (pairs ,key =lambda x :x ["score"],reverse =True )

        pair_elems =[]

        top_n =min (5 ,len (pairs_for_team ))

        pair_sum =0

        for p in pairs_for_team [:top_n ]:

            pair_sum +=p ["score"]

            a ,b =p ["a"],p ["b"]

            rel =_find_sprite_relpath (f"{a}.{b}")

            if rel :

                src =f"/sprites/{rel}"

            else :

                src =f"https://infinitefusiondex.com/sprites/{a}.{b}.png"

            pair_elems .append (
            html .Div (
            [
            html .Img (
            src =src ,
            style ={
            "width":"44px",
            "height":"44px",
            "objectFit":"contain",
            "marginRight":"6px",
            "borderRadius":"6px",
            },
            ),
            html .Span (f"{p['score']:,}"),
            ],
            style ={
            "display":"inline-flex",
            "alignItems":"center",
            "marginRight":"8px",
            },
            )
            )

        header =html .Div (
        [
        html .B (f"Team #{idx+1} — score: {t.get('score', 0):.0f}"),
        html .Div (
        [
        html .Small (
        "(Score = sum of pair scores; pair score = Total + Defensive from fusion results)",
        style ={"marginLeft":"12px","color":"#6c757d"},
        )
        ],
        style ={"marginLeft":"12px"},
        ),
        html .Div (
        pair_elems ,
        style ={
        "marginLeft":"12px",
        "display":"flex",
        "alignItems":"center",
        },
        ),
        ],
        style ={
        "display":"flex",
        "alignItems":"center",
        "gap":"10px",
        "flexWrap":"wrap",
        },
        )

        actions =dbc .Row (
        [
        dbc .Col (
        dbc .Button (
        "Add Team",
        id ={"type":"add-team","index":idx },
        color ="success",
        size ="sm",
        ),
        width ="auto",
        )
        ],
        align ="center",
        style ={"marginTop":"8px","gap":"8px"},
        )

        card =dbc .Card (
        [
        dbc .CardBody (
        [
        header ,
        html .Div (
        pair_labels ,
        style ={
        "marginTop":"8px",
        "display":"flex",
        "flexWrap":"wrap",
        },
        ),
        html .Div (
        member_buttons ,
        style ={
        "marginTop":"8px",
        "display":"flex",
        "flexWrap":"wrap",
        },
        ),
        actions ,
        team_results_container ,
        ]
        )
        ],
        style ={"marginBottom":"8px"},
        )

        cards .append (card )

    teams_serializable =[]

    for i ,t in enumerate (teams ):

        try :

            members =(
            list (t ["members"])
            if isinstance (t ["members"],(list ,tuple ))
            else [t ["members"]]
            )

            import networkx as nx

            Gt =nx .Graph ()

            for m in members :

                Gt .add_node (int (m ))

            for a ,b in combinations (members ,2 ):

                a_i ,b_i =int (a ),int (b )

                w =pair_scores .get (frozenset ({a_i ,b_i }),0 )

                if w :

                    Gt .add_edge (a_i ,b_i ,weight =w )

            matching =nx .algorithms .matching .max_weight_matching (
            Gt ,maxcardinality =False
            )

            pairs =[
            {
            "a":int (a ),
            "b":int (b ),
            "score":pair_scores .get (frozenset ({int (a ),int (b )}),0 ),
            }
            for a ,b in matching
            ]

        except Exception :

            pairs =[]

            used =set ()

            all_pairs =[]

            for a ,b in combinations (members ,2 ):

                a_i ,b_i =int (a ),int (b )

                all_pairs .append ((pair_scores .get (frozenset ({a_i ,b_i }),0 ),a_i ,b_i ))

            all_pairs .sort (key =lambda x :x [0 ],reverse =True )

            for s ,a ,b in all_pairs :

                if a in used or b in used :

                    continue

                pairs .append ({"a":a ,"b":b ,"score":s })

                used .update ((a ,b ))

        teams_serializable .append (
        {"members":list (t ["members"]),"score":t .get ("score",0 ),"pairs":pairs }
        )

    return dbc .Container (cards ),teams_serializable

if __name__ =="__main__":

    def _prefetch_fusion_sprites ():
        """Background prefetcher: download missing fusion sprites in parallel."""
        try :
            import concurrent.futures

            import requests

            sprites_dir =Path (__file__ ).parent /"data"/"sprites"
            sprites_dir .mkdir (exist_ok =True )

            base_ids =[]
            try :
                base_ids =[int (pid )for pid in pokemon_data .POKEMON_DATA .keys ()]
            except Exception :
                base_ids =[]

            if not base_ids :
                logger .info ("No base IDs found to prefetch")
            else :
                logger .info (f"Starting prefetch of {len(base_ids)} base sprites")

                def _download_base (i ):
                    try :
                        start =((i -1 )//100 )*100 +1
                        end =start +99
                        subdir =f"{start:03d}-{end:03d}"
                        subdir_path =sprites_dir /subdir
                        subdir_path .mkdir (exist_ok =True )
                        target =subdir_path /f"{i}.png"
                        if target .exists ():
                            return True
                        url =f"https://infinitefusiondex.com/sprites/{i}.png"
                        resp =requests .get (url ,timeout =8 ,headers ={"User-Agent":"Mozilla/5.0"})
                        if resp .status_code !=200 :
                            return False
                        data =resp .content
                        if not data :
                            return False
                        tmp =target .with_suffix ('.tmp')
                        tmp .write_bytes (data )
                        tmp .rename (target )
                        return True
                    except Exception as e :
                        logger .warning (f"Base sprite prefetch failed for {i}: {e}")
                        return False

                with concurrent .futures .ThreadPoolExecutor (max_workers =12 )as exe :
                    list (exe .map (_download_base ,base_ids ))

                logger .info ("Base sprite prefetch complete")
        except Exception as e :
            logger .warning (f"Error in prefetcher: {e}")

    threading .Thread (target =_prefetch_fusion_sprites ,daemon =True ).start ()

    try :
        threading .Thread (target =_pre_cache_grids ,daemon =True ).start ()
    except Exception :
        pass

    app .run_server (debug =True ,port =8051 ,threaded =True )
