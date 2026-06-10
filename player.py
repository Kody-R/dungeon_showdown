from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path

from config import DATA_DIR


@dataclass
class Player:
    name: str = "Crawler"
    player_class: str = "IT Department Survivor"
    class_id: str = "it_department_survivor"
    class_description: str = "Survived printer drivers, password resets, and now whatever this is."
    special_ability: str = "Have You Tried Rebooting It: balanced stats with extra luck."
    level: int = 1
    xp: int = 0
    hp: int = 30
    max_hp: int = 30
    attack: int = 5
    defense: int = 2
    luck: int = 1
    credits: int = 25
    rooms_cleared: int = 0
    items_found: int = 0
    traps_survived: int = 0
    defeated_bosses: list[str] = field(default_factory=list)
    current_room_id: str = "room_0"
    inventory: list[dict] = field(default_factory=list)
    equipped_weapon: dict | None = None
    equipped_armor: dict | None = None
    status_effects: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        allowed = {field_name for field_name in cls.__dataclass_fields__}
        clean = {key: value for key, value in data.items() if key in allowed}
        return cls(**clean)

    @classmethod
    def from_class_template(cls, class_template: dict, item_catalog: list[dict] | None = None) -> "Player":
        item_catalog = item_catalog or []
        items_by_id = {item.get("id"): dict(item) for item in item_catalog}
        inventory = [items_by_id[item_id] for item_id in class_template.get("starting_items", []) if item_id in items_by_id]
        max_hp = int(class_template.get("hp", 30))
        return cls(
            name="Crawler",
            player_class=str(class_template.get("name", "IT Department Survivor")),
            class_id=str(class_template.get("id", "it_department_survivor")),
            class_description=str(class_template.get("description", "")),
            special_ability=str(class_template.get("special", "")),
            hp=max_hp,
            max_hp=max_hp,
            attack=int(class_template.get("attack", 5)),
            defense=int(class_template.get("defense", 2)),
            luck=int(class_template.get("luck", 1)),
            credits=int(class_template.get("credits", 25)),
            inventory=inventory,
        )

    @staticmethod
    def load_class_templates(data_dir: Path = DATA_DIR) -> list[dict]:
        path = data_dir / "player_classes.json"
        if not path.exists():
            return [{
                "id": "it_department_survivor",
                "name": "IT Department Survivor",
                "description": "Balanced survivor with extra luck.",
                "hp": 30,
                "attack": 5,
                "defense": 2,
                "luck": 3,
                "starting_items": [],
                "special": "Balanced fallback class.",
            }]
        return json.loads(path.read_text(encoding="utf-8"))

    def heal_full(self) -> None:
        self.hp = self.max_hp

    def heal(self, amount: int) -> int:
        before = self.hp
        self.hp = min(self.max_hp, self.hp + max(0, amount))
        return self.hp - before

    def equipment_attack_bonus(self) -> int:
        weapon = self.equipped_weapon or {}
        trinket_bonus = sum(int(item.get("attack_bonus", 0) or 0) for item in self.inventory if item.get("type") == "trinket")
        return int(weapon.get("attack_bonus", 0) or 0) + trinket_bonus

    def equipment_defense_bonus(self) -> int:
        armor = self.equipped_armor or {}
        return int(armor.get("defense_bonus", 0) or 0)

    def equipment_luck_bonus(self) -> int:
        equipped = [self.equipped_weapon or {}, self.equipped_armor or {}]
        inventory_trinkets = [item for item in self.inventory if item.get("type") == "trinket"]
        return sum(int(item.get("luck_bonus", 0) or 0) for item in equipped + inventory_trinkets)

    def status_attack_bonus(self) -> int:
        return sum(int(effect.get("attack_bonus", 0) or 0) for effect in self.status_effects)

    def status_defense_bonus(self) -> int:
        return sum(int(effect.get("defense_bonus", 0) or 0) for effect in self.status_effects)

    def status_luck_bonus(self) -> int:
        return sum(int(effect.get("luck_bonus", 0) or 0) for effect in self.status_effects)

    def total_attack(self) -> int:
        return self.attack + self.equipment_attack_bonus() + self.status_attack_bonus()

    def total_defense(self) -> int:
        return self.defense + self.equipment_defense_bonus() + self.status_defense_bonus()

    def total_luck(self) -> int:
        return self.luck + self.equipment_luck_bonus() + self.status_luck_bonus()

    def tick_status_effects(self) -> list[str]:
        expired: list[str] = []
        kept: list[dict] = []
        for effect in self.status_effects:
            if "turns" not in effect:
                kept.append(effect)
                continue
            effect = dict(effect)
            effect["turns"] = int(effect.get("turns", 0)) - 1
            if effect["turns"] <= 0:
                expired.append(effect.get("name", effect.get("id", "Status effect")))
            else:
                kept.append(effect)
        self.status_effects = kept
        return expired

    def xp_to_next_level(self) -> int:
        return 20 + (self.level - 1) * 15

    def gain_xp(self, amount: int) -> bool:
        self.xp += max(0, amount)
        leveled = False
        while self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            self.max_hp += 6
            self.attack += 1
            if self.level % 2 == 0:
                self.defense += 1
            if self.level % 3 == 0:
                self.luck += 1
            self.hp = self.max_hp
            leveled = True
        return leveled

    def crit_chance(self) -> float:
        return min(0.30, 0.05 + self.total_luck() * 0.02)

    def display_lines(self) -> list[str]:
        weapon = self.equipped_weapon["name"] if self.equipped_weapon else "None"
        armor = self.equipped_armor["name"] if self.equipped_armor else "None"
        return [
            f"Name: {self.name}",
            f"Class: {self.player_class}",
            f"Special: {self.special_ability[:52]}",
            f"Level: {self.level}  XP: {self.xp}/{self.xp_to_next_level()}",
            f"HP: {self.hp}/{self.max_hp}",
            f"ATK: {self.total_attack()} ({self.attack} base)  DEF: {self.total_defense()} ({self.defense} base)",
            f"LUCK: {self.total_luck()} ({self.luck} base)  Credits: {self.credits}",
            f"Items: {len(self.inventory)}  Found: {self.items_found}  Rooms Cleared: {self.rooms_cleared}",
            f"Weapon: {weapon}",
            f"Armor: {armor}",
            f"Room: {self.current_room_id}",
        ]
