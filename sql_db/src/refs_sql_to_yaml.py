import yaml
import sqlite3

# Custom YAML Dumper to handle block scalar style for specific keys
class CustomDumper(yaml.Dumper):
    def represent_scalar(self, tag, value, style=None):
        # Apply folded scalar style (>-)
        if tag == 'tag:yaml.org,2002:str' and isinstance(value, str):
            if hasattr(self, 'current_key') and self.current_key == "authors":
                if self.current_key != value and len(value) > 50:
                    style = '>'  # Force plain scalar style (no wrapping)
            if hasattr(self, 'current_key') and self.current_key in ["title", "conference","journal"]:  # Specific keys
                if self.current_key != value:
                    style = '>'

        return super().represent_scalar(tag, value, style)
    
    def represent_sequence(self, tag, sequence, flow_style=None):
        # Ensure lists like 'authors' are always represented inline
        if hasattr(self, 'current_key') and self.current_key == "authors":
            flow_style = False  # Force inline style for authors
        return super().represent_sequence(tag, sequence, flow_style)

    def represent_mapping(self, tag, mapping, flow_style=None):
        # Create a MappingNode and explicitly pass the key to represent_scalar
        node = yaml.MappingNode(tag, [])
        for key, value in mapping.items():
            self.current_key = key  # Set the current key
            key_node = self.represent_data(key)
            value_node = self.represent_data(value)
            node.value.append((key_node, value_node))
        self.current_key = None  # Reset current_key after processing
        node.flow_style = flow_style
        return node

# Remove non-ASCII characters, newline characters, and trailing spaces from data
def remove_non_ascii(data):
    if isinstance(data, str):
        # Remove non-ASCII characters, newline characters, and strip trailing spaces
        return ''.join(char for char in data if ord(char) < 128).replace('\n', ' ').strip()
    elif isinstance(data, list):
        # Recursively process lists
        return [remove_non_ascii(item) for item in data]
    elif isinstance(data, dict):
        # Recursively process dictionaries
        return {remove_non_ascii(key): remove_non_ascii(value) for key, value in data.items()}
    return data  # Return other data types as-is

# Fetch data from the database
def fetch_data(cursor):
    # Fetch metadata
    cursor.execute("SELECT key, value FROM metadata")
    metadata = {row[0]: row[1] for row in cursor.fetchall()}

    # Fetch refs
    cursor.execute("SELECT ref_id, type FROM refs")
    refs = {}
    for ref_id, ref_type in cursor.fetchall():
        if ref_type not in refs:
            refs[ref_type] = []
        refs[ref_type].append({"ref_id": ref_id})

    # Fetch authors and ref details
    for ref_type, ref_list in refs.items():
        for ref in ref_list:
            ref_id = ref["ref_id"]
            del ref["ref_id"]  # Remove ref_id from the dictionary

            # Fetch authors
            cursor.execute("SELECT author_name FROM authors WHERE ref_id = ?", (ref_id,))
            ref["authors"] = [row[0] for row in cursor.fetchall()]

            # Fetch other details
            cursor.execute("SELECT key, value FROM ref_dat WHERE ref_id = ?", (ref_id,))
            for key, value in cursor.fetchall():
                # Handle the 'corr' key
                if key == "corr":
                    if value.lower() in ["1", "yes", "true"]:  # Keep only if value is 1, yes, or true
                        ref[key] = True
                    else:
                        continue  # Skip adding the 'corr' key
                else:
                    ref[key] = value

    return metadata, refs

# Export data to YAML
def export_to_yaml(db_file, output_file):
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Fetch data
    metadata, refs = fetch_data(cursor)

    # Structure the data for YAML
    yaml_data = metadata
    for ref_type, ref_list in refs.items():
        yaml_data[ref_type] = ref_list

    # Remove non-ASCII characters from the data
    yaml_data = remove_non_ascii(yaml_data)

    # Write to YAML file with custom dumper
    with open(output_file, "w") as file:
        yaml.dump(yaml_data, file, Dumper=CustomDumper, default_flow_style=False, sort_keys=False)

    print(f"Data exported to {output_file}")

    # Close the connection
    conn.close()

# Main function
def main():
    db_file = "./mydata/refs.db"
    output_yaml_file = "./mydata/exported_refs.yml"

    export_to_yaml(db_file, output_yaml_file)

if __name__ == "__main__":
    main()