"""全局配置：路径、上传限制、图片白名单。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库文件（运行时生成，已 gitignore）
DATABASE = os.path.join(BASE_DIR, "data", "app.db")

# 上传目录（运行时生成，已 gitignore）
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# 单文件最大体积：5MB
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

# 允许的图片真实格式（由 magic number 校验，不依赖扩展名）
ALLOWED_IMAGE_EXT = {"png", "jpg", "webp"}

# 期数种子文件（复制自参考项目 202609）
SEED_FILE = os.path.join(BASE_DIR, "seed_data", "202609.js")

# 管理员密码（删除轴 / 删除评论时校验；简单门槛，非完整鉴权）
ADMIN_PASSWORD = "zdtxd1"

# 默认期数（仅在 period 表为空时兜底；正常情况下取最新一期）
DEFAULT_PERIOD = "202609"

# 手工登记的期数（只建期数档案，不导入排刀数据）：(期数ID, 显示名)
# 202609 由 seed.py 从 seed_data/202609.js 导入，后续新增的期登记在这里即可
EXTRA_PERIODS = [
    ("202610", "S92天蝎座202610喵园首日排刀表"),
]
