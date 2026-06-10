from __future__ import annotations
from player import Player
from dungeon import Floor


def build_run_summary(run_data: dict | None, player: Player | None, floor: Floor | None, reason: str) -> list[str]:
    if not run_data or not player:
        return ["No run data available."]
    floors_seen = len(run_data.get("floors", {}))
    defeated = len(getattr(player, "defeated_bosses", []))
    return [
        f"Result: {reason}",
        f"Seed: {run_data.get('seed', 'unknown')}",
        f"Floors generated: {floors_seen}",
        f"Current floor: {run_data.get('current_floor', 'unknown')}",
        f"Class: {player.player_class}",
        f"Level: {player.level} | XP: {player.xp}/{player.xp_to_next_level()}",
        f"HP: {player.hp}/{player.max_hp}",
        f"Credits: {player.credits}",
        f"Rooms cleared: {player.rooms_cleared}",
        f"Items found: {player.items_found}",
        f"Bosses defeated: {defeated}",
        f"Final theme: {floor.theme.get('name', 'Unknown') if floor else 'Unknown'}",
    ]
