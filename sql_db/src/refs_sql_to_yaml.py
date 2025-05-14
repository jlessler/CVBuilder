import yaml
import sqlite3

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

    # Write to YAML file
    with open(output_file, "w") as file:
        yaml.dump(yaml_data, file, default_flow_style=False, sort_keys=False)

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