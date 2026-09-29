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
    """读取上传流，校验后落盘为随机名文件。成功返回文件名，失败返回 None。"""
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
    return filename


def is_safe_stored_filename(name: str) -> bool:
    """校验通过 /uploads/<name> 输出的文件名仅含安全字符，杜绝目录遍历。"""
    import re
    return re.match(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9]+$", name) is not None
