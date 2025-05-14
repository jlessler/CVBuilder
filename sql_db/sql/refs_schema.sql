
-- SQL definition created using ChatGPT

CREATE TABLE metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT
);

CREATE TABLE refs (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL
);

CREATE TABLE authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    FOREIGN KEY (ref_id) REFERENCES refs(ref_id)
);

CREATE TABLE ref_dat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id INTEGER NOT NULL,
    key INTEGER NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (ref_id) REFERENCES refs(ref_id)
);