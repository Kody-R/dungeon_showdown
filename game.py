from __future__ import annotations
from pathlib import Path
import time
import pygame

from announcer import Announcer
from asset_manager import AssetManager
from audio_manager import AudioManager
from combat import CombatEncounter
from config import ASSET_DIR, COLORS, DEFAULT_SETTINGS, DIFFICULTY_SETTINGS, FPS, SCREEN_HEIGHT, SCREEN_WIDTH, THEMES, TITLE
from dungeon import Floor
from floor_generator import FloorGenerator
from inventory import InventoryManager
from items import item_price, item_summary, rarity_label, sort_inventory
from lore_manager import LoreManager
from ollama_client import OllamaClient
from player import Player
from save_system import SaveSystem
from run_summary import build_run_summary
from seed_manager import new_seed
from ui import Button, TextLog, draw_text, draw_wrapped_text, load_fonts


class GameState:
    MAIN_MENU = "main_menu"
    PLAYING = "playing"
    LOAD_GAME = "load_game"
    SETTINGS = "settings"
    CLASS_SELECT = "class_select"
    FLOOR_INTRO = "floor_intro"
    OLLAMA_GENERATION = "ollama_generation"
    COMBAT = "combat"
    DEATH = "death"
    INVENTORY = "inventory"
    SHOP = "shop"
    LOOT_REVEAL = "loot_reveal"
    FLOOR_COMPLETE = "floor_complete"
    RUN_SUMMARY = "run_summary"


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.small_font, self.font, self.big_font = load_fonts()

        self.state = GameState.MAIN_MENU
        self.running = True
        self.log = TextLog()
        self.combat_log = TextLog(max_lines=80)
        self.save_system = SaveSystem()
        self.floor_generator = FloorGenerator()
        self.ollama_client = OllamaClient(
            model="llama3.1:8b",
            base_url="http://localhost:11434",
            timeout=45,
            enabled=True,
        )
        self.lore_manager = LoreManager(self.ollama_client)
        self.announcer = Announcer()
        self.assets = AssetManager(ASSET_DIR)
        self.audio = AudioManager(ASSET_DIR)
        self.ollama_generation_lines: list[str] = []
        self.detected_models: list[str] = []
        self.class_templates = Player.load_class_templates()
        self.selected_class_index = 0

        self.run_data: dict | None = None
        self.player: Player | None = None
        self.floor: Floor | None = None
        self.combat: CombatEncounter | None = None
        self.menu_buttons: list[Button] = []
        self.load_buttons: list[Button] = []
        self.selected_save_paths: list[Path] = []
        self.inventory_selection = 0
        self.shop_selection = 0
        self.loot_reveal_items: list[dict] = []
        self.loot_reveal_index = 0
        self.pending_floor_number: int | None = None
        self.floor_completion_summary: dict = {}
        self.previous_state_before_inventory = GameState.PLAYING
        self.selected_settings_index = 0
        self.run_summary_reason = "Run summary"
        self.room_click_targets: dict[str, pygame.Rect] = {}

        self._build_main_menu()


    def apply_ui_theme(self) -> None:
        settings = self.current_settings() if hasattr(self, "run_data") else DEFAULT_SETTINGS
        theme = THEMES.get(str(settings.get("ui_theme", "hazard")), THEMES["hazard"])
        COLORS["bg"] = theme["bg"]
        COLORS["panel"] = theme["panel"]
        COLORS["accent"] = theme["accent"]

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_click(event.pos)

    def handle_keydown(self, key: int) -> None:
        if self.state == GameState.CLASS_SELECT:
            self.handle_class_select_keydown(key)
            return

        if self.state == GameState.COMBAT:
            self.handle_combat_keydown(key)
            return

        if self.state == GameState.INVENTORY:
            self.handle_inventory_keydown(key)
            return

        if self.state == GameState.SHOP:
            self.handle_shop_keydown(key)
            return

        if self.state == GameState.LOOT_REVEAL:
            self.handle_loot_reveal_keydown(key)
            return

        if self.state == GameState.FLOOR_COMPLETE:
            self.handle_floor_complete_keydown(key)
            return

        if self.state == GameState.SETTINGS:
            self.handle_settings_keydown(key)
            return

        if self.state == GameState.RUN_SUMMARY:
            if key in [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE]:
                self._build_main_menu()
                self.state = GameState.MAIN_MENU
            return

        if self.state == GameState.DEATH:
            if key in [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE]:
                self._build_main_menu()
                self.state = GameState.MAIN_MENU
            return

        if key == pygame.K_ESCAPE:
            if self.state == GameState.PLAYING:
                self._build_main_menu()
                self.state = GameState.MAIN_MENU
            elif self.state in [GameState.LOAD_GAME, GameState.SETTINGS, GameState.FLOOR_INTRO, GameState.INVENTORY, GameState.SHOP, GameState.LOOT_REVEAL, GameState.FLOOR_COMPLETE, GameState.OLLAMA_GENERATION]:
                self._build_main_menu()
                self.state = GameState.MAIN_MENU
            else:
                self.running = False
            return

        if self.state == GameState.FLOOR_INTRO and key in [pygame.K_RETURN, pygame.K_SPACE]:
            self.state = GameState.PLAYING
            return

        if self.state == GameState.PLAYING:
            if key in [pygame.K_w, pygame.K_UP]:
                self.move_by_direction("north")
            elif key in [pygame.K_d, pygame.K_RIGHT]:
                self.move_by_direction("east")
            elif key in [pygame.K_s, pygame.K_DOWN]:
                self.move_by_direction("south")
            elif key in [pygame.K_a, pygame.K_LEFT]:
                self.move_by_direction("west")
            elif key == pygame.K_i:
                self.open_inventory(GameState.PLAYING)
            elif key == pygame.K_m:
                self.log.add("Map is visible. Corporate has not approved zooming yet.")
            elif key == pygame.K_c and self.player:
                self.log.add(f"Character checked. HP {self.player.hp}/{self.player.max_hp}, XP {self.player.xp}/{self.player.xp_to_next_level()}.")
            elif key == pygame.K_RETURN:
                self.interact_current_room()

    def handle_combat_keydown(self, key: int) -> None:
        if not self.combat:
            self.state = GameState.PLAYING
            return
        if key in [pygame.K_a, pygame.K_RETURN, pygame.K_SPACE]:
            self.resolve_combat_result(self.combat.attack())
        elif key == pygame.K_d:
            self.resolve_combat_result(self.combat.defend())
        elif key == pygame.K_f:
            self.resolve_combat_result(self.combat.flee())
        elif key == pygame.K_i:
            self.open_inventory(GameState.COMBAT)
        elif key == pygame.K_x:
            self.resolve_combat_result(self.combat.inspect(), save=False)
        elif key == pygame.K_ESCAPE:
            self.combat_log.add("Escaping menus is allowed. Escaping consequences is currently in beta.")

    def resolve_combat_result(self, result, save: bool = True) -> None:
        for message in result.messages:
            self.combat_log.add(message)
            self.log.add(message)
        for message in self.announcer.after_combat_messages(result.messages):
            self.combat_log.add(message)
            self.log.add(message)
        if result.defeat:
            if self.floor and self.player:
                recap = self.lore_manager.generate_death_recap(self.floor, self.player, cause="combat defeat")
                self.log.add(recap)
                self.combat_log.add(recap)
            self.log.add(self.announcer.line("DEATH"))
            self.save_current_state()
            self.state = GameState.DEATH
            return
        if result.victory:
            self.finish_room_after_combat(cleared=True)
            return
        if result.fled:
            self.finish_room_after_combat(cleared=False)
            return
        if save:
            self.save_current_state()

    def finish_room_after_combat(self, cleared: bool) -> None:
        if not self.floor or not self.player:
            self.state = GameState.PLAYING
            return
        room = self.floor.rooms[self.player.current_room_id]
        if cleared:
            room.cleared = True
            self.player.rooms_cleared += 1
            defeated_xp = 0
            if self.combat:
                defeated_xp = sum(enemy.xp for enemy in self.combat.enemies)
            credit_reward = self.calculate_credit_reward(defeated_xp, room.room_type)
            self.player.credits += credit_reward
            self.log.add(f"Credits awarded: {credit_reward}. Balance: {self.player.credits}.")
            if room.room_type == "Boss Room":
                self.log.add(f"Boss defeated: {self.floor.boss['name']}. The exit unlocks with a noise like legal approval.")
                if self.floor.boss.get("id") not in self.player.defeated_bosses:
                    self.player.defeated_bosses.append(self.floor.boss.get("id", self.floor.boss.get("name", "boss")))
                self.log.add(self.announcer.line("VICTORY"))
                recap = self.lore_manager.generate_victory_recap(self.floor, self.player)
                self.log.add(recap)
                self.prepare_floor_complete_summary()
            else:
                self.log.add(self.announcer.line("ROOM_CLEAR"))
        else:
            self.log.add("You stumble back into exploration mode. The room remains uncleared.")
        self.combat = None
        self.save_current_state()
        if cleared and room.room_type == "Boss Room":
            self.state = GameState.FLOOR_COMPLETE
        else:
            self.state = GameState.PLAYING

    def open_inventory(self, previous_state: str) -> None:
        if not self.player:
            return
        self.previous_state_before_inventory = previous_state
        self.player.inventory = sort_inventory(self.player.inventory)
        if self.player.inventory:
            self.inventory_selection = max(0, min(self.inventory_selection, len(self.player.inventory) - 1))
        else:
            self.inventory_selection = 0
        self.state = GameState.INVENTORY

    def handle_inventory_keydown(self, key: int) -> None:
        if not self.player:
            self.state = GameState.PLAYING
            return
        if key in [pygame.K_ESCAPE, pygame.K_i]:
            self.state = self.previous_state_before_inventory
            return
        if not self.player.inventory:
            if key in [pygame.K_RETURN, pygame.K_SPACE]:
                self.log.add("Inventory empty. Even the moths filed a transfer request.")
            return
        if key in [pygame.K_w, pygame.K_UP]:
            self.inventory_selection = (self.inventory_selection - 1) % len(self.player.inventory)
        elif key in [pygame.K_s, pygame.K_DOWN]:
            self.inventory_selection = (self.inventory_selection + 1) % len(self.player.inventory)
        elif key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_e]:
            selected_item = self.player.inventory[self.inventory_selection]
            selected_effect = str(selected_item.get("effect", "")).lower()

            if self.previous_state_before_inventory == GameState.COMBAT and selected_effect == "combat_damage":
                if not self.combat:
                    self.log.add("No active combat target. The item remains unused.")
                    self.state = GameState.PLAYING
                    return

                used_item = self.player.inventory.pop(self.inventory_selection)
                combat_result = self.combat.use_combat_item(used_item)
                self.player.inventory = sort_inventory(self.player.inventory)
                if self.player.inventory:
                    self.inventory_selection = min(self.inventory_selection, len(self.player.inventory) - 1)
                else:
                    self.inventory_selection = 0
                self.state = GameState.COMBAT
                self.resolve_combat_result(combat_result)
                return

            result = InventoryManager.use_or_equip(self.player, self.inventory_selection)
            for message in result.messages:
                self.log.add(message)
                if self.previous_state_before_inventory == GameState.COMBAT:
                    self.combat_log.add(message)
            if result.success:
                if self.player.inventory:
                    self.player.inventory = sort_inventory(self.player.inventory)
                    self.inventory_selection = min(self.inventory_selection, len(self.player.inventory) - 1)
                else:
                    self.inventory_selection = 0
                self.save_current_state()
            if result.item_consumed and self.previous_state_before_inventory == GameState.COMBAT:
                self.state = GameState.COMBAT

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.state == GameState.MAIN_MENU:
            for button in self.menu_buttons:
                if button.rect.collidepoint(pos):
                    self.handle_menu_action(button.action)
                    return
        elif self.state == GameState.CLASS_SELECT:
            for i, template in enumerate(self.class_templates[:8]):
                rect = pygame.Rect(96, 158 + i * 64, 470, 54)
                if rect.collidepoint(pos):
                    self.selected_class_index = i
                    self.start_new_game(i)
                    return
        elif self.state == GameState.LOAD_GAME:
            for button in self.load_buttons:
                if button.rect.collidepoint(pos):
                    self.handle_load_action(button.action)
                    return
        elif self.state == GameState.PLAYING:
            for room_id, rect in self.room_click_targets.items():
                if rect.collidepoint(pos):
                    self.enter_room(room_id)
                    return
        elif self.state == GameState.SHOP:
            self.handle_shop_click(pos)

    def update(self, dt: int) -> None:
        pass

    def draw(self) -> None:
        self.apply_ui_theme()
        self.screen.fill(COLORS["bg"])
        if self.state == GameState.MAIN_MENU:
            self.draw_main_menu()
        elif self.state == GameState.LOAD_GAME:
            self.draw_load_game()
        elif self.state == GameState.CLASS_SELECT:
            self.draw_class_select()
        elif self.state == GameState.SETTINGS:
            self.draw_settings()
        elif self.state == GameState.FLOOR_INTRO:
            self.draw_floor_intro()
        elif self.state == GameState.OLLAMA_GENERATION:
            self.draw_ollama_generation()
        elif self.state == GameState.PLAYING:
            self.draw_playing()
        elif self.state == GameState.COMBAT:
            self.draw_combat()
        elif self.state == GameState.DEATH:
            self.draw_death()
        elif self.state == GameState.INVENTORY:
            self.draw_inventory()
        elif self.state == GameState.SHOP:
            self.draw_shop()
        elif self.state == GameState.LOOT_REVEAL:
            self.draw_loot_reveal()
        elif self.state == GameState.FLOOR_COMPLETE:
            self.draw_floor_complete()
        elif self.state == GameState.RUN_SUMMARY:
            self.draw_run_summary()
        pygame.display.flip()

    def _build_main_menu(self) -> None:
        cx = SCREEN_WIDTH // 2
        top = 280
        specs = [
            ("New Game", "new_game"),
            ("Load Game", "load_game"),
            ("Settings", "settings"),
            ("Run Summary", "run_summary"),
            ("Quit", "quit"),
        ]
        self.menu_buttons = [Button(pygame.Rect(cx - 150, top + i * 60, 300, 48), label, action) for i, (label, action) in enumerate(specs)]

    def handle_menu_action(self, action: str) -> None:
        if action == "new_game":
            self.class_templates = Player.load_class_templates()
            self.selected_class_index = 0
            self.state = GameState.CLASS_SELECT
        elif action == "load_game":
            self.build_load_menu()
            self.state = GameState.LOAD_GAME
        elif action == "settings":
            self.apply_run_settings_to_ollama()
            self.detected_models = self.ollama_client.list_models()
            self.state = GameState.SETTINGS
        elif action == "run_summary":
            self.run_summary_reason = "Current run snapshot"
            self.state = GameState.RUN_SUMMARY
        elif action == "quit":
            self.running = False

    def start_new_game(self, class_index: int | None = None) -> None:
        seed = new_seed()
        if class_index is None:
            class_index = self.selected_class_index
        class_index = max(0, min(class_index, len(self.class_templates) - 1)) if self.class_templates else 0
        template = self.class_templates[class_index] if self.class_templates else {}
        player = Player.from_class_template(template, self.floor_generator.items)
        floor = self.floor_generator.generate_floor(seed, 1)
        self.run_data = self.save_system.create_run_data(seed, player, floor)
        self.apply_difficulty_to_floor(floor)
        self.apply_run_settings_to_ollama()
        self.player = player
        self.floor = floor
        self.generate_lore_for_current_floor()
        self.save_system.save_run(self.run_data)
        self.log = TextLog()
        self.combat_log = TextLog(max_lines=80)
        self.log.add(f"New run created with seed {seed}.")
        self.announcer = Announcer(seed)
        self.log.add(f"Phase 8 polished prototype online. Class selected: {player.player_class}.")
        self.state = GameState.FLOOR_INTRO

    def build_load_menu(self) -> None:
        paths = self.save_system.list_saves()
        self.selected_save_paths = paths[:8]
        self.load_buttons = []
        y = 170
        for i, path in enumerate(self.selected_save_paths):
            self.load_buttons.append(Button(pygame.Rect(320, y + i * 58, 640, 44), path.stem, f"load:{i}"))
        self.load_buttons.append(Button(pygame.Rect(320, 650, 220, 44), "Back", "back"))

    def handle_load_action(self, action: str) -> None:
        if action == "back":
            self._build_main_menu()
            self.state = GameState.MAIN_MENU
            return
        if action.startswith("load:"):
            idx = int(action.split(":", 1)[1])
            if idx < len(self.selected_save_paths):
                self.load_game(self.selected_save_paths[idx])

    def load_game(self, path: Path) -> None:
        self.run_data = self.save_system.load_run(path)
        self.player = Player.from_dict(self.run_data["player"])
        current_floor = str(self.run_data["current_floor"])
        self.apply_run_settings_to_ollama()
        self.floor = Floor.from_dict(self.run_data["floors"][current_floor])
        self.log = TextLog()
        self.combat_log = TextLog(max_lines=80)
        self.announcer = Announcer(self.run_data["seed"])
        self.log.add(f"Loaded run seed {self.run_data['seed']} on floor {current_floor}.")
        if not self.floor.lore.get("generated_once"):
            self.generate_lore_for_current_floor()
            self.save_current_state()
        self.state = GameState.PLAYING

    def move_to_connected_room(self, connection_index: int) -> None:
        """Legacy slot movement fallback.

        The UI now prefers directional movement, but this remains for older saves
        or future controller bindings that may still use connection indexes.
        """
        if not self.player or not self.floor:
            return
        current = self.floor.rooms[self.player.current_room_id]
        if connection_index >= len(current.connections):
            self.log.add("No connected room in that slot.")
            self.log.add("Available exits: " + self.available_exit_summary())
            return
        target_id = current.connections[connection_index]
        self.enter_room(target_id)

    def directional_exits(self) -> dict[str, str]:
        """Return best connected room for north/east/south/west based on map position."""
        if not self.player or not self.floor:
            return {}
        current = self.floor.rooms[self.player.current_room_id]
        candidates: dict[str, list[tuple[int, str]]] = {"north": [], "east": [], "south": [], "west": []}
        for room_id in current.connections:
            other = self.floor.rooms.get(room_id)
            if other is None:
                continue
            dx = int(other.x) - int(current.x)
            dy = int(other.y) - int(current.y)
            distance = abs(dx) + abs(dy)
            if distance == 0:
                continue
            # Prefer the dominant axis, but still support slightly diagonal generated links.
            if abs(dx) >= abs(dy):
                if dx > 0:
                    candidates["east"].append((distance, room_id))
                elif dx < 0:
                    candidates["west"].append((distance, room_id))
            if abs(dy) >= abs(dx):
                if dy > 0:
                    candidates["south"].append((distance, room_id))
                elif dy < 0:
                    candidates["north"].append((distance, room_id))
        exits: dict[str, str] = {}
        for direction, options in candidates.items():
            if options:
                options.sort(key=lambda item: item[0])
                exits[direction] = options[0][1]
        return exits

    def available_exit_summary(self) -> str:
        if not self.floor:
            return "none"
        exits = self.directional_exits()
        labels = []
        for direction in ["north", "east", "south", "west"]:
            room_id = exits.get(direction)
            if room_id and room_id in self.floor.rooms:
                room = self.floor.rooms[room_id]
                labels.append(f"{direction.title()} -> {room.room_type}")
        return ", ".join(labels) if labels else "none"

    def move_by_direction(self, direction: str) -> None:
        exits = self.directional_exits()
        target_id = exits.get(direction)
        if not target_id:
            self.log.add(f"No exit {direction.title()}. Available exits: {self.available_exit_summary()}.")
            return
        self.enter_room(target_id)

    def enter_room(self, room_id: str) -> None:
        if not self.player or not self.floor or not self.run_data:
            return
        if room_id not in self.floor.rooms:
            self.log.add("That room does not exist. The map department denies everything.")
            return
        self.player.current_room_id = room_id
        room = self.floor.rooms[room_id]
        first_visit = not room.visited
        room.visited = True
        self.log.add(f"Entered {room.title} [{room.room_type}].")
        if first_visit:
            self.log.add(room.description)
            if room.room_type == "Combat" and room.enemies:
                self.log.add("Hostile presence detected. Press Enter to start combat.")
            elif room.room_type == "Mini-Boss":
                self.log.add("Mini-boss signal detected. Press Enter to convert confidence into data.")
            elif room.room_type == "NPC Event":
                self.log.add("Event detected. Press Enter to interact with the probably-not-a-trap person.")
            elif room.room_type == "Shop":
                self.log.add("Shop kiosk detected. Press Enter to browse the free prototype sample.")
            elif room.room_type == "Boss Room":
                self.log.add(f"Boss signal detected: {self.floor.boss['name']}. Press Enter if you enjoy terrible decisions.")
        self.save_current_state()

    def interact_current_room(self) -> None:
        if not self.player or not self.floor:
            return
        room = self.floor.rooms[self.player.current_room_id]
        if room.cleared:
            self.log.add("This room is already cleared. The audience boos your thoroughness.")
            return
        if room.room_type == "Rest":
            self.player.heal_full()
            room.cleared = True
            self.log.add("You rest. HP restored. The vending machine watches without blinking.")
            self.log.add(self.announcer.line("REST"))
        elif room.room_type in ["Loot", "Sponsor Crate"]:
            if room.loot:
                self.open_loot_reveal(room.loot, source=room.room_type)
                return
            room.cleared = True
            self.log.add("Collected: nothing. The crate contains only brand disappointment.")
        elif room.room_type == "Trap":
            self.resolve_trap(room)
        elif room.room_type in ["Combat", "Mini-Boss"]:
            self.start_combat(room.enemies, is_boss=False)
            return
        elif room.room_type == "NPC Event":
            room.cleared = True
            event = room.event or {}
            self.log.add(event.get("chosen_text", "A suspiciously helpful stranger gives you advice that smells like onions."))
            if room.loot:
                for item in room.loot[:1]:
                    self.log.add(self.announcer.loot_reveal(item))
                self.player.items_found += len(room.loot[:1])
                for message in InventoryManager.add_items(self.player, room.loot[:1]):
                    self.log.add(message)
                room.loot = []
            else:
                healed = self.player.heal(5)
                self.log.add(f"You recover {healed} HP from questionable encouragement.")
        elif room.room_type == "Shop":
            event = room.event or {}
            self.log.add(event.get("chosen_text", "A wall kiosk dispenses goods and judgment."))
            self.open_shop()
            return
        elif room.room_type == "Boss Gate":
            room.cleared = True
            self.log.add("Boss gate unlocked. The door makes an approvingly expensive clunk.")
        elif room.room_type == "Boss Room":
            self.start_combat([self.floor.boss], is_boss=True)
            return
        elif room.room_type == "Exit":
            self.prepare_floor_complete_summary()
            self.state = GameState.FLOOR_COMPLETE
            return
        else:
            room.cleared = True
            self.log.add("Room marked clear.")
        self.save_current_state()

    def open_loot_reveal(self, items: list[dict], source: str = "Loot") -> None:
        if not self.player or not self.floor:
            return
        self.loot_reveal_items = [dict(item) for item in items]
        self.loot_reveal_index = 0
        room = self.floor.rooms[self.player.current_room_id]
        room.cleared = True
        room.loot = []
        self.player.items_found += len(self.loot_reveal_items)
        for message in InventoryManager.add_items(self.player, self.loot_reveal_items):
            self.log.add(message)
        if source == "Sponsor Crate":
            self.log.add(self.announcer.line("SPONSOR_BREAK"))
            if self.floor.lore.get("sponsor_message"):
                self.log.add(self.floor.lore["sponsor_message"])
        self.save_current_state()
        self.state = GameState.LOOT_REVEAL

    def handle_loot_reveal_keydown(self, key: int) -> None:
        if key not in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE]:
            return
        self.loot_reveal_index += 1
        if self.loot_reveal_index >= len(self.loot_reveal_items):
            self.loot_reveal_items = []
            self.loot_reveal_index = 0
            self.state = GameState.PLAYING

    def open_shop(self) -> None:
        if not self.player or not self.floor:
            return
        room = self.floor.rooms[self.player.current_room_id]
        self.shop_selection = 0
        if not room.loot:
            self.log.add("The shop is sold out, which somehow makes it smug.")
            room.cleared = True
            self.save_current_state()
            return
        self.state = GameState.SHOP

    def current_shop_offers(self) -> list[dict]:
        if not self.player or not self.floor:
            return []
        room = self.floor.rooms[self.player.current_room_id]
        return sorted(room.loot, key=item_price)

    def buy_selected_shop_item(self) -> None:
        if not self.player or not self.floor:
            return
        room = self.floor.rooms[self.player.current_room_id]
        offers = self.current_shop_offers()
        if not offers:
            self.log.add("The kiosk is empty. It still asks for a tip.")
            room.cleared = True
            self.save_current_state()
            self.state = GameState.PLAYING
            return
        self.shop_selection = max(0, min(self.shop_selection, len(offers) - 1))
        item = offers[self.shop_selection]
        price = item_price(item)
        if self.player.credits < price:
            self.log.add(f"Cannot afford {item.get('name', 'item')}. Need {price} credits; have {self.player.credits}.")
            return
        self.player.credits -= price
        # Remove the matching item from the room's unsorted offer list.
        for idx, candidate in enumerate(room.loot):
            if candidate.get("id") == item.get("id"):
                room.loot.pop(idx)
                break
        self.player.items_found += 1
        for message in InventoryManager.add_items(self.player, [item]):
            self.log.add(message)
        self.log.add(f"Purchased {item.get('name', 'item')} for {price} credits. Balance: {self.player.credits}.")
        if not room.loot:
            room.cleared = True
            self.log.add("Shop sold out. The kiosk thanks you for participating in commerce.")
        self.shop_selection = min(self.shop_selection, max(0, len(self.current_shop_offers()) - 1))
        self.save_current_state()

    def handle_shop_keydown(self, key: int) -> None:
        offers = self.current_shop_offers()
        if key in [pygame.K_ESCAPE, pygame.K_i]:
            self.state = GameState.PLAYING
            return
        if not offers:
            self.state = GameState.PLAYING
            return
        if key in [pygame.K_w, pygame.K_UP]:
            self.shop_selection = (self.shop_selection - 1) % len(offers)
        elif key in [pygame.K_s, pygame.K_DOWN]:
            self.shop_selection = (self.shop_selection + 1) % len(offers)
        elif key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_e]:
            self.buy_selected_shop_item()

    def handle_shop_click(self, pos: tuple[int, int]) -> None:
        offers = self.current_shop_offers()
        if not offers:
            return
        for i, _item in enumerate(offers[:8]):
            row = pygame.Rect(80, 180 + i * 48, 660, 38)
            if row.collidepoint(pos):
                self.shop_selection = i
                self.buy_selected_shop_item()
                return

    def prepare_floor_complete_summary(self) -> None:
        if not self.player or not self.floor or not self.run_data:
            return
        rooms_total = len(self.floor.rooms)
        rooms_cleared = sum(1 for room in self.floor.rooms.values() if room.cleared)
        self.floor_completion_summary = {
            "floor": self.floor.floor_number,
            "theme": self.floor.theme.get("name", "Unknown Floor"),
            "boss": self.floor.boss.get("name", "Unknown Boss"),
            "rooms_cleared": rooms_cleared,
            "rooms_total": rooms_total,
            "items_found": self.player.items_found,
            "credits": self.player.credits,
            "next_floor": int(self.floor.floor_number) + 1,
        }
        self.save_current_state()

    def handle_floor_complete_keydown(self, key: int) -> None:
        if key in [pygame.K_RETURN, pygame.K_SPACE]:
            self.advance_floor()
        elif key == pygame.K_ESCAPE:
            self.state = GameState.PLAYING

    def draw_hp_bar(self, rect: pygame.Rect, current: int, maximum: int, fill_color: tuple[int, int, int]) -> None:
        maximum = max(1, int(maximum))
        current = max(0, min(int(current), maximum))
        pygame.draw.rect(self.screen, COLORS["bg"], rect, border_radius=5)
        inner = rect.inflate(-4, -4)
        if inner.width > 0 and inner.height > 0:
            fill_width = int(inner.width * (current / maximum))
            fill = pygame.Rect(inner.x, inner.y, fill_width, inner.height)
            if fill_width > 0:
                pygame.draw.rect(self.screen, fill_color, fill, border_radius=4)
        pygame.draw.rect(self.screen, COLORS["panel_light"], rect, width=2, border_radius=5)

    def start_combat(self, enemies: list[dict], is_boss: bool = False) -> None:
        if not self.player or not self.floor or not self.run_data:
            return
        room = self.floor.rooms[self.player.current_room_id]
        if not enemies:
            room.cleared = True
            self.log.add("The room was supposed to contain violence, but scheduling lost the creature.")
            self.save_current_state()
            return
        boss_intro = self.floor.lore.get("boss_intro", "") if is_boss else ""
        if boss_intro:
            self.log.add(boss_intro)
        self.combat = CombatEncounter(
            self.player,
            enemies,
            int(self.run_data["seed"]),
            int(self.floor.floor_number),
            room.id,
            is_boss=is_boss,
        )
        self.combat_log = TextLog(max_lines=80)
        if boss_intro:
            self.combat_log.add(boss_intro)
        opening_line = self.announcer.combat_start(is_boss=is_boss)
        self.combat_log.add(opening_line)
        self.log.add(opening_line)
        for message in self.combat.messages:
            self.combat_log.add(message)
            self.log.add(message)
        self.state = GameState.COMBAT

    def resolve_trap(self, room) -> None:
        if not self.player:
            return
        trap = room.trap or {"name": "Unknown Trap", "difficulty": 10}
        roll = pygame.time.get_ticks() % 20 + 1 + self.player.luck
        difficulty = int(trap.get("difficulty", 10))
        room.cleared = True
        if roll >= difficulty:
            self.log.add(f"Trap avoided: {trap.get('name', 'Unknown Trap')}. Roll {roll} vs difficulty {difficulty}.")
            self.log.add(self.announcer.line("TRAP_AVOIDED"))
        else:
            damage = max(1, difficulty - roll + 2)
            self.player.hp = max(0, self.player.hp - damage)
            self.log.add(f"Trap triggered: {trap.get('name', 'Unknown Trap')}. Took {damage} damage.")
            self.log.add(self.announcer.line("TRAP_TRIGGERED"))
            if self.player.hp <= 0:
                recap = self.lore_manager.generate_death_recap(self.floor, self.player, cause=f"trap: {trap.get('name', 'Unknown Trap')}")
                self.log.add(recap)
                self.log.add(self.announcer.line("DEATH"))
                self.save_current_state()
                self.state = GameState.DEATH

    def advance_floor(self) -> None:
        if not self.run_data or not self.player:
            return
        next_floor_number = int(self.run_data["current_floor"]) + 1
        seed = int(self.run_data["seed"])
        if str(next_floor_number) in self.run_data.get("floors", {}):
            self.floor = Floor.from_dict(self.run_data["floors"][str(next_floor_number)])
        else:
            self.floor = self.floor_generator.generate_floor(seed, next_floor_number)
            self.apply_difficulty_to_floor(self.floor)
            self.generate_lore_for_current_floor()
        self.player.current_room_id = "room_0"
        self.run_data["current_floor"] = next_floor_number
        self.floor_completion_summary = {}
        self.pending_floor_number = None
        self.save_current_state()
        self.log.add(f"Advanced to Floor {next_floor_number}.")
        self.state = GameState.FLOOR_INTRO

    def save_current_state(self) -> None:
        if not self.run_data or not self.player or not self.floor:
            return
        self.save_system.serialize_player_into_run(self.run_data, self.player)
        self.save_system.serialize_floor_into_run(self.run_data, self.floor)
        self.save_system.save_run(self.run_data)


    def apply_run_settings_to_ollama(self) -> None:
        settings = dict(DEFAULT_SETTINGS) if 'DEFAULT_SETTINGS' in globals() else {}
        if self.run_data:
            settings.update(self.run_data.get("settings", {}))
        self.ollama_client.enabled = bool(settings.get("ollama_enabled", True))
        self.ollama_client.base_url = str(settings.get("ollama_base_url", self.ollama_client.base_url)).rstrip("/")
        self.ollama_client.model = str(settings.get("ollama_model", self.ollama_client.model))
        self.ollama_client.timeout = int(settings.get("text_generation_timeout", settings.get("ollama_timeout", self.ollama_client.timeout)) or 45)

    def show_generation_progress(self, message: str) -> None:
        self.state = GameState.OLLAMA_GENERATION
        self.ollama_generation_lines.append(message)
        self.ollama_generation_lines = self.ollama_generation_lines[-9:]
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
        self.draw()
        pygame.display.flip()
        time.sleep(0.05)

    def generate_lore_for_current_floor(self) -> None:
        if not self.floor or not self.run_data:
            return
        self.apply_run_settings_to_ollama()
        self.ollama_generation_lines = []
        self.show_generation_progress(f"Generating Floor {self.floor.floor_number} broadcast package...")
        self.lore_manager.generate_floor_package(
            self.floor,
            self.floor_generator.sponsors,
            progress=self.show_generation_progress,
        )
        if self.ollama_client.last_error:
            self.show_generation_progress("AI broadcast failed. Loading emergency corporate-approved filler...")
        else:
            self.show_generation_progress("Broadcast package complete.")
        self.save_system.serialize_floor_into_run(self.run_data, self.floor)
        self.save_system.save_run(self.run_data)


    def current_settings(self) -> dict:
        settings = dict(DEFAULT_SETTINGS)
        if self.run_data:
            settings.update(self.run_data.get("settings", {}))
        return settings

    def write_settings(self, settings: dict) -> None:
        if self.run_data is not None:
            self.run_data["settings"] = settings
            self.save_system.save_run(self.run_data)
        self.apply_run_settings_to_ollama()
        self.audio.set_volumes(settings.get("music_volume", 0.5), settings.get("sound_volume", 0.7))

    def settings_rows(self) -> list[tuple[str, str]]:
        settings = self.current_settings()
        return [
            ("difficulty", str(settings.get("difficulty", "normal"))),
            ("ui_theme", str(settings.get("ui_theme", "hazard"))),
            ("ollama_enabled", str(settings.get("ollama_enabled", True))),
            ("ollama_model", str(settings.get("ollama_model", self.ollama_client.model))),
            ("text_generation_timeout", str(settings.get("text_generation_timeout", self.ollama_client.timeout))),
            ("music_volume", f"{float(settings.get('music_volume', 0.5)):.1f}"),
            ("sound_volume", f"{float(settings.get('sound_volume', 0.7)):.1f}"),
            ("fullscreen", str(settings.get("fullscreen", False))),
            ("autosave", str(settings.get("autosave", True))),
        ]

    def handle_settings_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._build_main_menu()
            self.state = GameState.MAIN_MENU
            return
        rows = self.settings_rows()
        if key in [pygame.K_w, pygame.K_UP]:
            self.selected_settings_index = (self.selected_settings_index - 1) % len(rows)
        elif key in [pygame.K_s, pygame.K_DOWN]:
            self.selected_settings_index = (self.selected_settings_index + 1) % len(rows)
        elif key in [pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT, pygame.K_RETURN, pygame.K_SPACE]:
            self.cycle_selected_setting(reverse=key in [pygame.K_a, pygame.K_LEFT])

    def cycle_selected_setting(self, reverse: bool = False) -> None:
        settings = self.current_settings()
        key = self.settings_rows()[self.selected_settings_index][0]
        step = -1 if reverse else 1
        if key == "difficulty":
            choices = list(DIFFICULTY_SETTINGS.keys())
            current = str(settings.get(key, "normal"))
            settings[key] = choices[(choices.index(current) + step) % len(choices)] if current in choices else "normal"
        elif key == "ui_theme":
            choices = list(THEMES.keys())
            current = str(settings.get(key, "hazard"))
            settings[key] = choices[(choices.index(current) + step) % len(choices)] if current in choices else "hazard"
        elif key in {"ollama_enabled", "fullscreen", "autosave"}:
            settings[key] = not bool(settings.get(key, False))
        elif key == "text_generation_timeout":
            values = [10, 20, 45, 60, 90]
            current = int(settings.get(key, 45) or 45)
            settings[key] = values[(values.index(current) + step) % len(values)] if current in values else 45
        elif key in {"music_volume", "sound_volume"}:
            current = float(settings.get(key, 0.5 if key == "music_volume" else 0.7))
            settings[key] = round(max(0.0, min(1.0, current + step * 0.1)), 1)
        elif key == "ollama_model" and self.detected_models:
            current = str(settings.get(key, self.ollama_client.model))
            idx = self.detected_models.index(current) if current in self.detected_models else -1
            settings[key] = self.detected_models[(idx + step) % len(self.detected_models)]
        self.write_settings(settings)

    def apply_difficulty_to_floor(self, floor: Floor) -> None:
        settings = self.current_settings()
        difficulty = str(settings.get("difficulty", "normal"))
        modifiers = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS["normal"])
        if floor.lore.get("difficulty_applied") == difficulty:
            return
        hp_mult = float(modifiers["enemy_hp"])
        attack_mult = float(modifiers["enemy_attack"])
        trap_bonus = int(modifiers["trap_bonus"])
        for room in floor.rooms.values():
            for enemy in room.enemies:
                enemy["hp"] = max(1, int(enemy.get("hp", 1) * hp_mult))
                enemy["attack"] = max(1, int(enemy.get("attack", 1) * attack_mult))
            if room.trap:
                room.trap["difficulty"] = max(1, int(room.trap.get("difficulty", 10)) + trap_bonus)
        floor.boss["hp"] = max(1, int(floor.boss.get("hp", 1) * hp_mult))
        floor.boss["attack"] = max(1, int(floor.boss.get("attack", 1) * attack_mult))
        floor.lore["difficulty_applied"] = difficulty

    def calculate_credit_reward(self, xp_value: int, room_type: str) -> int:
        settings = self.current_settings()
        difficulty = str(settings.get("difficulty", "normal"))
        bonus = int(DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS["normal"]).get("credit_bonus", 0))
        base = 6 if room_type != "Boss Room" else 25
        return max(1, base + xp_value // 3 + bonus)

    def draw_ollama_generation(self) -> None:
        draw_text(self.screen, self.big_font, "AI Broadcast Generation", 360, 80, COLORS["accent"])
        panel = pygame.Rect(190, 170, 900, 390)
        pygame.draw.rect(self.screen, COLORS["panel"], panel, border_radius=10)
        draw_text(self.screen, self.font, "Preparing local dungeon flavor package...", panel.x + 28, panel.y + 28, COLORS["text"])
        y = panel.y + 86
        lines = self.ollama_generation_lines or ["Waiting for generation task..."]
        for line in lines[-9:]:
            draw_text(self.screen, self.small_font, f"• {line}", panel.x + 42, y, COLORS["muted"])
            y += 34
        draw_text(self.screen, self.small_font, "If Ollama is offline or slow, fallback text will be saved instead.", panel.x + 28, panel.bottom - 44, COLORS["accent"])

    def draw_main_menu(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.assets.blit_scaled_ui(self.screen, "title_bg", pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # Subtle vignette for readability over illustrated backgrounds.
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 55))
        self.screen.blit(dim, (0, 0))

        logo_rect = pygame.Rect(330, 36, 620, 205)
        if not self.assets.blit_scaled_ui(self.screen, "logo", logo_rect):
            draw_text(self.screen, self.big_font, TITLE, 390, 98, COLORS["accent"])

        draw_text(self.screen, self.small_font, "Phase 8 Asset UI Patch", 525, 232, COLORS["muted"])

        # Dark backing plate keeps the menu readable and avoids overlap with the logo.
        menu_panel = pygame.Rect(440, 260, 400, 350)
        overlay = pygame.Surface((menu_panel.width, menu_panel.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 172))
        self.screen.blit(overlay, menu_panel)
        pygame.draw.rect(self.screen, COLORS["accent"], menu_panel, width=2, border_radius=10)

        draw_text(self.screen, self.small_font, "Original dark-comedy roguelike framework. No copyrighted lore included.", 322, 660, COLORS["muted"])
        for button in self.menu_buttons:
            button.draw(self.screen, self.font, mouse)

    def handle_class_select_keydown(self, key: int) -> None:
        if key in [pygame.K_ESCAPE]:
            self._build_main_menu()
            self.state = GameState.MAIN_MENU
            return
        if not self.class_templates:
            self.start_new_game(0)
            return
        if key in [pygame.K_w, pygame.K_UP]:
            self.selected_class_index = (self.selected_class_index - 1) % len(self.class_templates)
        elif key in [pygame.K_s, pygame.K_DOWN]:
            self.selected_class_index = (self.selected_class_index + 1) % len(self.class_templates)
        elif key in [pygame.K_RETURN, pygame.K_SPACE]:
            self.start_new_game(self.selected_class_index)

    def draw_class_select(self) -> None:
        draw_text(self.screen, self.big_font, "Choose Your Crawler", 360, 50, COLORS["accent"])
        draw_text(self.screen, self.small_font, "Pick a class. Portraits, icons, stats, and starter gear are now separated cleanly.", 260, 103, COLORS["muted"])

        list_rect = pygame.Rect(70, 140, 500, 505)
        detail_rect = pygame.Rect(600, 140, 610, 505)
        pygame.draw.rect(self.screen, COLORS["panel"], list_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["panel"], detail_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["panel_light"], list_rect, width=2, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["panel_light"], detail_rect, width=2, border_radius=10)

        y = list_rect.y + 12
        mouse = pygame.mouse.get_pos()
        for i, template in enumerate(self.class_templates[:8]):
            row = pygame.Rect(list_rect.x + 16, y, list_rect.width - 32, 56)
            selected = i == self.selected_class_index
            if selected or row.collidepoint(mouse):
                pygame.draw.rect(self.screen, COLORS["button_hover"], row, border_radius=6)

            class_id = str(template.get("id", ""))
            icon = self.assets.class_icon(class_id)
            text_x = row.x + 16
            if icon:
                self.screen.blit(icon, (row.x + 8, row.y + 2))
                text_x = row.x + 72

            draw_text(self.screen, self.font, template.get("name", "Crawler"), text_x, row.y + 7, COLORS["accent"] if selected else COLORS["text"])
            stat_line = f"HP {template.get('hp')}   ATK {template.get('attack')}   DEF {template.get('defense')}   LUCK {template.get('luck')}"
            draw_text(self.screen, self.small_font, stat_line, text_x, row.y + 33, COLORS["muted"])
            y += 64

        if self.class_templates:
            template = self.class_templates[self.selected_class_index]
            class_id = str(template.get("id", ""))
            portrait = self.assets.class_portrait(class_id)

            portrait_rect = pygame.Rect(detail_rect.right - 304, detail_rect.y + 22, 276, 276)
            portrait_back = portrait_rect.inflate(12, 12)
            pygame.draw.rect(self.screen, COLORS["bg"], portrait_back, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["accent"], portrait_back, width=2, border_radius=8)
            if portrait:
                self.screen.blit(portrait, portrait_rect)
            else:
                draw_text(self.screen, self.small_font, "No portrait found", portrait_rect.x + 68, portrait_rect.y + 128, COLORS["muted"])

            left_x = detail_rect.x + 24
            right_limit = portrait_back.x - 24
            text_width = max(220, right_limit - left_x)

            y = detail_rect.y + 24
            draw_text(self.screen, self.font, template.get("name", "Crawler"), left_x, y, COLORS["accent"])
            y += 40
            stats = f"HP {template.get('hp')}  ATK {template.get('attack')}"
            draw_text(self.screen, self.font, stats, left_x, y, COLORS["text"])
            y += 30
            stats2 = f"DEF {template.get('defense')}  LUCK {template.get('luck')}"
            draw_text(self.screen, self.font, stats2, left_x, y, COLORS["text"])
            y += 42
            draw_text(self.screen, self.small_font, "Description", left_x, y, COLORS["accent"])
            y += 26
            draw_wrapped_text(self.screen, self.small_font, template.get("description", ""), pygame.Rect(left_x, y, text_width, 92), COLORS["text"])

            lower_y = detail_rect.y + 322
            draw_text(self.screen, self.small_font, "Special", left_x, lower_y, COLORS["accent"])
            lower_y += 26
            draw_wrapped_text(self.screen, self.small_font, template.get("special", ""), pygame.Rect(left_x, lower_y, detail_rect.width - 48, 62), COLORS["muted"])
            lower_y += 78
            draw_text(self.screen, self.small_font, "Starting Items", left_x, lower_y, COLORS["accent"])
            lower_y += 26
            item_names = []
            item_lookup = {item.get("id"): item.get("name") for item in self.floor_generator.items}
            for item_id in template.get("starting_items", []):
                item_names.append(item_lookup.get(item_id, item_id))
            draw_wrapped_text(self.screen, self.small_font, ", ".join(item_names) or "None", pygame.Rect(left_x, lower_y, detail_rect.width - 48, 62), COLORS["text"])

        draw_text(self.screen, self.font, "Up/Down: select | Enter/Space: start | Esc: back", 330, 680, COLORS["muted"])

    def draw_load_game(self) -> None:
        mouse = pygame.mouse.get_pos()
        draw_text(self.screen, self.big_font, "Load Game", 500, 70, COLORS["accent"])
        if not self.selected_save_paths:
            draw_text(self.screen, self.font, "No seed saves found yet.", 500, 280, COLORS["muted"])
        for button in self.load_buttons:
            button.draw(self.screen, self.font, mouse)

    def draw_settings(self) -> None:
        settings = self.current_settings()
        theme_key = str(settings.get("ui_theme", "hazard"))
        draw_text(self.screen, self.big_font, "Settings", 520, 55, COLORS["accent"])
        panel = pygame.Rect(180, 125, 920, 500)
        pygame.draw.rect(self.screen, COLORS["panel"], panel, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["panel_light"], panel, width=2, border_radius=10)
        draw_text(self.screen, self.font, "Phase 8 polish settings", panel.x + 28, panel.y + 24, COLORS["accent"])
        draw_text(self.screen, self.small_font, "Up/Down selects. Left/Right or Enter changes. Esc returns.", panel.x + 28, panel.y + 56, COLORS["muted"])
        rows = self.settings_rows()
        y = panel.y + 104
        for idx, (key, value) in enumerate(rows):
            row = pygame.Rect(panel.x + 28, y - 6, panel.width - 56, 34)
            if idx == self.selected_settings_index:
                pygame.draw.rect(self.screen, COLORS["button_hover"], row, border_radius=6)
            label = key.replace("_", " ").title()
            draw_text(self.screen, self.font, label, row.x + 12, y, COLORS["accent"] if idx == self.selected_settings_index else COLORS["text"])
            draw_text(self.screen, self.font, value, row.x + 410, y, COLORS["text"])
            y += 42
        detected = ", ".join(self.detected_models[:6]) if self.detected_models else "none detected; manual configured model remains allowed"
        info = [
            f"Detected Ollama models: {detected}",
            f"Current theme: {THEMES.get(theme_key, THEMES['hazard'])['name']}",
            "Difficulty applies when new floors are generated; existing generated floors keep saved values.",
            "Audio and sprite hooks are safe: missing asset files will not crash the game.",
        ]
        y = panel.bottom + 18
        for line in info:
            draw_text(self.screen, self.small_font, line, 210, y, COLORS["muted"])
            y += 24

    def draw_floor_intro(self) -> None:
        if not self.floor:
            return
        lore = self.floor.lore
        draw_text(self.screen, self.big_font, lore.get("title", "Floor Intro"), 90, 80, COLORS["accent"])
        body = "\n\n".join([
            lore.get("intro", "The broadcast begins."),
            lore.get("description", "The floor smells like danger and bad decisions."),
            "ANNOUNCER WARNING: " + lore.get("warning", "Try not to die."),
        ])
        draw_wrapped_text(self.screen, self.font, body, pygame.Rect(100, 170, 1080, 360), COLORS["text"])
        draw_text(self.screen, self.font, "Press Enter or Space to begin.", 430, 620, COLORS["muted"])

    def draw_playing(self) -> None:
        if not self.player or not self.floor or not self.run_data:
            return
        self.assets.blit_scaled_ui(self.screen, "gameplay_bg", pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        top = pygame.Rect(20, 12, 1240, 76)
        if not self.assets.blit_scaled_ui(self.screen, "top_bar", top):
            pygame.draw.rect(self.screen, COLORS["panel"], top, border_radius=8)
        top_text = f"Seed {self.run_data['seed']} | Floor {self.floor.floor_number}: {self.floor.theme['name']} | {self.player.name} HP {self.player.hp}/{self.player.max_hp}"
        draw_text(self.screen, self.font, top_text, 44, 39, COLORS["text"])
        credits_icon = self.assets.generic_icon("credits")
        if credits_icon:
            self.screen.blit(credits_icon, (1086, 28))
        draw_text(self.screen, self.font, f"{self.player.credits}", 1116, 39, COLORS["gold"])

        map_rect = pygame.Rect(20, 100, 760, 400)
        side_rect = pygame.Rect(800, 100, 460, 400)
        log_panel_rect = pygame.Rect(20, 520, 1240, 180)
        log_rect = pygame.Rect(46, 548, 1188, 130)

        pygame.draw.rect(self.screen, COLORS["panel"], map_rect, border_radius=8)
        if not self.assets.blit_scaled_ui(self.screen, "right_stats_panel", side_rect):
            pygame.draw.rect(self.screen, COLORS["panel"], side_rect, border_radius=8)
        if not self.assets.blit_scaled_ui(self.screen, "bottom_log_panel", log_panel_rect):
            pygame.draw.rect(self.screen, COLORS["panel"], log_panel_rect, border_radius=8)

        self.draw_room_map(map_rect)
        self.draw_side_panel(side_rect)
        self.log.draw(self.screen, self.small_font, log_rect)

    def draw_room_map(self, rect: pygame.Rect) -> None:
        if not self.player or not self.floor:
            return
        self.room_click_targets = {}
        draw_text(self.screen, self.font, "Floor Map", rect.x + 18, rect.y + 14, COLORS["accent"])
        draw_text(self.screen, self.small_font, "Click a highlighted connected room, or use W/A/S/D by map direction.", rect.x + 18, rect.y + 42, COLORS["muted"])

        origin_x = rect.x + 50
        origin_y = rect.y + 98
        scale_x = 68
        scale_y = 68
        current = self.floor.rooms[self.player.current_room_id]
        exits = self.directional_exits()
        connected_ids = set(current.connections)
        direction_for_room = {room_id: direction for direction, room_id in exits.items()}

        for room in self.floor.rooms.values():
            for other_id in room.connections:
                other = self.floor.rooms[other_id]
                start = (origin_x + room.x * scale_x + 29, origin_y + room.y * scale_y + 21)
                end = (origin_x + other.x * scale_x + 29, origin_y + other.y * scale_y + 21)
                width = 5 if room.id == current.id or other.id == current.id else 2
                color = COLORS["accent"] if room.id == current.id or other.id == current.id else COLORS["panel_light"]
                pygame.draw.line(self.screen, color, start, end, width)

        for room in self.floor.rooms.values():
            r = pygame.Rect(origin_x + room.x * scale_x, origin_y + room.y * scale_y, 58, 42)
            is_current = room.id == self.player.current_room_id
            is_connected = room.id in connected_ids
            if is_current:
                color = COLORS["room_current"]
            elif is_connected:
                color = COLORS["button_hover"]
            elif room.cleared:
                color = COLORS["room_cleared"]
            elif room.visited:
                color = COLORS["room"]
            else:
                color = COLORS["room_locked"]

            pygame.draw.rect(self.screen, color, r, border_radius=7)
            border_color = COLORS["accent"] if is_current or is_connected else COLORS["bg"]
            border_width = 3 if is_current or is_connected else 2
            pygame.draw.rect(self.screen, border_color, r, width=border_width, border_radius=7)

            if is_connected:
                self.room_click_targets[room.id] = r.inflate(10, 10)

            icon = self.assets.icon(room.room_type)
            if icon:
                self.screen.blit(icon, icon.get_rect(center=(r.centerx, r.centery - 6)))
                label_text = direction_for_room.get(room.id, room.room_type[:3]).upper()[:3] if is_connected else room.room_type[:3]
                label = self.small_font.render(label_text, True, COLORS["bg"] if is_current else COLORS["text"])
                self.screen.blit(label, label.get_rect(center=(r.centerx, r.centery + 12)))
            else:
                label_text = direction_for_room.get(room.id, room.room_type[:7]).upper()[:3] if is_connected else room.room_type[:7]
                label = self.small_font.render(label_text, True, COLORS["bg"] if is_current else COLORS["text"])
                self.screen.blit(label, label.get_rect(center=r.center))

        legend_y = rect.bottom - 34
        draw_text(self.screen, self.small_font, f"Exits: {self.available_exit_summary()}", rect.x + 18, legend_y, COLORS["accent"])

    def draw_side_panel(self, rect: pygame.Rect) -> None:
        if not self.player or not self.floor:
            return
        room = self.floor.rooms[self.player.current_room_id]
        draw_text(self.screen, self.font, room.title, rect.x + 18, rect.y + 18, COLORS["accent"])
        draw_text(self.screen, self.small_font, f"Type: {room.room_type} | Cleared: {room.cleared}", rect.x + 18, rect.y + 52, COLORS["muted"])
        draw_text(self.screen, self.small_font, f"Exits: {self.available_exit_summary()}", rect.x + 18, rect.y + 70, COLORS["accent"])
        class_key = getattr(self.player, "player_class_id", "") or str(getattr(self.player, "player_class", "")).lower().replace(" ", "_")
        class_icon = self.assets.class_icon(class_key)
        if class_icon:
            self.screen.blit(class_icon, (rect.right - 82, rect.y + 14))
        draw_wrapped_text(self.screen, self.small_font, room.description, pygame.Rect(rect.x + 18, rect.y + 96, rect.width - 36, 76), COLORS["text"])
        y = rect.y + 178
        if room.enemies and not room.cleared:
            names = ", ".join(enemy.get("name", "Enemy") for enemy in room.enemies)
            draw_text(self.screen, self.small_font, f"Enemies: {names}", rect.x + 18, y, COLORS["danger"])
            y += 26
        if room.room_type == "Boss Room" and not room.cleared:
            draw_text(self.screen, self.small_font, f"Boss: {self.floor.boss['name']}", rect.x + 18, y, COLORS["danger"])
            y += 26
        draw_text(self.screen, self.small_font, "Player", rect.x + 18, y, COLORS["accent"])
        y += 28
        for line in self.player.display_lines():
            draw_text(self.screen, self.small_font, line, rect.x + 18, y, COLORS["text"])
            y += 22
        y += 6
        draw_text(self.screen, self.small_font, "Controls", rect.x + 18, y, COLORS["accent"])
        y += 24
        controls = [
            "W/Up: North | D/Right: East",
            "S/Down: South | A/Left: West",
            "Click highlighted rooms to move",
            "Enter: interact/start combat",
            "I: inventory | C: character | Esc: menu",
        ]
        for line in controls:
            draw_text(self.screen, self.small_font, line, rect.x + 18, y, COLORS["muted"])
            y += 21

    def draw_combat(self) -> None:
        if not self.player or not self.combat:
            return
        top = pygame.Rect(20, 18, 1240, 58)
        pygame.draw.rect(self.screen, COLORS["panel"], top, border_radius=8)
        draw_text(self.screen, self.font, f"COMBAT | {self.player.name} | Turn {self.combat.turn}", 38, 30, COLORS["danger"])
        self.draw_hp_bar(pygame.Rect(420, 34, 320, 22), self.player.hp, self.player.max_hp, COLORS["good"])
        draw_text(self.screen, self.small_font, f"HP {self.player.hp}/{self.player.max_hp}", 752, 34, COLORS["text"])

        enemy_rect = pygame.Rect(20, 96, 760, 250)
        action_rect = pygame.Rect(800, 96, 460, 250)
        log_rect = pygame.Rect(20, 370, 1240, 330)
        pygame.draw.rect(self.screen, COLORS["panel"], enemy_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["panel"], action_rect, border_radius=8)

        draw_text(self.screen, self.font, "Hostiles", enemy_rect.x + 18, enemy_rect.y + 18, COLORS["accent"])

        active = self.combat.active_enemy()
        portrait_rect = pygame.Rect(enemy_rect.x + 24, enemy_rect.y + 58, 156, 156)
        pygame.draw.rect(self.screen, COLORS["bg"], portrait_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["danger"], portrait_rect, width=2, border_radius=8)
        if active:
            # Portrait-ready placeholder until enemy portrait assets are generated.
            draw_text(self.screen, self.big_font, "?", portrait_rect.x + 62, portrait_rect.y + 45, COLORS["danger"])
            draw_text(self.screen, self.small_font, "Enemy Portrait", portrait_rect.x + 22, portrait_rect.y + 114, COLORS["muted"])

        y = enemy_rect.y + 58
        for enemy in self.combat.enemies:
            status = "ALIVE" if enemy.alive else "DOWN"
            color = COLORS["danger"] if enemy.alive else COLORS["muted"]
            name_x = enemy_rect.x + 210
            draw_text(self.screen, self.font, f"{enemy.name} [{status}]", name_x, y, color)
            y += 30
            bar_color = COLORS["danger"] if enemy.alive else COLORS["muted"]
            self.draw_hp_bar(pygame.Rect(name_x, y, 310, 20), enemy.hp, enemy.max_hp, bar_color)
            draw_text(self.screen, self.small_font, f"HP {enemy.hp}/{enemy.max_hp}", name_x + 326, y - 2, COLORS["text"])
            y += 30
            draw_text(self.screen, self.small_font, f"ATK {enemy.attack} | DEF {enemy.defense} | XP {enemy.xp}", name_x, y, COLORS["text"])
            y += 38

        draw_text(self.screen, self.font, "Actions", action_rect.x + 18, action_rect.y + 18, COLORS["accent"])
        actions = [
            "A / Enter / Space: Attack",
            "D: Defend",
            "F: Flee (disabled for bosses)",
            "I: Inventory/use healing and combat items",
            "X: Inspect active enemy",
            "Esc: snark, not escape",
        ]
        y = action_rect.y + 64
        for line in actions:
            draw_text(self.screen, self.small_font, line, action_rect.x + 24, y, COLORS["text"])
            y += 30
        self.combat_log.draw(self.screen, self.small_font, log_rect)

    def draw_inventory(self) -> None:
        if not self.player:
            return
        top = pygame.Rect(20, 18, 1240, 58)
        list_rect = pygame.Rect(20, 96, 620, 500)
        detail_rect = pygame.Rect(660, 96, 600, 500)
        help_rect = pygame.Rect(20, 620, 1240, 80)
        pygame.draw.rect(self.screen, COLORS["panel"], top, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["panel"], list_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["panel"], detail_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["panel"], help_rect, border_radius=8)

        context = "Combat" if self.previous_state_before_inventory == GameState.COMBAT else "Exploration"
        draw_text(self.screen, self.font, f"INVENTORY | {context} | HP {self.player.hp}/{self.player.max_hp}", 38, 34, COLORS["accent"])
        draw_text(self.screen, self.font, "Items", list_rect.x + 18, list_rect.y + 18, COLORS["accent"])

        if not self.player.inventory:
            draw_text(self.screen, self.font, "No items. Somehow, capitalism failed you.", list_rect.x + 28, list_rect.y + 90, COLORS["muted"])
        else:
            visible = self.player.inventory[:14]
            y = list_rect.y + 62
            for idx, item in enumerate(visible):
                selected = idx == self.inventory_selection
                row = pygame.Rect(list_rect.x + 16, y - 4, list_rect.width - 32, 30)
                if selected:
                    pygame.draw.rect(self.screen, COLORS["button_hover"], row, border_radius=5)
                equipped = ""
                if self.player.equipped_weapon is item or (self.player.equipped_weapon and self.player.equipped_weapon.get("id") == item.get("id") and item.get("type") == "weapon"):
                    equipped = " [E]"
                if self.player.equipped_armor is item or (self.player.equipped_armor and self.player.equipped_armor.get("id") == item.get("id") and item.get("type") == "armor"):
                    equipped = " [E]"
                label = f"{idx + 1}. {item.get('name', 'Unknown')}{equipped}"
                color = COLORS["accent"] if selected else COLORS["text"]
                draw_text(self.screen, self.small_font, label, list_rect.x + 28, y, color)
                rarity = rarity_label(item)
                draw_text(self.screen, self.small_font, rarity, list_rect.x + 430, y, COLORS["muted"])
                y += 34

        draw_text(self.screen, self.font, "Details", detail_rect.x + 18, detail_rect.y + 18, COLORS["accent"])
        if self.player.inventory:
            item = self.player.inventory[self.inventory_selection]
            y = detail_rect.y + 66
            detail_lines = [
                item.get("name", "Unknown Item"),
                f"Type: {item.get('type', 'item').title()}",
                f"Rarity: {rarity_label(item)}",
                f"Attack Bonus: {int(item.get('attack_bonus', 0) or 0)}",
                f"Defense Bonus: {int(item.get('defense_bonus', 0) or 0)}",
                f"Effect: {str(item.get('effect', 'none')).replace('_', ' ').title()}",
            ]
            if str(item.get("effect", "")).lower() == "combat_damage":
                detail_lines.append(f"Combat Damage: {int(item.get('damage', 0) or 0)}")
            for line in detail_lines:
                draw_text(self.screen, self.small_font, line, detail_rect.x + 28, y, COLORS["text"])
                y += 28
            y += 8
            draw_wrapped_text(self.screen, self.small_font, item.get("flavor", "No flavor text. Suspicious."), pygame.Rect(detail_rect.x + 28, y, detail_rect.width - 56, 110), COLORS["muted"])
            y += 128
            draw_text(self.screen, self.small_font, "Selected summary:", detail_rect.x + 28, y, COLORS["accent"])
            y += 28
            draw_wrapped_text(self.screen, self.small_font, item_summary(item), pygame.Rect(detail_rect.x + 28, y, detail_rect.width - 56, 80), COLORS["text"])

        controls = "Up/Down: select | Enter/E: equip or use | I/Esc: return"
        draw_text(self.screen, self.font, controls, help_rect.x + 24, help_rect.y + 22, COLORS["text"])
        if self.previous_state_before_inventory == GameState.COMBAT:
            helper = "Combat items target the active enemy, consume your action, then enemies may retaliate."
        else:
            helper = "Weapons and armor equip safely. Healing consumables work anywhere. Combat items require active combat."
        draw_text(self.screen, self.small_font, helper, help_rect.x + 24, help_rect.y + 52, COLORS["muted"])


    def draw_shop(self) -> None:
        if not self.player or not self.floor:
            self.state = GameState.PLAYING
            return
        room = self.floor.rooms[self.player.current_room_id]
        offers = self.current_shop_offers()

        draw_text(self.screen, self.big_font, "Shop Kiosk", 470, 50, COLORS["accent"])
        draw_text(self.screen, self.font, f"Credits: {self.player.credits}", 980, 62, COLORS["gold"])
        panel = pygame.Rect(60, 125, 1160, 500)
        pygame.draw.rect(self.screen, COLORS["panel"], panel, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["panel_light"], panel, width=2, border_radius=10)

        draw_text(self.screen, self.font, "Offers", 90, 145, COLORS["accent"])
        if not offers:
            draw_text(self.screen, self.font, "Sold out. The kiosk is now just furniture with opinions.", 120, 280, COLORS["muted"])
        else:
            for i, item in enumerate(offers[:8]):
                row = pygame.Rect(80, 180 + i * 48, 660, 38)
                selected = i == self.shop_selection
                affordable = self.player.credits >= item_price(item)
                if selected:
                    pygame.draw.rect(self.screen, COLORS["button_hover"], row, border_radius=6)
                color = COLORS["text"] if affordable else COLORS["muted"]
                draw_text(self.screen, self.small_font, item.get("name", "Unknown Item"), row.x + 12, row.y + 9, COLORS["accent"] if selected else color)
                draw_text(self.screen, self.small_font, rarity_label(item), row.x + 360, row.y + 9, color)
                draw_text(self.screen, self.small_font, f"{item_price(item)} cr", row.x + 545, row.y + 9, COLORS["gold"] if affordable else COLORS["muted"])

            item = offers[self.shop_selection]
            detail = pygame.Rect(770, 180, 410, 360)
            pygame.draw.rect(self.screen, COLORS["bg"], detail, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["accent"], detail, width=2, border_radius=8)
            y = detail.y + 22
            draw_text(self.screen, self.font, item.get("name", "Unknown Item"), detail.x + 22, y, COLORS["accent"])
            y += 38
            lines = [
                f"Type: {item.get('type', 'item').title()}",
                f"Rarity: {rarity_label(item)}",
                f"Price: {item_price(item)} credits",
                f"ATK Bonus: {int(item.get('attack_bonus', 0) or 0)}",
                f"DEF Bonus: {int(item.get('defense_bonus', 0) or 0)}",
                f"Heal: {int(item.get('heal', 0) or 0)}",
                f"Damage: {int(item.get('damage', 0) or 0)}",
                f"Effect: {str(item.get('effect', 'none')).replace('_', ' ').title()}",
            ]
            for line in lines:
                draw_text(self.screen, self.small_font, line, detail.x + 22, y, COLORS["text"])
                y += 25
            y += 10
            draw_wrapped_text(self.screen, self.small_font, item.get("flavor", ""), pygame.Rect(detail.x + 22, y, detail.width - 44, 90), COLORS["muted"])

        draw_text(self.screen, self.font, "Up/Down: select | Enter/E: buy | Esc/I: leave shop", 300, 655, COLORS["muted"])

    def draw_loot_reveal(self) -> None:
        if not self.loot_reveal_items:
            self.state = GameState.PLAYING
            return
        item = self.loot_reveal_items[min(self.loot_reveal_index, len(self.loot_reveal_items) - 1)]
        self.assets.blit_scaled_ui(self.screen, "gameplay_bg", pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

        popup = pygame.Rect(230, 80, 820, 560)
        if not self.assets.blit_scaled_ui(self.screen, "loot_popup", popup):
            pygame.draw.rect(self.screen, COLORS["panel"], popup, border_radius=12)
            pygame.draw.rect(self.screen, COLORS["accent"], popup, width=3, border_radius=12)

        draw_text(self.screen, self.big_font, "NEW ITEM!", popup.x + 285, popup.y + 55, COLORS["accent"])
        icon_box = pygame.Rect(popup.x + 330, popup.y + 130, 160, 160)
        pygame.draw.rect(self.screen, COLORS["bg"], icon_box, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["gold"], icon_box, width=2, border_radius=10)
        draw_text(self.screen, self.big_font, "?", icon_box.x + 66, icon_box.y + 47, COLORS["gold"])

        y = popup.y + 320
        draw_text(self.screen, self.font, item.get("name", "Unknown Item"), popup.x + 70, y, COLORS["accent"])
        y += 38
        draw_text(self.screen, self.font, f"{rarity_label(item)} {item.get('type', 'item').title()}", popup.x + 70, y, COLORS["text"])
        y += 40
        draw_wrapped_text(self.screen, self.small_font, item_summary(item), pygame.Rect(popup.x + 70, y, popup.width - 140, 52), COLORS["text"])
        y += 70
        draw_wrapped_text(self.screen, self.small_font, item.get("flavor", "No flavor. Concerning."), pygame.Rect(popup.x + 70, y, popup.width - 140, 60), COLORS["muted"])

        count = f"{self.loot_reveal_index + 1}/{len(self.loot_reveal_items)}"
        draw_text(self.screen, self.small_font, count, popup.right - 95, popup.y + 26, COLORS["muted"])
        draw_text(self.screen, self.font, "Press Enter/Space to continue.", popup.x + 245, popup.bottom - 58, COLORS["muted"])

    def draw_floor_complete(self) -> None:
        if not self.floor_completion_summary and self.floor:
            self.prepare_floor_complete_summary()
        summary = self.floor_completion_summary
        draw_text(self.screen, self.big_font, "Floor Cleared", 455, 60, COLORS["accent"])
        panel = pygame.Rect(250, 135, 780, 460)
        pygame.draw.rect(self.screen, COLORS["panel"], panel, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["accent"], panel, width=3, border_radius=10)

        lines = [
            f"Floor {summary.get('floor', '?')}: {summary.get('theme', 'Unknown Floor')}",
            f"Boss Defeated: {summary.get('boss', 'Unknown Boss')}",
            f"Rooms Cleared: {summary.get('rooms_cleared', 0)}/{summary.get('rooms_total', 0)}",
            f"Items Found This Run: {summary.get('items_found', 0)}",
            f"Current Credits: {summary.get('credits', 0)}",
            "",
            f"Continue to Floor {summary.get('next_floor', '?')}?",
        ]
        y = panel.y + 48
        for line in lines:
            color = COLORS["accent"] if line.startswith("Continue") else COLORS["text"]
            draw_text(self.screen, self.font, line, panel.x + 60, y, color)
            y += 45 if line else 28
        draw_text(self.screen, self.font, "Enter/Space: continue | Esc: return to current floor", 320, 650, COLORS["muted"])

    def draw_run_summary(self) -> None:
        draw_text(self.screen, self.big_font, "Run Summary", 455, 62, COLORS["accent"])
        panel = pygame.Rect(260, 135, 760, 470)
        pygame.draw.rect(self.screen, COLORS["panel"], panel, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["panel_light"], panel, width=2, border_radius=10)
        lines = build_run_summary(self.run_data, self.player, self.floor, self.run_summary_reason)
        y = panel.y + 28
        for line in lines:
            draw_text(self.screen, self.font, line, panel.x + 36, y, COLORS["text"])
            y += 32
        draw_text(self.screen, self.font, "Press Enter, Space, or Esc to return to the main menu.", 330, 650, COLORS["muted"])

    def draw_death(self) -> None:
        draw_text(self.screen, self.big_font, "YOU DIED", 520, 90, COLORS["danger"])
        body = (
            "The cameras cut to a memorial montage assembled from your least flattering angles. "
            "Your seed save remains available, but this crawler's current condition is mostly paperwork."
        )
        draw_wrapped_text(self.screen, self.font, body, pygame.Rect(240, 190, 820, 150), COLORS["text"])
        if self.player:
            draw_text(self.screen, self.font, f"Final Level: {self.player.level} | HP: {self.player.hp}/{self.player.max_hp}", 420, 380, COLORS["muted"])
        draw_text(self.screen, self.font, "Press Enter, Space, or Esc to return to the main menu.", 330, 610, COLORS["muted"])
