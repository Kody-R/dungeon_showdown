from __future__ import annotations
from dataclasses import dataclass, field

from items import item_summary, sort_inventory
from player import Player


@dataclass
class InventoryResult:
    messages: list[str] = field(default_factory=list)
    item_consumed: bool = False
    equipped: bool = False
    success: bool = False


class InventoryManager:
    @staticmethod
    def add_items(player: Player, items: list[dict]) -> list[str]:
        messages: list[str] = []
        for item in items:
            player.inventory.append(dict(item))
            messages.append(f"NEW ITEM! {item_summary(item)}")
            flavor = item.get("flavor")
            if flavor:
                messages.append(f"Announcer: \"{flavor}\"")
        player.inventory = sort_inventory(player.inventory)
        return messages

    @staticmethod
    def use_or_equip(player: Player, index: int) -> InventoryResult:
        if index < 0 or index >= len(player.inventory):
            return InventoryResult(["No item selected. The inventory gremlin shrugs."], success=False)
        item = player.inventory[index]
        item_type = str(item.get("type", "item")).lower()
        if item_type == "weapon":
            old = player.equipped_weapon
            player.equipped_weapon = item
            return InventoryResult([f"Equipped weapon: {item.get('name', 'Unknown Weapon')}.", _equipment_delta_line(old, item, "attack_bonus", "ATK")], equipped=True, success=True)
        if item_type == "armor":
            old = player.equipped_armor
            player.equipped_armor = item
            return InventoryResult([f"Equipped armor: {item.get('name', 'Unknown Armor')}.", _equipment_delta_line(old, item, "defense_bonus", "DEF")], equipped=True, success=True)
        if item_type == "consumable":
            return InventoryManager._use_consumable(player, index, item)
        return InventoryResult([f"{item.get('name', 'Unknown Item')} is not usable yet. It stares back with feature-roadmap energy."], success=False)

    @staticmethod
    def _use_consumable(player: Player, index: int, item: dict) -> InventoryResult:
        effect = str(item.get("effect", "")).lower()
        messages: list[str] = []
        item_name = item.get("name", "Consumable")

        # Data-driven healing support.
        # Current items.json uses:
        #   {"effect": "heal", "heal": 8}
        #   {"effect": "heal_and_inspire", "heal": 24, "attack_bonus": 2}
        # Older prototypes used restore_small_hp / restore_large_hp. Support both.
        if effect in {"heal", "restore_small_hp", "restore_large_hp", "heal_and_inspire"} or int(item.get("heal", 0) or 0) > 0:
            if effect == "restore_small_hp":
                heal_amount = 12
            elif effect == "restore_large_hp":
                heal_amount = 25
            else:
                heal_amount = int(item.get("heal", 0) or 0)

            before = player.hp
            healed = player.heal(heal_amount)
            messages.append(f"Used {item_name}. HP {before}/{player.max_hp} -> {player.hp}/{player.max_hp} (+{healed}).")

            if effect == "heal_and_inspire":
                attack_bonus = int(item.get("attack_bonus", 2) or 2)
                player.status_effects.append({
                    "id": "inspired",
                    "name": "Inspired",
                    "attack_bonus": attack_bonus,
                    "turns": 3,
                })
                messages.append(f"Inspired: +{attack_bonus} ATK for 3 combat turns.")

        elif effect == "boost_attack_temp":
            player.status_effects.append({"id": "inspired", "name": "Inspired", "attack_bonus": 2, "turns": 3})
            messages.append(f"Used {item_name}. Inspired: +2 ATK for 3 combat turns.")

        elif effect == "over_caffeinated":
            player.status_effects.append({"id": "over_caffeinated", "name": "Over-Caffeinated", "attack_bonus": 1, "luck_bonus": 1, "turns": 4})
            messages.append(f"Used {item_name}. Over-Caffeinated: +1 ATK and +1 LUCK for 4 combat turns.")

        elif effect == "combat_damage":
            return InventoryResult([f"{item_name} is a combat item. Use it from the inventory while you are in combat."], item_consumed=False, success=False)

        else:
            messages.append(f"Used {item_name}. It tasted like unresolved mechanics.")

        player.inventory.pop(index)
        return InventoryResult(messages, item_consumed=True, success=True)


def _equipment_delta_line(old: dict | None, new: dict, stat_key: str, stat_label: str) -> str:
    old_value = int((old or {}).get(stat_key, 0) or 0)
    new_value = int(new.get(stat_key, 0) or 0)
    delta = new_value - old_value
    if delta > 0:
        return f"Net {stat_label}: +{delta}."
    if delta < 0:
        return f"Net {stat_label}: {delta}."
    return f"Net {stat_label}: unchanged."
