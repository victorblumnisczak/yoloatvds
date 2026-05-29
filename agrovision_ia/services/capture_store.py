import os
from services.config import SAVE_DIR


def list_captures() -> list:
    if not os.path.isdir(SAVE_DIR):
        return []
    files = sorted(os.listdir(SAVE_DIR), reverse=True)
    return [f"/static/captures/{f}" for f in files if f.endswith(".jpg")]
