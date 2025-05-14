import yaml
import sqlite3

# Converts YAML data to SQL Lite DB

# Load YAML file
def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Insert metadata
def insert_metadata(cursor, metadata):
    for key, value in metadata.items():
        cursor.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", (key, value))

# Insert refs and authors
def insert_refs(cursor, refs, reftype):
    for ref in refs:
        # print(reftype) ## DEBUG
        cursor.execute("INSERT INTO refs (type) VALUES (?)", (reftype,))
        ref_id = cursor.lastrowid
        #print(ref_id) ##DEBUG

        # Insert authors
        for author in ref.get("authors", []):
            cursor.execute("INSERT INTO authors (ref_id, author_name) VALUES (?, ?)", (ref_id, author))

        # Insert other ref details
        for key, value in ref.items():
            #print(key) ## DEBUG
            #print(value) ## DEBUG
            if key != "authors":
                cursor.execute("INSERT INTO ref_dat (ref_id, key, value) VALUES (?, ?, ?)", (ref_id, key, value))

# Main function
def main():
    yaml_file = "./mydata/refs.yml"
    db_file = "./mydata/refs.db"

    # Load YAML data
    data = load_yaml(yaml_file)

    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("DROP TABLE IF EXISTS metadata")
    cursor.execute("DROP TABLE IF EXISTS refs")
    cursor.execute("DROP TABLE IF EXISTS authors")
    cursor.execute("DROP TABLE IF EXISTS ref_dat")
    cursor.executescript(open("./sql_db/sql/refs_schema.sql").read())

    # Insert data
    insert_metadata(cursor, {"myname": data.get("myname", "")})
    insert_refs(cursor, data.get("papers", []), "papers")
    insert_refs(cursor, data.get("preprints", []), "preprints")
    insert_refs(cursor, data.get("papersNoPeer", []), "papersNoPeer")
    insert_refs(cursor, data.get("chapters", []), "chapters")
    insert_refs(cursor, data.get("letters", []), "letters")
    insert_refs(cursor, data.get("scimeetings",[]),"scimeetings")

    # Commit and close
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()