###########################################
# Build BitCraft dashboard from STDB data #
###########################################

import warnings
warnings.filterwarnings("ignore")

import copy
import json
import requests
import sys
import time

import pandas as pd
import panel as pn

# Fetch STDB schema via SQL query.
def sql_to_schema(sql, json_output=None):
    response = requests.post("https://playtest.spacetimedb.org/database/sql/bitcraft-alpha-3", headers={"token": ""}, data=sql, verify=False)
    try:
        data = response.json()
        if json_output:
            with open(json_output, "w") as f:
                f.write(json.dumps(data, indent=4))
        return data
    except Exception as e:
        print(response.content.decode("UTF-8"))

# Transform STDB schema into readable dict.
def schema_to_dict(schema, json_output=None):
    def schema_to_dict_rec(elements, rows):
        elements = copy.deepcopy(elements)
        rows = copy.deepcopy(rows)
        
        result = [{} for _ in range(len(rows))]
        for i in range(0, len(elements)):
            element_name = elements[i]["name"]["some"]
            
            values = [row[i] for row in rows]
            for j in range(0, len(rows)):
                if "Product" in elements[i]["algebraic_type"]:
                    rec_elements = elements[i]["algebraic_type"]["Product"]["elements"]
                    rec_rows = [values[j]]
                    values[j] = schema_to_dict_rec(rec_elements, rec_rows)[0]
                if "Builtin" in elements[i]["algebraic_type"] and "Array" in elements[i]["algebraic_type"]["Builtin"] and "Product" in elements[i]["algebraic_type"]["Builtin"]["Array"]:
                    rec_elements = elements[i]["algebraic_type"]["Builtin"]["Array"]["Product"]["elements"]
                    rec_rows = values[j]
                    values[j] = schema_to_dict_rec(rec_elements, rec_rows)
                if "Sum" in elements[i]["algebraic_type"]:
                    index = int(list(values[j].keys())[0])
                    rec_result = list(values[j].values())
                    if "Product" in elements[i]["algebraic_type"]["Sum"]["variants"][index]["algebraic_type"]:
                        rec_elements = elements[i]["algebraic_type"]["Sum"]["variants"][index]["algebraic_type"]["Product"]["elements"]
                        rec_rows = rec_result
                        rec_result = schema_to_dict_rec(rec_elements, rec_rows)
                    new_dict = {}
                    new_dict[elements[i]["algebraic_type"]["Sum"]["variants"][index]["name"]["some"]] = rec_result[0]
                    values[j] = new_dict
                result[j][element_name] = values[j]
        return result
    
    elements = schema[0]["schema"]["elements"]
    rows = schema[0]["rows"]
    result = schema_to_dict_rec(elements, rows)
    if json_output:
        with open(json_output, "w") as f:
            f.write(json.dumps(result, indent=4))
    return result

# Fetch STDB data via SQL query.
def sql_to_dict(sql, json_output=None):
    schema = sql_to_schema(sql)
    if schema:
        return schema_to_dict(schema, json_output=json_output)

def find_by_key_value(data, key, value):
    result = []
    for row in data:
        if key in row and row[key] == value:
            result.append(row)
    return result

if __name__ == "__main__":
    # Obtain STDB data from server or cache.
    player_experience_infos = sql_to_dict("select PlayerUsernameState.username, ExperienceState.experience_stacks \
                                           from ExperienceState join PlayerUsernameState \
                                           on PlayerUsernameState.entity_id = ExperienceState.entity_id")
    
    time.sleep(5)
    
    guild_infos = sql_to_dict("select * from ClaimDescriptionState join ClaimTechState \
                               on ClaimTechState.entity_id = ClaimDescriptionState.entity_id")
    
    time.sleep(5)
    
    #trade_deployable_infos = json.load(open("cache/trade_deployable_infos.json"))
    trade_deployable_infos = sql_to_dict("select * from TradeOrderState \
                                          join DeployableState on DeployableState.entity_id = TradeOrderState.shop_entity_id \
                                          join DeployableCollectibleState on DeployableCollectibleState.deployable_entity_id = TradeOrderState.shop_entity_id \
                                          join TradeOrderState on TradeOrderState.shop_entity_id = TradeOrderState.shop_entity_id", json_output="cache/trade_deployable_infos.json")
    #trade_deployable_infos = sql_to_dict("select TradeOrderState.remaining_stock, TradeOrderState.offer_items, \
    #                                      TradeOrderState.offer_cargo_id, TradeOrderState.required_items, \
    #                                      TradeOrderState.required_cargo_id, DeployableState.nickname, DeployableCollectibleState.location, \
    #                                      PlayerUsernameState.username from TradeOrderState \
    #                                      join DeployableState on TradeOrderState.shop_entity_id = DeployableState.entity_id \
    #                                      join PlayerUsernameState on DeployableState.owner_id = PlayerUsernameState.entity_id \
    #                                      join DeployableCollectibleState on TradeOrderState.shop_entity_id = DeployableCollectibleState.deployable_entity_id")
    
    time.sleep(5)
    
    #trade_building_infos = json.load(open("cache/trade_building_infos.json"))
    trade_building_infos = sql_to_dict("select * from TradeOrderState join BuildingState \
                                        on BuildingState.entity_id = TradeOrderState.shop_entity_id \
                                        join LocationState on LocationState.entity_id = TradeOrderState.shop_entity_id \
                                        join TradeOrderState on TradeOrderState.shop_entity_id = TradeOrderState.shop_entity_id \
                                        where BuildingState.constructed_by_player_entity_id != 0", json_output="cache/trade_building_infos.json")
    
    time.sleep(5)
    
    #username_infos = json.load(open("cache/username_infos.json"))
    username_infos = sql_to_dict("select * from PlayerUsernameState", json_output="cache/username_infos.json")
    
    time.sleep(5)
    
    metadata_list = json.load(open("BitCraft.Spacetime_json/.DescList.json"))
    metadata_dicts = {}
    for metadata in metadata_list:
        metadata_dicts[metadata["table"]] = json.load(open("cache/" + metadata["table"] + ".json"))
        #metadata_dicts[metadata["table"]] = sql_to_dict("select * from " + metadata["table"], json_output="cache/" + metadata["table"] + ".json")
        #print("Finished " + metadata["table"])
        #time.sleep(5)
    
    # Create BitCraft entity id lookup maps.
    entity_username_map = {}
    for username in username_infos:
        entity_username_map[username["entity_id"]] = username["username"]
    
    entity_guild_map = {}
    for guild in guild_infos:
        entity_guild_map[guild["entity_id"]] = guild["name"]
    
    entity_buildingdesc_map = {}
    for buildingdesc in metadata_dicts["BuildingDesc"]:
        entity_buildingdesc_map[buildingdesc["id"]] = buildingdesc["name"]
    
    # Custom CSS for the final static HTML.
    CSS = """
    #header {
        visibility: hidden;
        position: absolute;
    }

    .pn-busy-container {
        opacity: 0;
    }
    
    :host .tabulator {
        font-size: 20px;
    }
    
    :host .tabulator-tableholder {
        transform: rotateX(180deg);
    }
    
    :host .tabulator-table {
        max-width: None;
        transform: rotateX(180deg);
    }
    
    :host .bk-input-group {
        font-size: 20px;
    }
    
    :host .bk-header {
        font-size: 20px;
    }
    
    :host .bk-tab {
        width: 100%;
    }
    
    :host .bk-active {
        border: 2px solid #ddd !important;
        border-bottom-width: 0px !important;
        box-shadow: 2px -2px 5px rgba(0, 0, 0, 0.1) !important;
    }
    """

    # Initialize Panel dashboard website builder library. Include "extras.js" helper functions.
    pn.extension("mathjax", design="bootstrap", js_files={"extras": "extras.js"}, raw_css=[CSS])

    # The building of the following dashboards generally consists of three operations:
    # 1. The parsing of the dashboard's data from the source STDB data.
    # 2. The initialization and configuring of the dashboard's Tabulator object.
    # 3. Creating the JavaScript which makes the static dashboard, interactive.

    # Build Players dashboard.
    player_experience_data = []
    for player_experience in player_experience_infos:
        exp_sum = sum([skill["quantity"] for skill in player_experience["experience_stacks"]])
        exp_list = [skill["quantity"] for skill in sorted(player_experience["experience_stacks"], key=lambda d: d["skill_id"])][1:]
        if player_experience["username"] == "Cat":
            continue #player_experience["username"] = player_experience["username"] + " [Admin]"
        player_experience_data.append([player_experience["username"], exp_sum] + exp_list)
    skill_names = [skill["name"] for skill in sorted(metadata_dicts["SkillDesc"], key=lambda d: d["id"])][1:]
    players_df = pd.DataFrame(player_experience_data, columns=["Username", "Experience"] + skill_names)
    players_df.sort_values(by="Experience", ascending=False, inplace=True)
    players_df["Rank"] = players_df["Experience"].rank(method="min", ascending=False).astype(int)
    players_df = players_df[["Rank", "Username", "Experience"] + skill_names]
    players = pn.widgets.Tabulator(players_df, css_classes=["players-tabulator"], disabled=True, show_index=False, text_align="left", sorters=[{"field": "Rank", "dir": "asc"}], sortable={"Rank": False}, sizing_mode="stretch_width", frozen_columns=["Rank"])
    players.jslink(
        target=players,
        code={"sorters": """
            if (source.sorters[0]["field"] === "Rank") {
                return;
            }
            let sorted_column = [...source.source.data[source.sorters[0]["field"]]];
            
            let indices_map = [];
            for (let i = 0; i < sorted_column.length; i++) {
                indices_map.push([i, sorted_column[i]]);
            }
            if (source.sorters[0]["dir"] === "asc") {
                indices_map.sort((a, b) => a[1] - b[1]);
            } else {
                indices_map.sort((a, b) => b[1] - a[1]);
            }
            
            let last_score = -1;
            let rank = 0;
            let ranking_map = [];
            for (const [index, score] of indices_map) {
                if (last_score != score) {
                    rank++;
                    last_score = score;
                }
                ranking_map.push([index, rank])
            }

            source.source.patch(new Map([["Rank", ranking_map]]));
        """}
    )
    player_search = pn.widgets.TextInput(placeholder="Search for a player here...", sizing_mode="stretch_width")
    player_search.jslink(target=players, code={"value_input": """
        const tabulator = getTabulatorByClass("players-tabulator");
        tabulator.setFilter("Username", "like", source.value_input);
    """})
    players_column = pn.Column(player_search, players, margin=(5, 0, 0, 0))
    
    # Build Empires dashboard.
    guild_data = []
    for guild_info in guild_infos:
        if guild_info["owner_player_entity_id"] == 0:
            continue
        guild_name = guild_info["name"]
        guild_tier = str(([100] + [tech for tech in guild_info["learned"] if tech in [200, 300, 400, 500, 600, 700, 800, 900, 1000]])[-1]//100)
        guild_members = len(guild_info["members"])
        guild_size = guild_info["num_tiles"]
        guild_location = "(" + str(round(guild_info["location"]["some"]["z"]/3)) + ", " + str(round(guild_info["location"]["some"]["x"]/3)) + ")"
        guild_wealth = guild_info["treasury"]
        guild_supplies = guild_info["supplies"]
        guild_data.append([guild_name, guild_tier, guild_supplies, guild_members, guild_size, guild_wealth, guild_location])
    guilds_df = pd.DataFrame(guild_data, columns=["Name", "Tier", "Supplies", "Members", "Size", "Wealth", "Location"])
    guilds = pn.widgets.Tabulator(guilds_df, css_classes=["guilds-tabulator"], sizing_mode="stretch_width", disabled=True, show_index=False, text_align="left", sorters=[{"field": "Tier", "dir": "desc"}, {"field": "Supplies", "dir": "desc"}])
    guild_search = pn.widgets.TextInput(placeholder="Search for an empire here...", sizing_mode="stretch_width")
    guild_search.jslink(target=guilds, code={"value_input": """
        const tabulator = getTabulatorByClass("guilds-tabulator");
        tabulator.setFilter("Name", "like", source.value_input);
    """})
    guilds_column = pn.Column(guild_search, guilds, margin=(5, 0, 0, 0))
    
    # Build Trades dashboard.
    def items_formatter(items):
        result = ""
        for item in items:
            item_name = [e["name"] for e in metadata_dicts["ItemDesc"] if e["id"] == item["item_id"]][0]
            result += item_name + " (" + str(item["quantity"]) + ")\n"
        return result
    
    def cargo_formatter(item_ids):
        result = ""
        for item_id in item_ids:
            item_name = [e["name"] for e in metadata_dicts["CargoDesc"] if e["id"] == item_id][0]
            result += item_name + "\n"
        return result
    
    trade_data = []
    for trade_info in trade_deployable_infos:
        if "none" in trade_info["location"]:
            continue
        trade_seller = entity_username_map[trade_info["owner_id"]] if trade_info["owner_id"] in entity_username_map else "SYSTEM"
        trade_shop_name = trade_info["nickname"]
        trade_give = items_formatter(trade_info["required_items"]) if len(trade_info["required_items"]) != 0 else cargo_formatter(trade_info["required_cargo_id"])
        trade_receive = items_formatter(trade_info["offer_items"]) if len(trade_info["offer_items"]) != 0 else cargo_formatter(trade_info["offer_cargo_id"])
        trade_stock = trade_info["remaining_stock"]
        trade_location = "(" + str(round(trade_info["location"]["some"]["z"]/3)) + ", " + str(round(trade_info["location"]["some"]["x"]/3)) + ")"
        trade_data.append([trade_shop_name, trade_seller, trade_give, trade_receive, trade_stock, trade_location])
    for trade_info in trade_building_infos:
        trade_seller = entity_guild_map[trade_info["claim_entity_id"]] if trade_info["claim_entity_id"] in entity_guild_map else str(trade_info["claim_entity_id"])
        trade_shop_name = trade_info["nickname"] if trade_info["nickname"] != "" else entity_buildingdesc_map[trade_info["building_description_id"]]
        trade_give = items_formatter(trade_info["required_items"]) if len(trade_info["required_items"]) != 0 else cargo_formatter(trade_info["required_cargo_id"])
        trade_receive = items_formatter(trade_info["offer_items"]) if len(trade_info["offer_items"]) != 0 else cargo_formatter(trade_info["offer_cargo_id"])
        trade_stock = trade_info["remaining_stock"]
        trade_location = "(" + str(round(trade_info["z"]/3)) + ", " + str(round(trade_info["x"]/3)) + ")"
        trade_data.append([trade_shop_name, trade_seller, trade_give, trade_receive, trade_stock, trade_location])
    trades_df = pd.DataFrame(trade_data, columns=["Shop Name", "Seller", "Give", "Receive", "Stock", "Location"])
    trades = pn.widgets.Tabulator(trades_df, css_classes=["trades-tabulator"], disabled=True, show_index=False, text_align="left", sorters=[{"field": "Stock", "dir": "desc"}], sizing_mode="stretch_width", formatters={"Required Items": {"type": "textarea"}})
    trade_search = pn.widgets.TextInput(placeholder="Search for a trade here...", sizing_mode="stretch_width")
    trade_search.jslink(target=trades, code={"value_input": """
        const tabulator = getTabulatorByClass("trades-tabulator");
        
        if (source.value_input) {
            tabulator.setFilter(globalFilter, source.value_input);
        } else {
            tabulator.clearFilter();
        }
    """})
    notice_mkdn = pn.pane.Markdown("# Notice: Trade functionality has been frozen for being too powerful")
    trades_column = pn.Column(notice_mkdn, trade_search, trades, margin=(5, 0, 0, 0))
    
    # Build Map dashboard.
    map_iframe_url = "https://bitcraft-map.littledaimon.net/"
    map_iframe = f'<iframe src="{map_iframe_url}" width="100%" height="100%"></iframe>'
    map_pane = pn.pane.HTML(map_iframe, sizing_mode="stretch_both")
    map_credit = pn.pane.HTML('<p style="position: absolute; bottom: 0; left: 10px; text-align: center; font-size: 20px">Map created by <a style="color: black;" href="https://bitcraft-map.littledaimon.net/">LittleDaimon</a></p>', sizing_mode="stretch_width")
    map_column = pn.Column(map_pane, map_credit, margin=(5, 0, 0, 0))
    
    # Build Metadata dashboard.
    metadata_map = {}
    metadata_models = {}
    for metadata in metadata_list:
        metadata_infos = metadata_dicts[metadata["table"]]
        metadata_data = [data.values() for data in metadata_infos]
        metadata_df = pd.DataFrame(metadata_data, columns=metadata_infos[0].keys())
        
        metadata_table = pn.widgets.Tabulator(metadata_df, css_classes=[metadata["table"] + "-tabulator"], disabled=True, show_index=False, text_align="left", sorters=[{"field": metadata["sorted_column"], "dir": "asc"}], formatters={col: {"type": "json", "multiline": False} for col in metadata_df.columns})
        metadata_search = pn.widgets.TextInput(placeholder="Search through the table here...", sizing_mode="stretch_width")
        metadata_search.jslink(target=metadata_table, code={"value_input": """
            const tabulator = getTabulatorByClass(\"""" + metadata["table"] + """-tabulator");
            
            if (source.value_input) {
                tabulator.setFilter(globalFilter, source.value_input);
            } else {
                tabulator.clearFilter();
            }
        """})
        
        metadata_column = pn.Column(metadata_search, metadata_table)
        metadata_map[metadata["name"]] = metadata["table"]
        metadata_models[metadata["table"]] = metadata_column.get_root()
    metadata_select = pn.widgets.Select(name="", value="null", options={"Select some metadata...": "null", **metadata_map}, sizing_mode="stretch_width")
    metadata_column = pn.Column(metadata_select, margin=(5, 0, 0, 0))
    metadata_select.jslink(target=metadata_column, args=metadata_models, code={"value": """
        let children = [...target.children];
        if (source.value === "null") {
            children.pop();
        } else {
            children[1] = eval(source.value);
        }
        target.children = children;
    """})
    
    # Assign all dashboards to their corresponding tabs.
    tabs = pn.Tabs(("Players", players_column),
                   ("Empires", guilds_column),
                   ("Trades", trades_column),
                   ("Map", map_column),
                   ("Metadata", metadata_column), margin=5)

    # Save the BitCraft Dashboard website to a single static HTML file.
    if len(sys.argv) > 1:
        tabs.save("nginx/html/bitcraft.nul.dev/index.html", title="BitCraft Dashboards", favicon="favicon.ico")
    else:
        tabs.save("index.html", title="BitCraft Dashboards", favicon="favicon.ico")
