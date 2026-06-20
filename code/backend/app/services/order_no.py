import random

from app.core.timezone import now_cn


def generate_order_no() -> str:
    ts = now_cn().strftime("%Y%m%d%H%M%S")
    return f"QP{ts}{random.randint(1000, 9999)}"
