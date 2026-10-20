"""SQLite 初始化与连接管理。"""
import sqlite3
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS period (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    tips        TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS knife_type (
    id          TEXT,
    period_id   TEXT,
    zone        TEXT,
    description TEXT,
    video_url   TEXT,
    video_source TEXT,
    axis_image  TEXT,
    PRIMARY KEY (period_id, id)
);

CREATE TABLE IF NOT EXISTS paidao_user (
    period_id TEXT,
    rank      INTEGER,
    name      TEXT,
    level     INTEGER,
    bold      INTEGER DEFAULT 0,
    PRIMARY KEY (period_id, rank)
);

CREATE TABLE IF NOT EXISTS user_knife (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id                TEXT,
    user_rank                INTEGER,
    slot                     INTEGER,
    knife_type_id_first      TEXT,
    knife_type_id_last       TEXT,
    knife_type_id_first_done INTEGER DEFAULT 0,
    knife_type_id_last_done  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS axis (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id   TEXT,
    boss        TEXT,
    image_path  TEXT,
    damage      REAL,
    summary     TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS comment (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    axis_id     INTEGER,
    content     TEXT,
    image_path  TEXT,
    uploader    TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS comment_like (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id  INTEGER,
    voter       TEXT
);

CREATE INDEX IF NOT EXISTS idx_axis_period ON axis(period_id);
CREATE INDEX IF NOT EXISTS idx_comment_axis ON comment(axis_id);
CREATE INDEX IF NOT EXISTS idx_like_comment ON comment_like(comment_id, voter);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# 列改名迁移：旧库 user_knife.knife_type_id/position → knife_type_id_first/knife_type_id_last
RENAMES = [
    ("user_knife", "knife_type_id", "knife_type_id_first"),
    ("user_knife", "position", "knife_type_id_last"),
]

# 补列迁移：(表, 列名, 定义)
ADD_COLUMNS = [
    ("user_knife", "knife_type_id_first_done", "INTEGER DEFAULT 0"),
    ("user_knife", "knife_type_id_last_done", "INTEGER DEFAULT 0"),
    ("knife_type", "borrow", "TEXT"),
]


def _table_columns(conn, table):
    return [r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)]


def migrate(conn):
    """幂等迁移：先按 RENAMES 改名，再按 ADD_COLUMNS 补列。"""
    for table, old, new in RENAMES:
        cols = _table_columns(conn, table)
        if old in cols and new not in cols:
            conn.execute("ALTER TABLE %s RENAME COLUMN %s TO %s" % (table, old, new))
    for table, col, decl in ADD_COLUMNS:
        cols = _table_columns(conn, table)
        if col not in cols:
            conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, decl))


def init_db():
    import os
    os.makedirs(os.path.dirname(current_app.config["DATABASE"]), exist_ok=True)
    db = sqlite3.connect(current_app.config["DATABASE"])
    db.executescript(SCHEMA)
    migrate(db)
    db.commit()
    db.close()
