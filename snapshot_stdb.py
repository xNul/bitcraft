##########################################
# Snapshot BitCraft SpacetimeDB instance #
##########################################

import os
import time

from bitcraft import *

# Extract list of all STDB tables from Unity assets.
spacetime_csharp_path = "BitCraft.Spacetime"
csharp_files = os.listdir(spacetime_csharp_path)

table_list = []
for csharp_file in csharp_files:
    with open(spacetime_csharp_path + "/" + csharp_file) as f:
        if "DatabaseTableWithPrimaryKey" in f.read():
            file_name = os.path.basename(csharp_file)
            table_name = os.path.splitext(file_name)[0]
            table_list.append(table_name)

# Copy all STDB tables and save them in a JSON format.
spacetime_csharp_path_json = spacetime_csharp_path + "_json"
if not os.path.exists(spacetime_csharp_path_json):
    os.mkdir(spacetime_csharp_path_json)

desc_list = []
for table in table_list:
    print("Obtaining '" + table + "'...")
    output_path = spacetime_csharp_path_json + "/" + table + ".json"
    #if os.path.exists(output_path):
    #    continue
    table_info = sql_to_dict("select * from " + table, json_output=output_path)
    if table_info and len(table_info) != 0:
        print(table + " query succeeded")
        if table.endswith("Desc"):
            first_column = list(table_info[0].keys())[0]
            desc_list.append({
                "name": table[:-4] + "s",
                "table": table,
                "sorted_column": first_column
            })
    else:
        print(table + " query failed")
    time.sleep(5)

with open(spacetime_csharp_path_json + "/.DescList.json", "w") as f:
    f.write(json.dumps(desc_list, indent=4))