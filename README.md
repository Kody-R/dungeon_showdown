# Dungeon Showdown - Phase 8 Prototype

Original dark-comedy roguelike framework for a chaotic televised dungeon crawler. Core gameplay is deterministic Python; Ollama is used only for flavor/lore and has safe fallbacks.

## Run

```bash
pip install pygame requests
python main.py
```

## Phase 8 Adds Polish

Phase 8 builds on the Phase 7 content expansion and focuses on presentation, settings, and run-structure polish:

- Better main menu labeling and improved settings screen.
- Keyboard-adjustable settings for difficulty, UI theme, Ollama enabled, detected model selection, timeout, volume, fullscreen flag, and autosave flag.
- Three UI theme presets: Hazard Broadcast, Cold Corporate, and Toxic Neon.
- Difficulty presets: easy, normal, hard, and nightmare.
- Difficulty scaling for newly generated floors, including enemy HP/attack and trap difficulty.
- Credits/currency tracked on the player.
- Shop rooms now price items and purchase the cheapest affordable offer instead of giving everything away.
- Combat victories award credits based on room type, XP value, and difficulty.
- Run summary screen showing seed, floor progress, class, level, credits, rooms cleared, items found, and defeated bosses.
- Safe optional audio hook through `audio_manager.py`; missing files or missing audio devices do not crash the game.
- Safe optional sprite/icon hook through `asset_manager.py`; generated fallback icons are used when image files are missing.
- Player stats now persist additional Phase 8 run metrics.

## Controls

### Main Menu

- Mouse: click buttons
- Esc: quit/back depending on screen

### Class Selection

- Up / Down: select class
- Enter / Space: start run with selected class
- Esc: return to menu

### Settings

- Up / Down: select setting
- Left / Right or Enter / Space: change selected setting
- Esc: return to menu

### Exploration

- W / Up: move to connection slot 1
- D / Right: move to connection slot 2
- S / Down: move to connection slot 3
- A / Left: move to connection slot 4
- Enter: interact/start combat/claim room reward
- I: inventory
- C: character summary
- M: map comment
- Esc: menu

### Combat

- A / Enter / Space: attack
- D: defend
- F: flee, disabled for bosses
- I: inventory/use item
- X: inspect active enemy
- Esc: snark, not escape

### Inventory

- Up / Down: select item
- Enter / Space / E: equip weapon/armor or use consumable
- I / Esc: return

## Optional Assets

The game runs without assets, but later packs can use this structure:

```text
assets/
├── music/
├── sounds/
└── sprites/
    └── icons/
```

Audio and icon loading are intentionally defensive. Missing files are ignored.

## Project Structure

```text
dungeon_showdown/
├── main.py
├── config.py
├── game.py
├── player.py
├── dungeon.py
├── floor_generator.py
├── combat.py
├── inventory.py
├── items.py
├── enemies.py
├── save_system.py
├── seed_manager.py
├── ui.py
├── ollama_client.py
├── lore_manager.py
├── announcer.py
├── asset_manager.py
├── audio_manager.py
├── run_summary.py
├── data/
│   ├── player_classes.json
│   ├── enemies.json
│   ├── items.json
│   ├── bosses.json
│   ├── rooms.json
│   ├── sponsors.json
│   ├── trap_templates.json
│   ├── floor_themes.json
│   └── loot_tables.json
├── saves/
└── assets/
```

## Design Rule

The game should feel AI-enhanced, not AI-dependent. Enemy stats, item effects, combat math, floor graph generation, trap checks, class stats, difficulty scaling, shops, and save files are all Python-controlled. Ollama only generates saved narrative flavor.

## Phase 8 Asset Pack Integration

This build includes the first generated visual asset pack and the loader changes needed to use it.

New folders:

```text
assets/ui/
assets/icons/
```

Included UI assets:

```text
assets/ui/logo_dungeon_showdown.png
assets/ui/bg_title_screen.png
assets/ui/bg_gameplay_frame.png
assets/ui/ui_top_bar.png
assets/ui/ui_right_stats_panel.png
assets/ui/ui_bottom_log_panel.png
assets/ui/ui_popup_loot.png
assets/ui/ui_popup_boss.png
```

Included room icons:

```text
assets/icons/icon_room_entrance.png
assets/icons/icon_room_combat.png
assets/icons/icon_room_trap.png
assets/icons/icon_room_loot.png
assets/icons/icon_room_boss.png
```

`asset_manager.py` now checks `assets/ui` and `assets/icons` first, while keeping the older fallback behavior. If an image is missing or fails to load, the game still uses generated fallback icons/panels and should not crash.

The main menu now uses the title background and logo when present. The gameplay screen uses the generated top HUD bar, right panel, bottom log panel, and room icons when available.


## Movement UI Patch

Movement is now directional instead of connection-slot based. The current room's valid exits are shown on the map and side panel, connected rooms are highlighted, and players can click highlighted connected rooms to move.


## Heal Item Fix

Consumables now support data-driven healing from `items.json` using `effect: heal` and the `heal` value. `heal_and_inspire` also restores HP and applies a temporary attack buff.


## Combat Item Fix

Consumables with `effect: combat_damage` now work from the inventory while in combat. They target the active enemy, deal their configured `damage`, consume the item, advance the combat turn, and allow enemy retaliation unless the item ends the fight.


## Gameplay Polish Patch

Added:
- Real shop screen with selectable offers, prices, affordability, and item details.
- Combat HP bars for player and enemies plus a portrait-ready enemy panel.
- Loot reveal popup screen for room rewards.
- Floor completion/elevator summary screen after boss clear or exit interaction.
