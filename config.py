from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
SAVE_DIR = PROJECT_ROOT / "saves"
ASSET_DIR = PROJECT_ROOT / "assets"

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

TITLE = "Dungeon Showdown"
DEFAULT_FONT_SIZE = 22
SMALL_FONT_SIZE = 18
BIG_FONT_SIZE = 42

ROOM_W = 84
ROOM_H = 62
ROOM_GAP = 22

COLORS = {
    "bg": (10, 12, 18),
    "panel": (22, 26, 36),
    "panel_light": (35, 42, 56),
    "text": (230, 235, 245),
    "muted": (150, 160, 175),
    "accent": (255, 198, 54),
    "danger": (230, 70, 70),
    "good": (95, 220, 140),
    "room": (57, 68, 88),
    "room_current": (255, 198, 54),
    "room_cleared": (70, 135, 100),
    "room_locked": (80, 80, 88),
    "button": (45, 55, 72),
    "button_hover": (68, 82, 105),
    "gold": (245, 186, 65),
    "blue": (100, 170, 255),
    "purple": (180, 120, 255),
}

THEMES = {
    "hazard": {
        "name": "Hazard Broadcast",
        "bg": (10, 12, 18),
        "panel": (22, 26, 36),
        "accent": (255, 198, 54),
    },
    "cold": {
        "name": "Cold Corporate",
        "bg": (8, 14, 22),
        "panel": (18, 31, 44),
        "accent": (100, 190, 255),
    },
    "toxic": {
        "name": "Toxic Neon",
        "bg": (9, 16, 10),
        "panel": (18, 36, 22),
        "accent": (125, 255, 120),
    },
}

DIFFICULTY_SETTINGS = {
    "easy": {"enemy_hp": 0.85, "enemy_attack": 0.85, "trap_bonus": -2, "credit_bonus": 4},
    "normal": {"enemy_hp": 1.0, "enemy_attack": 1.0, "trap_bonus": 0, "credit_bonus": 0},
    "hard": {"enemy_hp": 1.20, "enemy_attack": 1.15, "trap_bonus": 2, "credit_bonus": -2},
    "nightmare": {"enemy_hp": 1.40, "enemy_attack": 1.30, "trap_bonus": 4, "credit_bonus": -4},
}



DEFAULT_SETTINGS = {
    "fullscreen": False,
    "autosave": True,
    "difficulty": "normal",
    "ui_theme": "hazard",
    "ollama_enabled": True,
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_model": "llama3.1:8b",
    "text_generation_timeout": 90,
    "text_speed": "normal",
    "music_volume": 0.5,
    "sound_volume": 0.7,
}
