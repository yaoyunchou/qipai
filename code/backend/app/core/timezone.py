from datetime import date, datetime
from zoneinfo import ZoneInfo

# 业务时间统一按中国时区（门店本地时间），避免 Vercel 等 UTC 环境写入错误时刻
APP_TZ = ZoneInfo("Asia/Shanghai")


def now_cn() -> datetime:
    """返回 Asia/Shanghai 当前时刻（无时区标记，与数据库 TIMESTAMP 字段一致）。"""
    return datetime.now(APP_TZ).replace(tzinfo=None)


def today_cn() -> date:
    """返回 Asia/Shanghai 当前日期。"""
    return now_cn().date()
