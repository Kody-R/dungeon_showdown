from __future__ import annotations
import json
from pathlib import Path

from config import DATA_DIR

RARITY_ORDER = {
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "epic": 4,
    "legendary": 5,
    "absurd": 6,
}

RARITY_LABELS = {
    "common": "Common",
    "uncommon": "Uncommon",
    "rare": "Rare",
    "epic": "Epic",
    "legendary": "Legendary",
    "absurd": "Absurd",
}


def rarity_rank(item: dict) -> int:
    return RARITY_ORDER.get(str(item.get("rarity", "common")).lower(), 1)


def rarity_label(item: dict) -> str:
    return RARITY_LABELS.get(str(item.get("rarity", "common")).lower(), "Common")


def item_summary(item: dict) -> str:
    parts = [item.get("name", "Unknown Item"), rarity_label(item), item.get("type", "item").title()]
    attack = int(item.get("attack_bonus", 0) or 0)
    defense = int(item.get("defense_bonus", 0) or 0)
    if attack:
        parts.append(f"+{attack} ATK")
    if defense:
        parts.append(f"+{defense} DEF")
    effect = item.get("effect")
    if effect and effect != "none":
        parts.append(str(effect).replace("_", " ").title())
    return " | ".join(parts)



def item_price(item: dict) -> int:
    base_by_rarity = {
        "common": 12,
        "uncommon": 24,
        "rare": 48,
        "epic": 90,
        "legendary": 160,
        "absurd": 240,
    }
    rarity = str(item.get("rarity", "common")).lower()
    price = base_by_rarity.get(rarity, 12)
    if item.get("type") == "consumable":
        price = int(price * 0.75)
    return max(1, price)

def sort_inventory(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: (-rarity_rank(item), item.get("type", ""), item.get("name", "")))


class ItemCatalog:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.path = data_dir / "items.json"
        self.items = self._load()

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def by_id(self, item_id: str) -> dict | None:
        for item in self.items:
            if item.get("id") == item_id:
                return dict(item)
        return None
