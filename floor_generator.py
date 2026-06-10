from __future__ import annotations
import json
import random
from pathlib import Path

from config import DATA_DIR
from dungeon import Floor, Room


class FloorGenerator:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.floor_themes = self._load_json("floor_themes.json")
        self.bosses = self._load_json("bosses.json")
        self.enemies = self._load_json("enemies.json")
        self.items = self._load_json("items.json")
        self.traps = self._load_json("trap_templates.json")
        self.sponsors = self._load_json("sponsors.json")
        self.room_events = self._load_json("rooms.json")

    def _load_json(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def generate_floor(self, seed: int, floor_number: int) -> Floor:
        rng = random.Random(f"{seed}:{floor_number}:floor")
        theme = rng.choice(self.floor_themes)
        boss = self._scale_boss(self._choose_boss(rng, theme), floor_number)
        rooms = self._generate_rooms(rng, floor_number, theme)
        rooms["room_0"].visited = True
        return Floor(
            floor_number=floor_number,
            theme=theme,
            rooms=rooms,
            boss=boss,
            lore={
                "title": theme["name"],
                "intro": f"Welcome to Floor {floor_number}: {theme['name']}.",
                "description": theme.get("description", "The lights flicker. Something nearby wants a signature."),
                "warning": "Corporate reminds you that survival is not guaranteed by your current subscription tier.",
            },
            generated_by_ollama=False,
        )

    def _choose_boss(self, rng: random.Random, theme: dict) -> dict:
        tags = set(theme.get("boss_tags", []) + theme.get("enemy_tags", []))
        matching = [boss for boss in self.bosses if tags.intersection(boss.get("floor_theme_tags", []))]
        return dict(rng.choice(matching or self.bosses))

    def _scale_boss(self, boss: dict, floor_number: int) -> dict:
        boss = dict(boss)
        bump = max(0, floor_number - 1)
        boss["hp"] = int(boss.get("hp", 80)) + bump * 10
        boss["attack"] = int(boss.get("attack", 9)) + bump * 2
        boss["defense"] = int(boss.get("defense", 3)) + bump // 2
        boss["xp"] = int(boss.get("xp", 40)) + bump * 8
        return boss

    def _generate_rooms(self, rng: random.Random, floor_number: int, theme: dict) -> dict[str, Room]:
        # Phase 7: larger deterministic graph with NPC events, shop, mini-boss, and more branches.
        layout = [
            ("room_0", "Entrance", 0, 2),
            ("room_1", "Combat", 1, 2),
            ("room_2", "Loot", 2, 1),
            ("room_3", "Trap", 2, 3),
            ("room_4", "NPC Event", 3, 0),
            ("room_5", "Sponsor Crate", 3, 2),
            ("room_6", "Combat", 3, 4),
            ("room_7", "Shop", 4, 1),
            ("room_8", "Rest", 4, 3),
            ("room_9", "Mini-Boss", 5, 2),
            ("room_10", "Trap", 6, 1),
            ("room_11", "Loot", 6, 3),
            ("room_12", "Boss Gate", 7, 2),
            ("room_13", "Boss Room", 8, 2),
            ("room_14", "Exit", 9, 2),
        ]
        connections = {
            "room_0": ["room_1"],
            "room_1": ["room_0", "room_2", "room_3"],
            "room_2": ["room_1", "room_4", "room_5"],
            "room_3": ["room_1", "room_5", "room_6"],
            "room_4": ["room_2", "room_7"],
            "room_5": ["room_2", "room_3", "room_7", "room_8"],
            "room_6": ["room_3", "room_8"],
            "room_7": ["room_4", "room_5", "room_9"],
            "room_8": ["room_5", "room_6", "room_9"],
            "room_9": ["room_7", "room_8", "room_10", "room_11"],
            "room_10": ["room_9", "room_12"],
            "room_11": ["room_9", "room_12"],
            "room_12": ["room_10", "room_11", "room_13"],
            "room_13": ["room_12", "room_14"],
            "room_14": ["room_13"],
        }
        rooms: dict[str, Room] = {}
        for room_id, room_type, x, y in layout:
            rooms[room_id] = Room(
                id=room_id,
                room_type=room_type,
                title=self._room_title(rng, room_type, theme),
                description=self._room_description(room_type, theme, floor_number),
                x=x,
                y=y,
                connections=connections[room_id],
                enemies=self._choose_enemies(rng, room_type, floor_number, theme),
                loot=self._choose_loot(rng, room_type),
                trap=self._choose_trap(rng, room_type, floor_number, theme),
                event=self._choose_event(rng, room_type),
                cleared=room_type in ["Entrance"],
            )
        return rooms

    def _room_title(self, rng: random.Random, room_type: str, theme: dict) -> str:
        adjectives = ["Suspicious", "Flickering", "Discount", "Condemned", "Premium", "Unauthorized", "Overbooked", "Haunted", "Sanitized"]
        nouns = {
            "Entrance": "Arrival Platform",
            "Combat": "Customer Engagement Zone",
            "Loot": "Questionable Prize Closet",
            "Trap": "Liability Hallway",
            "Sponsor Crate": "Brand Activation Chamber",
            "NPC Event": "Contestant Services Desk",
            "Shop": "Predatory Retail Kiosk",
            "Rest": "Unlicensed Break Room",
            "Mini-Boss": "Middle Management Arena",
            "Boss Gate": "Executive Access Gate",
            "Boss Room": "Final Performance Arena",
            "Exit": "Emergency Exit-ish Door",
        }
        if room_type in ["Entrance", "Boss Gate", "Boss Room", "Exit", "Mini-Boss"]:
            return nouns[room_type]
        return f"{rng.choice(adjectives)} {nouns.get(room_type, 'Room')}"

    def _room_description(self, room_type: str, theme: dict, floor_number: int) -> str:
        theme_name = theme.get("name", "Unbranded Danger Zone")
        base = {
            "Entrance": f"You arrive on Floor {floor_number}. The broadcast lights ignite over {theme_name}.",
            "Combat": "Something hostile is contractually obligated to be here.",
            "Loot": "A prize container hums with poor judgment and possible value.",
            "Trap": "The room is quiet in the way lawsuits are quiet before discovery.",
            "Sponsor Crate": "A corporate crate sits beneath a glowing sign that says YOU'RE WELCOME.",
            "NPC Event": "Someone who has survived too long waits under a broken camera drone.",
            "Shop": "A kiosk unfolds from the wall, already calculating your desperation markup.",
            "Rest": "A damaged bench, lukewarm vending machine, and suspicious calm invite you to breathe.",
            "Mini-Boss": "A smaller arena opens. The audience still screams like this counts for their dental plan.",
            "Boss Gate": "A reinforced gate demands confidence, clearance, or a terrible idea.",
            "Boss Room": "The arena opens wide. The audience signal spikes.",
            "Exit": "A door out. Probably. The label has been corrected with marker six times.",
        }
        return base.get(room_type, "A room full of unprocessed consequences.")

    def _choose_enemies(self, rng: random.Random, room_type: str, floor_number: int, theme: dict) -> list[dict]:
        if room_type not in ["Combat", "Mini-Boss"]:
            return []
        wanted_tags = set(theme.get("enemy_tags", []))
        matching = [enemy for enemy in self.enemies if wanted_tags.intersection(enemy.get("tags", []))]
        pool = matching or self.enemies
        if not pool:
            return [{"id": "emergency_goblin", "name": "Emergency Goblin", "hp": 10, "attack": 3, "defense": 1, "xp": 6}]
        enemy_count = 1 if floor_number < 3 else rng.choice([1, 2])
        if room_type == "Mini-Boss":
            enemy_count = 1
        enemies = []
        for _ in range(enemy_count):
            enemy = dict(rng.choice(pool))
            bump = max(0, floor_number - 1)
            enemy["hp"] = int(enemy.get("hp", 10)) + bump * 2
            enemy["attack"] = int(enemy.get("attack", 3)) + bump
            enemy["defense"] = int(enemy.get("defense", 1)) + bump // 3
            enemy["xp"] = int(enemy.get("xp", 6)) + bump * 2
            if room_type == "Mini-Boss":
                enemy["name"] = "Mini-Boss " + enemy.get("name", "Enemy")
                enemy["hp"] = int(enemy["hp"] * 1.7)
                enemy["attack"] += 2
                enemy["defense"] += 1
                enemy["xp"] = int(enemy["xp"] * 2)
            enemies.append(enemy)
        return enemies

    def _choose_loot(self, rng: random.Random, room_type: str) -> list[dict]:
        if room_type not in ["Loot", "Sponsor Crate", "Shop", "NPC Event", "Mini-Boss"]:
            return []
        if not self.items:
            return [{"id": "expired_energy_drink", "name": "Expired Energy Drink", "type": "consumable"}]
        count_by_type = {"Sponsor Crate": 2, "Shop": 3, "Mini-Boss": 2, "NPC Event": 1}
        count = count_by_type.get(room_type, 1)
        return [dict(self._weighted_item_choice(rng, room_type)) for _ in range(count)]

    def _weighted_item_choice(self, rng: random.Random, room_type: str) -> dict:
        rarity_weights = {
            "common": 60,
            "uncommon": 28,
            "rare": 9,
            "epic": 2,
            "legendary": 0.7,
            "absurd": 0.3,
        }
        if room_type in ["Sponsor Crate", "Mini-Boss"]:
            rarity_weights = {
                "common": 38,
                "uncommon": 36,
                "rare": 18,
                "epic": 5,
                "legendary": 2,
                "absurd": 1,
            }
        elif room_type == "Shop":
            rarity_weights = {
                "common": 35,
                "uncommon": 40,
                "rare": 18,
                "epic": 5,
                "legendary": 1.5,
                "absurd": 0.5,
            }
        weights = [rarity_weights.get(str(item.get("rarity", "common")).lower(), 1) for item in self.items]
        return rng.choices(self.items, weights=weights, k=1)[0]

    def _choose_trap(self, rng: random.Random, room_type: str, floor_number: int, theme: dict) -> dict | None:
        if room_type != "Trap":
            return None
        wanted_tags = set(theme.get("trap_tags", []))
        matching = [trap for trap in self.traps if wanted_tags.intersection(trap.get("tags", []))]
        pool = matching or self.traps
        if not pool:
            return {"id": "survey_kiosk", "name": "Corporate Survey Kiosk", "difficulty": 10 + floor_number}
        trap = dict(rng.choice(pool))
        trap["difficulty"] = int(trap.get("difficulty", 10)) + max(0, floor_number - 1)
        return trap

    def _choose_event(self, rng: random.Random, room_type: str) -> dict | None:
        if room_type not in ["NPC Event", "Shop"]:
            return None
        matching = [event for event in self.room_events if event.get("type") == room_type]
        if not matching and room_type == "Shop":
            matching = [event for event in self.room_events if event.get("id") == "brand_shop"]
        if not matching:
            return None
        event = dict(rng.choice(matching))
        outcomes = event.get("outcomes", [])
        if outcomes:
            event["chosen_text"] = rng.choice(outcomes)
        return event
