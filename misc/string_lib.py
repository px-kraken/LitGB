from datetime import datetime


def dtime_str() -> str:
    """Generate a datetime string for timestamps."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
