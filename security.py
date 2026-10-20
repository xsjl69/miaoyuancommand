"""图片上传安全校验：魔数校验真实格式、重命名落盘、限制大小。

绝不信任客户端提交的扩展名 / MIME，所有判定以文件头字节为准。
"""
import os
import uuid

from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH


def detect_image_ext(data: bytes):
    """依据文件头（magic number）判断真实图片格式，返回扩展名或 None。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(stream) -> str | None:
    """读取上传流，校验后落盘为随机名文件。成功返回文件名，失败返回 None。

    落盘成功后同步生成缩略图（best-effort，失败不影响上传本身）。
    """
    data = stream.read()
    if not data:
        return None
    if len(data) > MAX_CONTENT_LENGTH:
        return None
    ext = detect_image_ext(data)
    if ext is None:
        return None
    filename = uuid.uuid4().hex + "." + ext
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with open(os.path.join(UPLOAD_FOLDER, filename), "wb") as f:
        f.write(data)
    make_thumbnail(os.path.join(UPLOAD_FOLDER, filename))
    return filename


THUMB_SUFFIX = "_thumb.webp"
THUMB_MAX_EDGE = 640  # 列表卡片最高 130px，640px 足够 2x 屏清晰


def thumb_name(filename: str) -> str:
    """由原图文件名得到缩略图文件名（同目录，固定 _thumb.webp 后缀）。"""
    stem, _ = os.path.splitext(filename)
    return stem + THUMB_SUFFIX


def make_thumbnail(path: str):
    """为已落盘图片生成 WEBP 缩略图（最长边 ≤ THUMB_MAX_EDGE）。

    best-effort：Pillow 缺失或图片损坏时静默跳过，绝不影响上传主流程。
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    thumb = thumb_name(os.path.basename(path))
    thumb_path = os.path.join(os.path.dirname(path), thumb)
    if os.path.exists(thumb_path):
        return thumb
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE))
            im.save(thumb_path, "WEBP", quality=78, method=4)
        return thumb
    except Exception:
        try:
            if os.path.exists(thumb_path):
                os.remove(thumb_path)  # 半写坏文件不留垃圾
        except OSError:
            pass
        return None


def is_safe_stored_filename(name: str) -> bool:
    """校验通过 /uploads/<name> 输出的文件名仅含安全字符，杜绝目录遍历。"""
    import re
    return re.match(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9]+$", name) is not None
