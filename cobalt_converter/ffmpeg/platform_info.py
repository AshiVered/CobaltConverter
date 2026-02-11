import platform
import sys


def get_platform_key() -> str:
    system = sys.platform
    machine = platform.machine()
    return f"{system}_{machine}"
