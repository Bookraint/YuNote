import logging
import os
from pathlib import Path

VERSION = "v0.1.0"
YEAR = 2026
APP_NAME = "小宇笔记助手"
AUTHOR = ""

HELP_URL = ""
GITHUB_REPO_URL = ""
RELEASE_URL = ""
FEEDBACK_URL = ""

# 路径
ROOT_PATH = Path(__file__).parent.parent

RESOURCE_PATH = ROOT_PATH / "resource"
APPDATA_PATH = ROOT_PATH / "AppData"
BIN_PATH = RESOURCE_PATH / "bin"
ASSETS_PATH = RESOURCE_PATH / "assets"
PROMPTS_PATH = RESOURCE_PATH / "prompts"
TRANSLATIONS_PATH = RESOURCE_PATH / "translations"

LOG_PATH = APPDATA_PATH / "logs"
LLM_LOG_FILE = LOG_PATH / "llm_requests.jsonl"
SETTINGS_PATH = APPDATA_PATH / "settings.json"
MODEL_PATH = APPDATA_PATH / "models"
NOTES_PATH = APPDATA_PATH / "notes"
CACHE_PATH = APPDATA_PATH / "cache"

FASTER_WHISPER_PATH = BIN_PATH / "Faster-Whisper-XXL"

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 环境变量添加 bin 路径
os.environ["PATH"] = str(FASTER_WHISPER_PATH) + os.pathsep + os.environ["PATH"]
os.environ["PATH"] = str(BIN_PATH) + os.pathsep + os.environ["PATH"]

# 创建必要目录
for p in [LOG_PATH, MODEL_PATH, NOTES_PATH, CACHE_PATH]:
    p.mkdir(parents=True, exist_ok=True)
