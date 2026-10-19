"""种子导入：解析参考项目 202609.js，写入 period/knife_type/paidao_user/user_knife。

幂等：若目标期数已存在则跳过，可安全重复执行。
"""
import json
import os
import sqlite3

from config import SEED_FILE, DEFAULT_PERIOD, EXTRA_PERIODS

PERIOD_NAME = "S79天秤座202609喵园首日排刀表"


def parse_seed_file(path):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    start = src.index("{")
    end = src.rstrip().rstrip(";").rfind("}") + 1
    return json.loads(src[start:end])


def seed_period(conn, period_id=DEFAULT_PERIOD, name=PERIOD_NAME):
    data = parse_seed_file(SEED_FILE)
    tips = data.get("tips", "")
    cur = conn.cursor()
    cur.execute(
        'INSERT OR IGNORE INTO period(id,name,tips,created_at) VALUES(?,?,?,datetime("now"))',
        (period_id, name, tips),
    )
    for k in data.get("knife_types", []):
        cur.execute(
            "INSERT OR IGNORE INTO knife_type(id,period_id,zone,description,video_url,video_source,axis_image) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                k["id"],
                period_id,
                k.get("zone"),
                k.get("description", ""),
                k.get("video_url", ""),
                k.get("video_source", ""),
                k.get("axis_image", ""),
            ),
        )
    for u in data.get("users", []):
        cur.execute(
            "INSERT OR IGNORE INTO paidao_user(period_id,rank,name,level,bold) VALUES(?,?,?,?,?)",
            (
                period_id,
                u["rank"],
                u["name"],
                u.get("level"),
                1 if u.get("bold") else 0,
            ),
        )
        for i, knife in enumerate(u.get("knives", []), start=1):
            kid = knife[0] if len(knife) > 0 else None
            pos = knife[1] if len(knife) > 1 else None
            cur.execute(
                "INSERT INTO user_knife(period_id,user_rank,slot,knife_type_id_first,knife_type_id_last) "
                "VALUES(?,?,?,?,?)",
                (period_id, u["rank"], i, kid, pos),
            )
    conn.commit()


def ensure_periods(conn):
    """登记 EXTRA_PERIODS 中的期数（幂等）。只建期数档案，不导入排刀/刀型数据。"""
    cur = conn.cursor()
    for pid, pname in EXTRA_PERIODS:
        cur.execute(
            'INSERT INTO period(id,name,tips,created_at) VALUES(?,?,?,datetime("now")) '
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name",
            (pid, pname, ""),
        )
    conn.commit()


def seed_if_empty(conn):
    row = conn.execute("SELECT 1 FROM period WHERE id=?", (DEFAULT_PERIOD,)).fetchone()
    if row:
        return False
    seed_period(conn)
    return True


if __name__ == "__main__":
    import db
    import config

    db.init_db()
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    seeded = seed_if_empty(conn)
    conn.close()
    print("已导入 202609 排刀数据" if seeded else "期数已存在，跳过导入")
