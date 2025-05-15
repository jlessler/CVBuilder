from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from crossref.restful import Works

app = Flask(__name__, template_folder="../templates")
DB_FILE = "./mydata/refs.db"

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Home route to display all references
@app.route("/")
def index():
    conn = get_db_connection()
    refs = conn.execute("""
        SELECT refs.ref_id, refs.type,
               (SELECT GROUP_CONCAT(author_name, ', ') 
                FROM authors 
                WHERE authors.ref_id = refs.ref_id) AS authors,
               MAX(CASE WHEN ref_dat.key = 'title' THEN ref_dat.value END) AS title,
               MAX(CASE WHEN ref_dat.key = 'journal' THEN ref_dat.value END) AS journal,
               MAX(CASE WHEN ref_dat.key = 'year' THEN ref_dat.value END) AS year,
               MAX(CASE WHEN ref_dat.key = 'doi' THEN ref_dat.value END) AS doi
        FROM refs
        LEFT JOIN ref_dat ON refs.ref_id = ref_dat.ref_id
        GROUP BY refs.ref_id
    """).fetchall()
    conn.close()
    return render_template("index.html", refs=refs)

# Route to view details of a specific reference
@app.route("/ref/<int:ref_id>")
def view_ref(ref_id):
    conn = get_db_connection()
    ref = conn.execute("SELECT * FROM refs WHERE ref_id = ?", (ref_id,)).fetchone()
    authors = conn.execute("SELECT author_name FROM authors WHERE ref_id = ?", (ref_id,)).fetchall()
    ref_data = conn.execute("SELECT key, value FROM ref_dat WHERE ref_id = ?", (ref_id,)).fetchall()
    conn.close()
    return render_template("view_ref.html", ref=ref, authors=authors, ref_data=ref_data)

# Route to add a new reference
@app.route("/add/<ref_type>", methods=["GET", "POST"])
def add_ref(ref_type):
    if request.method == "POST":
        authors = request.form.get("authors", "").split(",")
        corr = request.form.get("corr", "no")  # Default to "no" if not checked
        cofirsts = request.form.get("cofirsts", "0")  # Default to 0 if not provided
        coseniors = request.form.get("coseniors", "0")  # Default to 0 if not provided
        ref_data = {key: value for key, value in request.form.items() if key not in ["authors", "cofirsts", "coseniors", "corr", "submit"]}

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into refs table
        cursor.execute("INSERT INTO refs (type) VALUES (?)", (ref_type,))
        ref_id = cursor.lastrowid

        # Insert authors
        for author in authors:
            if author.strip():
                cursor.execute("INSERT INTO authors (ref_id, author_name) VALUES (?, ?)", (ref_id, author.strip()))

        # Insert cofirsts and coseniors as numeric values
        cursor.execute("INSERT INTO ref_dat (ref_id, key, value) VALUES (?, ?, ?)", (ref_id, "cofirsts", cofirsts))
        cursor.execute("INSERT INTO ref_dat (ref_id, key, value) VALUES (?, ?, ?)", (ref_id, "coseniors", coseniors))

        # Insert corresponding author flag
        cursor.execute("INSERT INTO ref_dat (ref_id, key, value) VALUES (?, ?, ?)", (ref_id, "corr", corr))

        # Insert other reference details
        for key, value in ref_data.items():
            if value.strip():
                cursor.execute("INSERT INTO ref_dat (ref_id, key, value) VALUES (?, ?, ?)", (ref_id, key.strip(), value.strip()))

        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    return render_template("add_ref.html", ref_type=ref_type)

# Route to delete a reference
@app.route("/delete/<int:ref_id>", methods=["POST"])
def delete_ref(ref_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM refs WHERE ref_id = ?", (ref_id,))
    conn.execute("DELETE FROM authors WHERE ref_id = ?", (ref_id,))
    conn.execute("DELETE FROM ref_dat WHERE ref_id = ?", (ref_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# Route to fetch DOI details
@app.route("/fetch_doi", methods=["POST"])
def fetch_doi():
    doi = request.json.get("doi")
    if not doi:
        return jsonify({"error": "DOI is required"}), 400

    works = Works()
    try:
        ref = works.doi(doi)
        if not ref:
            return jsonify({"error": "DOI not found"}), 404

        # Helper function to safely extract values
        def safe_get(data, key, default=""):
            if isinstance(data, dict):
                value = data.get(key, default)
                if isinstance(value, list):
                    return value[0] if value else default
                return value
            return default

        # Helper function to safely extract nested lists
        def safe_get_nested_list(data, keys, default=None):
            try:
                for key in keys:
                    data = data[key]
                return data[0][0] if data and isinstance(data[0], list) else default
            except (KeyError, IndexError, TypeError):
                return default

        # Extract relevant fields
        data = {
            "title": safe_get(ref, "title", ""),
            "year": (
                safe_get_nested_list(ref, ["published-print", "date-parts"], None)
                or safe_get_nested_list(ref, ["published-online", "date-parts"], None)
            ),
            "journal": safe_get(ref, "container-title", ""),
            "volume": safe_get(ref, "volume", ""),
            "issue": safe_get(ref, "issue", ""),
            "pages": safe_get(ref, "page", ""),
            "authors": ", ".join(
                [f"{author.get('family', '')} {author.get('given', '')}" for author in ref.get("author", [])]
            ),
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)