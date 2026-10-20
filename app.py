"""喵园指挥台：Flask 后端。

模块结构：
  config.py   路径与限制
  db.py       SQLite 表结构与连接
  security.py 图片上传校验
  seed.py     202609 排刀数据导入
"""
import os
import sqlite3
import uuid
from datetime import datetime

from flask import (
    Flask,
    abort,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

import config
import db
import seed
from security import is_safe_stored_filename, save_image, thumb_name

app = Flask(__name__)
app.config["DATABASE"] = config.DATABASE
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
# 静态文件（css/js）不缓存：小内网应用，改动即时生效；304 协商代价可忽略
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
# 模板改动后自动重载（debug=False 时 Flask 默认缓存模板，改模板不重启不生效）
app.config["TEMPLATES_AUTO_RELOAD"] = True

VALID_BOSSES = ["D1", "D2", "D3", "D4", "D5"]


# --------------------------------------------------------------------------- #
# 启动钩子：建表 + 自动种子导入
# --------------------------------------------------------------------------- #
with app.app_context():
    db.init_db()
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    seed.seed_if_empty(conn)
    seed.ensure_periods(conn)
    conn.close()


app.teardown_appcontext(db.close_db)


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
def get_period():
    p = request.args.get("period")
    if p:
        return p
    row = db.get_db().execute("SELECT id FROM period ORDER BY id DESC LIMIT 1").fetchone()
    return row["id"] if row else config.DEFAULT_PERIOD


def get_voter():
    vid = request.cookies.get("voter_id")
    return vid if vid else uuid.uuid4().hex


def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _admin_password_from_request():
    """从 JSON body / 表单 / 请求头里取管理员密码。"""
    data = request.get_json(silent=True) or {}
    pw = data.get("password")
    if not pw:
        pw = request.form.get("password")
    if not pw:
        pw = request.headers.get("X-Admin-Password")
    return (pw or "").strip()


def _admin_ok():
    return _admin_password_from_request() == config.ADMIN_PASSWORD


def _remove_upload(stored_name):
    """删除 uploads 目录下的一个已存图片及其缩略图（best-effort，失败忽略）。"""
    if not stored_name or not is_safe_stored_filename(stored_name):
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
    thumb = os.path.join(current_app.config["UPLOAD_FOLDER"], thumb_name(stored_name))
    try:
        if os.path.isfile(thumb):
            os.remove(thumb)
    except OSError:
        pass


def _thumb_url(stored_name):
    """缩略图 URL（仅当缩略图文件已存在时返回，否则 None → 前端回退原图）。"""
    if not stored_name or not is_safe_stored_filename(stored_name):
        return None
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], thumb_name(stored_name))
    if os.path.isfile(path):
        return url_for("uploaded_file", filename=thumb_name(stored_name))
    return None


# --------------------------------------------------------------------------- #
# 页面路由
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return redirect(url_for("paidao"))


@app.route("/paidao")
def paidao():
    period = get_period()
    database = db.get_db()
    periods = database.execute("SELECT id, name FROM period ORDER BY id DESC").fetchall()
    meta = database.execute("SELECT * FROM period WHERE id=?", (period,)).fetchone()
    if meta is None:
        abort(404)

    kt = database.execute("SELECT * FROM knife_type WHERE period_id=?", (period,)).fetchall()
    users = database.execute(
        "SELECT * FROM paidao_user WHERE period_id=? ORDER BY rank", (period,)
    ).fetchall()
    knife_by_id = {k["id"]: k for k in kt}

    # 统计每个刀型被使用次数（主刀 + 尾刀格数分别计，与 202609「刀数=格数」口径一致；
    # 尾刀占位 'D' 不在 knife_by_id 中，自动跳过）
    counts = {}
    user_knives = {}
    for uk in database.execute(
        "SELECT * FROM user_knife WHERE period_id=? ORDER BY user_rank, slot", (period,)
    ):
        user_knives.setdefault(uk["user_rank"], []).append(uk)
        if uk["knife_type_id_first"] in knife_by_id:
            counts[uk["knife_type_id_first"]] = counts.get(uk["knife_type_id_first"], 0) + 1
        if uk["knife_type_id_last"] in knife_by_id:
            counts[uk["knife_type_id_last"]] = counts.get(uk["knife_type_id_last"], 0) + 1

    totals = {"B": 0, "C": 0, "D": 0}
    for k in kt:
        c = counts.get(k["id"], 0)
        if k["zone"] in totals:
            totals[k["zone"]] += c

    return render_template(
        "paidao.html",
        active="paidao",
        period=period,
        periods=periods,
        period_name=meta["name"],
        tips=meta["tips"] or "",
        knife_types=kt,
        knife_by_id=knife_by_id,
        users=users,
        user_knives=user_knives,
        counts=counts,
        totals=totals,
    )


# --------------------------------------------------------------------------- #
# 排刀：出刀完成标记
# --------------------------------------------------------------------------- #
DONE_FIELD_COLUMNS = {
    "first": "knife_type_id_first_done",
    "last": "knife_type_id_last_done",
}


@app.route("/api/user_knife/<int:uk_id>/done", methods=["POST"])
def api_user_knife_done(uk_id):
    """标记 / 取消某刀的"已完成"（上格 first、下格 last 各自独立）。"""
    data = request.get_json(silent=True) or request.form
    field = (data.get("field") or "").strip()
    col = DONE_FIELD_COLUMNS.get(field)
    if not col:
        return jsonify({"error": "field 必须为 first 或 last"}), 400
    database = db.get_db()
    row = database.execute(
        "SELECT id, %s AS cur FROM user_knife WHERE id=?" % col, (uk_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "记录不存在"}), 404
    raw = data.get("done")
    if raw is None:
        new_val = 0 if row["cur"] else 1
    else:
        new_val = 1 if str(raw).strip().lower() in ("1", "true", "yes", "on") else 0
    database.execute("UPDATE user_knife SET %s=? WHERE id=?" % col, (new_val, uk_id))
    database.commit()
    return jsonify({"ok": True, "field": field, "done": new_val})


@app.route("/axis")
def axis_page():
    period = get_period()
    database = db.get_db()
    periods = database.execute("SELECT id, name FROM period ORDER BY id DESC").fetchall()
    meta = database.execute("SELECT * FROM period WHERE id=?", (period,)).fetchone()
    if meta is None:
        abort(404)
    return render_template(
        "axis.html",
        active="axis",
        period=period,
        periods=periods,
        period_name=meta["name"],
    )


# --------------------------------------------------------------------------- #
# 图片安全输出
# --------------------------------------------------------------------------- #
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if not is_safe_stored_filename(filename):
        abort(400)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


# --------------------------------------------------------------------------- #
# 轴区 API
# --------------------------------------------------------------------------- #
@app.route("/api/axis")
def api_axis_list():
    period = get_period()
    rows = db.get_db().execute(
        "SELECT id, boss, image_path, damage, summary FROM axis "
        "WHERE period_id=? ORDER BY id DESC",
        (period,),
    ).fetchall()
    axes = [
        {
            "id": r["id"],
            "boss": r["boss"],
            "damage": r["damage"],
            "summary": r["summary"] or "",
            "image": url_for("uploaded_file", filename=r["image_path"]) if r["image_path"] else "",
            "image_thumb": _thumb_url(r["image_path"]) or "",
        }
        for r in rows
    ]
    return jsonify({"period": period, "axes": axes})


@app.route("/api/axis", methods=["POST"])
def api_axis_create():
    period = get_period()
    boss = (request.form.get("boss") or "").strip()
    damage_raw = (request.form.get("damage") or "").strip()
    summary = (request.form.get("summary") or "").strip()
    image = request.files.get("image")

    if boss not in VALID_BOSSES:
        return jsonify({"error": "BOSS 编号无效，应为 D1-D5"}), 400
    try:
        damage = float(damage_raw)
        if damage <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "伤害必须为正数（单位 e）"}), 400
    if image is None or image.filename == "":
        return jsonify({"error": "轴图不能为空"}), 400

    saved = save_image(image)
    if saved is None:
        return jsonify({"error": "图片校验失败：仅支持 PNG/JPG/WEBP，且需小于 5MB"}), 400

    database = db.get_db()
    cur = database.execute(
        "INSERT INTO axis(period_id,boss,image_path,damage,summary,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (period, boss, saved, damage, summary, now_ts()),
    )
    database.commit()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@app.route("/api/axis/<int:axis_id>")
def api_axis_detail(axis_id):
    database = db.get_db()
    ax = database.execute(
        "SELECT * FROM axis WHERE id=?", (axis_id,)
    ).fetchone()
    if ax is None:
        abort(404)
    voter = get_voter()
    comments = []
    for c in database.execute(
        "SELECT * FROM comment WHERE axis_id=? ORDER BY created_at ASC", (axis_id,)
    ):
        liked = database.execute(
            "SELECT 1 FROM comment_like WHERE comment_id=? AND voter=?",
            (c["id"], voter),
        ).fetchone()
        likes = database.execute(
            "SELECT COUNT(*) AS n FROM comment_like WHERE comment_id=?", (c["id"],)
        ).fetchone()["n"]
        comments.append(
            {
                "id": c["id"],
                "content": c["content"] or "",
                "image": url_for("uploaded_file", filename=c["image_path"]) if c["image_path"] else "",
                "uploader": c["uploader"],
                "created_at": c["created_at"],
                "likes": likes,
                "liked": bool(liked),
            }
        )
    return jsonify(
        {
            "axis": {
                "id": ax["id"],
                "boss": ax["boss"],
                "damage": ax["damage"],
                "summary": ax["summary"] or "",
                "image": url_for("uploaded_file", filename=ax["image_path"]) if ax["image_path"] else "",
                "image_thumb": _thumb_url(ax["image_path"]) or "",
                "created_at": ax["created_at"],
            },
            "comments": comments,
        }
    )


@app.route("/api/axis/<int:axis_id>", methods=["DELETE"])
def api_axis_delete(axis_id):
    """删除一条轴（需管理员密码）：级联删除其评论、评论点赞，并清理图片文件。"""
    if not _admin_ok():
        return jsonify({"error": "管理员密码错误"}), 403
    database = db.get_db()
    ax = database.execute("SELECT * FROM axis WHERE id=?", (axis_id,)).fetchone()
    if ax is None:
        return jsonify({"error": "轴不存在"}), 404
    comments = database.execute(
        "SELECT id, image_path FROM comment WHERE axis_id=?", (axis_id,)
    ).fetchall()
    for c in comments:
        database.execute("DELETE FROM comment_like WHERE comment_id=?", (c["id"],))
    database.execute("DELETE FROM comment WHERE axis_id=?", (axis_id,))
    database.execute("DELETE FROM axis WHERE id=?", (axis_id,))
    database.commit()
    # 文件删除放在事务提交之后（best-effort）
    for c in comments:
        _remove_upload(c["image_path"])
    _remove_upload(ax["image_path"])
    return jsonify({"ok": True, "deleted_comments": len(comments)})


@app.route("/api/axis/<int:axis_id>/comment", methods=["POST"])
def api_comment_create(axis_id):
    database = db.get_db()
    ax = database.execute("SELECT id FROM axis WHERE id=?", (axis_id,)).fetchone()
    if ax is None:
        abort(404)
    content = (request.form.get("content") or "").strip()
    uploader = (request.form.get("uploader") or "").strip()
    image = request.files.get("image")

    if not uploader:
        return jsonify({"error": "上传人不能为空"}), 400
    if not content and (image is None or image.filename == ""):
        return jsonify({"error": "评论文字与图片至少填一项"}), 400

    saved = None
    if image and image.filename != "":
        saved = save_image(image)
        if saved is None:
            return jsonify({"error": "图片校验失败：仅支持 PNG/JPG/WEBP，且需小于 5MB"}), 400

    cur = database.execute(
        "INSERT INTO comment(axis_id,content,image_path,uploader,created_at) "
        "VALUES(?,?,?,?,?)",
        (axis_id, content, saved, uploader, now_ts()),
    )
    database.commit()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@app.route("/api/comment/<int:comment_id>/like", methods=["POST"])
def api_comment_like(comment_id):
    database = db.get_db()
    c = database.execute("SELECT id FROM comment WHERE id=?", (comment_id,)).fetchone()
    if c is None:
        abort(404)
    voter = get_voter()
    existing = database.execute(
        "SELECT 1 FROM comment_like WHERE comment_id=? AND voter=?",
        (comment_id, voter),
    ).fetchone()
    if existing:
        database.execute(
            "DELETE FROM comment_like WHERE comment_id=? AND voter=?", (comment_id, voter)
        )
        liked = 0
    else:
        database.execute(
            "INSERT INTO comment_like(comment_id,voter) VALUES(?,?)", (comment_id, voter)
        )
        liked = 1
    database.commit()
    count = database.execute(
        "SELECT COUNT(*) AS n FROM comment_like WHERE comment_id=?", (comment_id,)
    ).fetchone()["n"]

    resp = make_response(jsonify({"count": count, "liked": liked}))
    if not request.cookies.get("voter_id"):
        resp.set_cookie("voter_id", voter, max_age=365 * 24 * 3600)
    return resp


@app.route("/api/comment/<int:comment_id>", methods=["DELETE"])
def api_comment_delete(comment_id):
    """删除一条评论（需管理员密码）：级联删除其点赞，并清理图片文件。"""
    if not _admin_ok():
        return jsonify({"error": "管理员密码错误"}), 403
    database = db.get_db()
    c = database.execute("SELECT * FROM comment WHERE id=?", (comment_id,)).fetchone()
    if c is None:
        return jsonify({"error": "评论不存在"}), 404
    database.execute("DELETE FROM comment_like WHERE comment_id=?", (comment_id,))
    database.execute("DELETE FROM comment WHERE id=?", (comment_id,))
    database.commit()
    _remove_upload(c["image_path"])
    return jsonify({"ok": True})


if __name__ == "__main__":
    # 常驻服务模式：关闭 debug/reloader（避免 reloader 子进程与 NSSM 进程监控冲突导致端口掉线）
    # 需要本地开发热重载时，临时改回 debug=True 手动跑即可。
    app.run(host="127.0.0.1", port=13201, debug=False, use_reloader=False, threaded=True)
