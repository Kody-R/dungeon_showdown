from __future__ import annotations
import json
from pathlib import Path

from config import SAVE_DIR, DEFAULT_SETTINGS
from dungeon import Floor
from player import Player
from seed_manager import seed_filename


class SaveSystem:
    def __init__(self, save_dir: Path = SAVE_DIR):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save_path(self, seed: int) -> Path:
        return self.save_dir / seed_filename(seed)

    def list_saves(self) -> list[Path]:
        return sorted(self.save_dir.glob("seed_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    def create_run_data(self, seed: int, player: Player, first_floor: Floor) -> dict:
        return {
            "seed": seed,
            "player": player.to_dict(),
            "current_floor": first_floor.floor_number,
            "floors": {str(first_floor.floor_number): first_floor.to_dict()},
            "settings": dict(DEFAULT_SETTINGS),
            "run_history": [],
        }

    def save_run(self, run_data: dict) -> None:
        path = self.save_path(run_data["seed"])
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(run_data, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def load_run(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def serialize_floor_into_run(self, run_data: dict, floor: Floor) -> None:
        run_data.setdefault("floors", {})[str(floor.floor_number)] = floor.to_dict()

    def serialize_player_into_run(self, run_data: dict, player: Player) -> None:
        run_data["player"] = player.to_dict()
