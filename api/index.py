"""Vercel Python 入口：将 code/backend FastAPI 应用暴露为 serverless 函数。"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "code" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: F401
