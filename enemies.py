from __future__ import annotations
from dataclasses import dataclass, field, asdict
import copy
import json
import random
from pathlib import Path

from config import DATA_DIR


@dataclass
class Combatant:
    id: str
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    xp: int = 0
    abilities: list[str] = field(default_factory=list)
    flavor: str = ""
    tags: list[str] = field(default_factory=list)
    is_boss: bool = False

    @classmethod
    def from_template(cls, template: dict, floor_number: int = 1, is_boss: bool = False) -> "Combatant":
        hp = int(template.get("hp", 10)) + max(0, floor_number - 1) * (8 if is_boss else 3)
        attack = int(template.get("attack", 3)) + max(0, floor_number - 1)
        defense = int(template.get("defense", 1)) + max(0, floor_number - 1) // 2
        xp = int(template.get("xp", 25 if is_boss else 8)) + max(0, floor_number - 1) * (8 if is_boss else 2)
        return cls(
            id=str(template.get("id", "enemy")),
            name=str(template.get("name", "Unnamed Problem")),
            hp=hp,
            max_hp=hp,
            attack=attack,
            defense=defense,
            xp=xp,
            abilities=list(template.get("abilities", [])),
            flavor=str(template.get("flavor", "It looks offended by your continued survival.")),
            tags=list(template.get("tags", template.get("floor_theme_tags", []))),
            is_boss=is_boss,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Combatant":
        # Supports old placeholder enemy dicts from Phase 1-2 saves.
        hp = int(data.get("hp", 10))
        return cls(
            id=str(data.get("id", "enemy")),
            name=str(data.get("name", "Unnamed Problem")),
            hp=hp,
            max_hp=int(data.get("max_hp", hp)),
            attack=int(data.get("attack", 3)),
            defense=int(data.get("defense", 1)),
            xp=int(data.get("xp", 6)),
            abilities=list(data.get("abilities", [])),
            flavor=str(data.get("flavor", "It looks hostile and under-supervised.")),
            tags=list(data.get("tags", [])),
            is_boss=bool(data.get("is_boss", False)),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def alive(self) -> bool:
        return self.hp > 0


class EnemyCatalog:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.enemies = self._load_json("enemies.json")

    def _load_json(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def choose_enemy(self, rng: random.Random, theme: dict, floor_number: int) -> dict:
        wanted_tags = set(theme.get("enemy_tags", []))
        matches = [enemy for enemy in self.enemies if wanted_tags.intersection(enemy.get("tags", []))]
        pool = matches or self.enemies or [
            {
                "id": "emergency_goblin",
                "name": "Emergency Goblin",
                "hp": 10,
                "attack": 3,
                "defense": 1,
                "xp": 6,
                "tags": ["fallback"],
                "abilities": [],
                "flavor": "A fallback creature from the legal department's backup folder.",
            }
        ]
        template = copy.deepcopy(rng.choice(pool))
        template["hp"] = int(template.get("hp", 10)) + max(0, floor_number - 1) * 2
        template["attack"] = int(template.get("attack", 3)) + max(0, floor_number - 1)
        template["defense"] = int(template.get("defense", 1)) + max(0, floor_number - 1) // 3
        template["xp"] = int(template.get("xp", 6)) + max(0, floor_number - 1) * 2
        return template
