import sqlite3
from flask import g
from . import config

def get_db_connection():
    if "db" not in g:
        g.db = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
        g.db.execute("PRAGMA journal_mode = WAL;")
        g.db.execute("PRAGMA synchronous = NORMAL;")
    return g.db

def close_connection(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS canciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            letra TEXT NOT NULL,
            ruta_foto TEXT,
            url_web_foto TEXT
        );
        """
    )
    conn.commit()