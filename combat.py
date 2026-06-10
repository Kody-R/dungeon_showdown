from __future__ import annotations
from dataclasses import dataclass, field
import random

from enemies import Combatant
from player import Player


LOCAL_COMBAT_LINES = [
    "The audience leans forward, mostly for insurance reasons.",
    "Somewhere, a producer whispers: make it messier.",
    "The dungeon camera zooms in like it has alimony payments.",
    "A sponsor logo flashes over the blood-safety disclaimer.",
]

CRIT_LINES = [
    "CRITICAL! That one had paperwork attached!",
    "CRITICAL! The audience loves blunt-force problem solving!",
    "CRITICAL! That hit just voided three warranties.",
]

DEFEND_LINES = [
    "You defend. Bold choice: becoming less hittable.",
    "You brace yourself and briefly resemble a tactical filing cabinet.",
]


@dataclass
class CombatResult:
    messages: list[str] = field(default_factory=list)
    victory: bool = False
    defeat: bool = False
    fled: bool = False


class CombatEncounter:
    def __init__(self, player: Player, enemies: list[dict], seed: int, floor_number: int, room_id: str, is_boss: bool = False):
        self.player = player
        self.seed = seed
        self.floor_number = floor_number
        self.room_id = room_id
        self.is_boss = is_boss
        self.rng = random.Random(f"{seed}:{floor_number}:{room_id}:combat")
        self.enemies = [Combatant.from_template(enemy, floor_number, is_boss=is_boss) for enemy in enemies]
        self.turn = 1
        self.player_defending = False
        self.finished = False
        self.victory = False
        self.defeat = False
        self.fled = False
        self.messages = [
            f"Combat starts: {self.enemy_summary()}.",
            self.rng.choice(LOCAL_COMBAT_LINES),
        ]
        if len(self.enemies) == 1 and self.enemies[0].flavor:
            self.messages.append(self.enemies[0].flavor)

    def enemy_summary(self) -> str:
        names = [enemy.name for enemy in self.enemies if enemy.alive]
        return ", ".join(names) if names else "nothing legally attackable"

    def active_enemy(self) -> Combatant | None:
        for enemy in self.enemies:
            if enemy.alive:
                return enemy
        return None

    def attack(self) -> CombatResult:
        result = CombatResult()
        if self.finished:
            result.messages.append("The fight is already over.")
            return result
        enemy = self.active_enemy()
        if not enemy:
            return self._finish_victory(result)

        crit = self.rng.random() < self.player.crit_chance()
        damage = self._player_damage(enemy, crit)
        enemy.hp = max(0, enemy.hp - damage)
        result.messages.append(f"You hit {enemy.name} for {damage} damage.")
        if crit:
            result.messages.append(self.rng.choice(CRIT_LINES))

        if not enemy.alive:
            result.messages.append(f"{enemy.name} collapses into a very marketable heap.")
            if not self.active_enemy():
                return self._finish_victory(result)

        result.messages.extend(self._enemy_turn())
        self.turn += 1
        if self.player.hp <= 0:
            return self._finish_defeat(result)
        result.messages.extend(self._tick_player_statuses())
        return result

    def defend(self) -> CombatResult:
        result = CombatResult(messages=[self.rng.choice(DEFEND_LINES)])
        if self.finished:
            result.messages.append("The fight is already over.")
            return result
        self.player_defending = True
        result.messages.extend(self._enemy_turn())
        self.player_defending = False
        self.turn += 1
        if self.player.hp <= 0:
            return self._finish_defeat(result)
        result.messages.extend(self._tick_player_statuses())
        return result

    def flee(self) -> CombatResult:
        result = CombatResult()
        if self.is_boss:
            result.messages.append("The boss arena doors laugh at your escape plan.")
            result.messages.extend(self._enemy_turn())
            if self.player.hp <= 0:
                return self._finish_defeat(result)
            result.messages.extend(self._tick_player_statuses())
            return result
        chance = 0.45 + min(0.25, self.player.total_luck() * 0.04)
        if self.rng.random() < chance:
            self.finished = True
            self.fled = True
            result.fled = True
            result.messages.append("You flee successfully. The audience files a complaint about pacing.")
            return result
        result.messages.append("You fail to flee. A camera drone captures the whole embarrassing attempt.")
        result.messages.extend(self._enemy_turn())
        if self.player.hp <= 0:
            return self._finish_defeat(result)
        result.messages.extend(self._tick_player_statuses())
        return result

    def use_combat_item(self, item: dict) -> CombatResult:
        """Use a targeted combat consumable against the active enemy.

        Supported data shape from items.json:
            {"type": "consumable", "effect": "combat_damage", "damage": 18}

        The item is removed by the inventory screen after this method succeeds.
        This method owns enemy damage, enemy retaliation, victory, defeat,
        status ticks, and turn advancement.
        """
        result = CombatResult()
        if self.finished:
            result.messages.append("The fight is already over.")
            return result

        enemy = self.active_enemy()
        if not enemy:
            return self._finish_victory(result)

        item_name = item.get("name", "Combat Item")
        effect = str(item.get("effect", "")).lower()

        if effect != "combat_damage":
            result.messages.append(f"{item_name} is not a targeted combat item.")
            return result

        base_damage = int(item.get("damage", 0) or 0)
        if base_damage <= 0:
            result.messages.append(f"{item_name} sputters dramatically but deals no damage.")
            result.messages.extend(self._enemy_turn())
            self.turn += 1
            if self.player.hp <= 0:
                return self._finish_defeat(result)
            result.messages.extend(self._tick_player_statuses())
            return result

        # Consumable combat damage bypasses part of defense, but still respects armor.
        damage = max(1, base_damage - max(0, enemy.defense // 2))
        before = enemy.hp
        enemy.hp = max(0, enemy.hp - damage)
        result.messages.append(f"Used {item_name} on {enemy.name}. Enemy HP {before}/{enemy.max_hp} -> {enemy.hp}/{enemy.max_hp} (-{damage}).")

        if not enemy.alive:
            result.messages.append(f"{enemy.name} is deleted from the fight by consumer-grade violence.")
            if not self.active_enemy():
                return self._finish_victory(result)

        result.messages.extend(self._enemy_turn())
        self.turn += 1
        if self.player.hp <= 0:
            return self._finish_defeat(result)
        result.messages.extend(self._tick_player_statuses())
        return result

    def inspect(self) -> CombatResult:
        result = CombatResult()
        enemy = self.active_enemy()
        if not enemy:
            result.messages.append("There is nothing left to inspect except consequences.")
            return result
        abilities = ", ".join(enemy.abilities) if enemy.abilities else "none listed"
        result.messages.append(f"{enemy.name}: HP {enemy.hp}/{enemy.max_hp}, ATK {enemy.attack}, DEF {enemy.defense}, abilities: {abilities}.")
        if enemy.flavor:
            result.messages.append(enemy.flavor)
        return result

    def _player_damage(self, enemy: Combatant, crit: bool) -> int:
        roll = self.rng.randint(-1, 2)
        damage = max(1, self.player.total_attack() + roll - enemy.defense)
        if crit:
            damage *= 2
        return damage

    def _enemy_turn(self) -> list[str]:
        messages: list[str] = []
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if self.rng.random() < 0.12:
                messages.append(f"{enemy.name} taunts you instead of making a good tactical decision.")
                continue
            roll = self.rng.randint(-1, 2)
            player_defense = self.player.total_defense()
            defend_bonus = max(1, player_defense) if self.player_defending else 0
            damage = max(1, enemy.attack + roll - player_defense - defend_bonus)
            self.player.hp = max(0, self.player.hp - damage)
            messages.append(f"{enemy.name} hits you for {damage} damage.")
            if self.player.hp <= 0:
                break
        if self.rng.random() < 0.25:
            messages.append(self.rng.choice(LOCAL_COMBAT_LINES))
        return messages

    def _tick_player_statuses(self) -> list[str]:
        expired = self.player.tick_status_effects()
        return [f"Status expired: {name}." for name in expired]

    def _finish_victory(self, result: CombatResult) -> CombatResult:
        self.finished = True
        self.victory = True
        result.victory = True
        xp = sum(enemy.xp for enemy in self.enemies)
        leveled = self.player.gain_xp(xp)
        result.messages.append(f"Victory! You gain {xp} XP.")
        if leveled:
            result.messages.append(f"LEVEL UP! You are now level {self.player.level}. Your survivability paperwork improves.")
        return result

    def _finish_defeat(self, result: CombatResult) -> CombatResult:
        self.finished = True
        self.defeat = True
        result.defeat = True
        result.messages.append("You have been defeated. The broadcast cuts to a tasteful sponsored obituary.")
        return result
