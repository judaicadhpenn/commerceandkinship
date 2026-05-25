import json
import os
import glob
from gedcom.parser import Parser
from gedcom.element.individual import IndividualElement
from gedcom.element.family import FamilyElement

def gedcom_to_graph(gedcom_file_path, master_json_path):
    # 1. Parse the incoming GEDCOM file
    gedcom_parser = Parser()
    gedcom_parser.parse_file(gedcom_file_path)

    new_nodes = []
    new_edges = []
    edge_counter = int(os.getpid()) # Unique baseline for temporary IDs

    root_child_elements = gedcom_parser.get_root_child_elements()

    # Pass 1: Extract Individuals
    for element in root_child_elements:
        if isinstance(element, IndividualElement):
            raw_id = element.get_pointer().replace('@', '')
            node_id = f"p_{raw_id.lower()}"

            (first, last) = element.get_name()
            full_name = f"{first} {last}".strip()

            birth_year = element.get_birth_year()
            summary = f"Born: {birth_year}" if birth_year != -1 else "Birth year unknown"

            new_nodes.append({
                "id": node_id,
                "type": "PERSON",
                "label": full_name,
                "summary": summary,
                "confidence": "CONFIRMED"
            })

    # Pass 2: Extract Families
    for element in root_child_elements:
        if isinstance(element, FamilyElement):
            husbands = element.get_husbands()
            wives = element.get_wives()
            children = element.get_children()

            # Partner Edges
            for h in husbands:
                h_id = f"p_{h.get_pointer().replace('@', '').lower()}"
                for w in wives:
                    w_id = f"p_{w.get_pointer().replace('@', '').lower()}"
                    new_edges.append({
                        "id": f"e_ged_{edge_counter}",
                        "type": "PARTNERED_WITH",
                        "from": h_id,
                        "to": w_id,
                        "confidence": "CONFIRMED"
                    })
                    edge_counter += 1

            # Parent Edges
            parents = husbands + wives
            for p in parents:
                p_id = f"p_{p.get_pointer().replace('@', '').lower()}"
                for c in children:
                    c_id = f"p_{c.get_pointer().replace('@', '').lower()}"
                    new_edges.append({
                        "id": f"e_ged_{edge_counter}",
                        "type": "PARENT_OF",
                        "from": p_id,
                        "to": c_id,
                        "confidence": "CONFIRMED"
                    })
                    edge_counter += 1

    # 2. Load existing master graph if it exists, otherwise initialize an empty one
    if os.path.exists(master_json_path) and os.path.getsize(master_json_path) > 0:
        try:
            with open(master_json_path, 'r', encoding='utf-8') as f:
                master_data = json.load(f)
        except json.JSONDecodeError:
            master_data = {"nodes": [], "edges": []}
    else:
        master_data = {"nodes": [], "edges": []}

    # 3. Smart Merge: Avoid duplicating existing node IDs
    existing_node_ids = {node['id'] for node in master_data.get('nodes', [])}
    added_nodes_count = 0

    for node in new_nodes:
        if node['id'] not in existing_node_ids:
            master_data['nodes'].append(node)
            added_nodes_count += 1

    # Smart Merge: Avoid duplicating existing edge pairs
    existing_edge_pairs = {(edge['from'], edge['to'], edge['type']) for edge in master_data.get('edges', [])}
    added_edges_count = 0

    for edge in new_edges:
        edge_pair = (edge['from'], edge['to'], edge['type'])
        if edge_pair not in existing_edge_pairs:
            master_data['edges'].append(edge)
            added_edges_count += 1

    # 4. Save everything back to the master graph file
    with open(master_json_path, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2)

    print(f"Automated processing of {os.path.basename(gedcom_file_path)} complete.")
    print(f"Merged {added_nodes_count} new individuals and {added_edges_count} new family ties into the master graph.")


if __name__ == "__main__":
    # Point directly to your src/data folder where Astro reads your master file
    master_file = 'src/data/kinship-commerce-graph.json'

    # Check for any incoming GEDCOM files in your raw repository upload folder
    ged_files = glob.glob('raw_data/*.ged')

    if ged_files:
        # Guarantee the destination folder directory structure exists
        os.makedirs(os.path.dirname(master_file), exist_ok=True)
        for ged_file in ged_files:
            gedcom_to_graph(ged_file, master_file)
    else:
        print("No new GEDCOM files detected in raw_data/. Skipping genealogical merge.")