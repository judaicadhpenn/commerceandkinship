import json

def convert_to_jsonld(input_file, output_file):
    # Load your exported application JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # The JSON-LD Context maps your keys to global namespaces
    context = {
        "schema": "http://schema.org/",
        "crm": "http://www.cidoc-crm.org/cidoc-crm/",
        "prov": "http://www.w3.org/ns/prov#",
        "id": "@id",
        "type": "@type"
    }

    entities = {}
    edges_by_id = {e['id']: e for e in data.get('edges', [])}

    # Establish a base URI for your archival project to ensure stable identifiers
    base_uri = "https://yourarchive.edu/graph/entity/"

    # ==========================================
    # PASS 1: Map Nodes to Semantic Entities
    # ==========================================
    for node in data.get('nodes', []):
        nid = node['id']
        uri = f"{base_uri}{nid}"

        entity = {
            "id": uri,
            "schema:name": node.get('label'),
            "schema:description": node.get('summary'),
            # PROV-O can capture your confidence ratings
            "prov:value": node.get('confidence')
        }

        # Type-specific ontology mapping
        if node['type'] == 'PERSON':
            entity['type'] = "schema:Person"

        elif node['type'] == 'BUSINESS':
            entity['type'] = "schema:Organization"
            props = node.get('properties', {})
            if props.get('kind'):
                entity['schema:additionalType'] = props.get('kind')

        elif node['type'] == 'ARTIFACT':
            entity['type'] = "crm:E22_Human-Made_Object"
            props = node.get('properties', {})
            if props.get('artifactKind'):
                entity['crm:P2_has_type'] = props.get('artifactKind')
            if props.get('transcript'):
                entity['crm:P190_has_symbolic_content'] = props.get('transcript')

        entities[nid] = entity

    # ==========================================
    # PASS 2: Map Edges to Entity Properties
    # ==========================================
    for edge in data.get('edges', []):
        from_id = edge['from']
        to_id = edge['to']
        etype = edge['type']

        if from_id not in entities:
            continue

        subject = entities[from_id]

        # Handle Edge-to-Edge Links (e.g., an Artifact evidencing a Relationship)
        if to_id in edges_by_id:
            target_edge = edges_by_id[to_id]
            # Standard RDF requires "reification" to point at a relationship.
            # For this baseline, we link the artifact to the subject of that relationship.
            target_node_id = target_edge['from']
            object_uri = {"id": f"{base_uri}{target_node_id}"}
        else:
            object_uri = {"id": f"{base_uri}{to_id}"}

        # Map custom edge types to semantic predicates
        predicate = None
        if etype == 'PARENT_OF':
            predicate = 'schema:children'
        elif etype == 'PARTNERED_WITH':
            predicate = 'schema:spouse'
        elif etype == 'OWNS':
            predicate = 'schema:owns'
        elif etype == 'EMPLOYS':
            predicate = 'schema:employee'
        elif etype == 'MEMBER_OF':
            predicate = 'schema:memberOf'
        elif etype == 'TRADES_WITH':
            predicate = 'schema:knows'
        elif etype == 'DEPICTS':
            predicate = 'crm:P62_depicts'
        elif etype == 'EVIDENCES':
            predicate = 'crm:P70_documents'

        # Inject the property into the subject entity
        if predicate:
            if predicate in subject:
                # If the property already exists, convert to a list
                if isinstance(subject[predicate], list):
                    subject[predicate].append(object_uri)
                else:
                    subject[predicate] = [subject[predicate], object_uri]
            else:
                subject[predicate] = object_uri

    # ==========================================
    # OUTPUT: Wrap in JSON-LD @graph array
    # ==========================================
    json_ld = {
        "@context": context,
        "@graph": list(entities.values())
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_ld, f, indent=2)

    print(f"Successfully converted {len(entities)} nodes to JSON-LD. Saved to {output_file}")

if __name__ == "__main__":
    import os
    # Read from raw_data, write to public
    if os.path.exists('raw_data/kinship-commerce-graph.json'):
        convert_to_jsonld('raw_data/kinship-commerce-graph.json', 'public/graph_linked_data.jsonld')
    else:
        print("No master graph JSON found to convert.")