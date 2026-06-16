from datetime import datetime
import random


def generate_order_no() -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"QP{ts}{random.randint(1000, 9999)}"
