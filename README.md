# Dungeon Showdown

**Dungeon Showdown** is a local-first Python/Pygame dungeon crawler about surviving a televised corporate-apocalypse dungeon full of traps, loot, bad sponsors, strange contestants, and deeply unsafe room design.

The game mixes deterministic roguelike-style gameplay with optional local AI-generated flavor text through **Ollama**. Python controls the actual game mechanics. Ollama is used only for lore, broadcasts, boss intros, sponsor messages, death recaps, and other immersion text.

No external servers are required to play.

---

## Current Status

Dungeon Showdown is currently a playable prototype with:

* Pygame-based UI
* class selection
* seed-based floor generation
* room-to-room exploration
* directional map movement
* turn-based combat
* inventory and equipment
* healing items
* combat consumables
* shops
* loot reveal screens
* boss fights
* floor completion summaries
* optional Ollama-powered generated lore
* generated UI and placeholder art assets

The project is still in active development.

---

## Features

### Dungeon Exploration

Each run uses a seed to generate dungeon floors with connected rooms. Rooms can include:

* Combat
* Trap
* Loot
* Sponsor Crate
* Shop
* Rest
* NPC Event
* Mini-Boss
* Boss Gate
* Boss Room
* Exit

Movement is based on the visible map layout.

```text
W / Up       Move North
D / Right    Move East
S / Down     Move South
A / Left     Move West
Mouse        Click highlighted connected rooms
Enter        Interact with current room
I            Open inventory
C            Character/status log
Esc          Menu/back
```

---

## Classes

The game includes several playable class templates, each with different starting stats, special flavor, and starting items.

Current class examples:

* Scrapper
* Former Mall Cop
* Failed Magician
* Lunch Lady Avenger
* IT Department Survivor
* Mascot Handler

Classes are defined in:

```text
data/player_classes.json
```

---

## Combat

Combat is turn-based and uses player stats, enemy stats, equipment bonuses, status effects, and item effects.

Combat controls:

```text
A / Enter / Space   Attack
D                   Defend
F                   Flee
I                   Open inventory
X                   Inspect active enemy
Esc                 Snark, not escape
```

Combat supports:

* enemy HP bars
* player HP bar
* standard enemy portrait placeholder
* mini-boss portrait placeholder
* boss portrait placeholder
* critical hits
* defense turns
* flee attempts
* combat item use
* enemy retaliation
* XP rewards
* credit rewards

---

## Inventory

The inventory supports:

* weapons
* armor
* consumables
* trinkets
* healing items
* combat items
* equipped item indicators
* item rarity labels
* item summaries
* item flavor text
* default item icons by type

Inventory controls:

```text
Up / Down            Select item
Enter / Space / E    Equip or use item
I / Esc              Return
```

Current default item icon types:

```text
assets/icons/items/item_weapon.png
assets/icons/items/item_armor.png
assets/icons/items/item_consumable.png
assets/icons/items/item_trinket.png
```

---

## Shops

Shop rooms now open an actual shop screen instead of auto-buying items.

Shop features:

* selectable item offers
* price display
* rarity display
* type display
* effect display
* affordability checking
* item icon display
* manual buying

Shop controls:

```text
Up / Down            Select item
Enter / Space / E    Buy selected item
Esc / I              Leave shop
```

---

## Loot Reveal Screen

Loot and sponsor crates display a dedicated reveal popup.

Loot reveal includes:

* item icon
* item name
* rarity
* item type
* effect summary
* flavor text
* multiple-item paging

Controls:

```text
Enter / Space    Continue through loot
Esc              Continue
```

---

## Floor Completion

After defeating a boss or reaching an exit, the game displays a floor completion/elevator summary screen.

The summary includes:

* floor number
* floor theme
* boss defeated
* rooms cleared
* items found
* current credits
* next floor prompt

Controls:

```text
Enter / Space    Continue to next floor
Esc              Return to current floor
```

---

## Optional Ollama Integration

Dungeon Showdown can use a locally running Ollama server to generate immersive lore.

Ollama can generate:

* floor titles
* floor introductions
* floor warnings
* boss intros
* sponsor messages
* rare loot narration
* death recaps
* victory recaps

The default Ollama API endpoint is:

```text
http://localhost:11434/api/generate
```

The game also checks installed models through:

```text
http://localhost:11434/api/tags
```

If Ollama is unavailable, slow, or disabled, the game falls back to local default text. Gameplay does not depend on Ollama.

---

## Recommended Ollama Models

The game does not require a specific model, but these are good local choices:

```text
llama3.1:8b
mistral-nemo
qwen2.5:7b
gemma2:9b
```

You can install a model with:

```bash
ollama pull llama3.1:8b
```

Then start Ollama:

```bash
ollama serve
```

---

## Installation

### Requirements

* Python 3.10+
* Pygame
* Requests
* Optional: Ollama

---

### Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/dungeon-showdown.git
cd dungeon-showdown
```

---

### Create a Virtual Environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Install Dependencies

```bash
pip install pygame requests
```

Or, if a `requirements.txt` file exists:

```bash
pip install -r requirements.txt
```

---

### Run the Game

```bash
python main.py
```

---

## Project Structure

```text
dungeon_showdown/
├── main.py
├── game.py
├── config.py
├── player.py
├── dungeon.py
├── floor_generator.py
├── combat.py
├── enemies.py
├── inventory.py
├── items.py
├── save_system.py
├── seed_manager.py
├── ui.py
├── asset_manager.py
├── audio_manager.py
├── announcer.py
├── lore_manager.py
├── ollama_client.py
├── run_summary.py
├── data/
│   ├── player_classes.json
│   ├── bosses.json
│   ├── enemies.json
│   ├── floor_themes.json
│   ├── items.json
│   ├── loot_tables.json
│   ├── rooms.json
│   ├── sponsors.json
│   └── trap_templates.json
├── assets/
│   ├── ui/
│   ├── icons/
│   │   ├── classes/
│   │   └── items/
│   └── portraits/
│       ├── classes/
│       ├── enemies/
│       └── bosses/
└── saves/
```

---

## Data Files

Most of the game content is data-driven through JSON files.

### `data/items.json`

Defines:

* weapons
* armor
* consumables
* trinkets
* healing items
* combat items
* rarity
* stats
* effects
* flavor text

Example item:

```json
{
  "id": "printer_toner_grenade",
  "name": "Printer Toner Grenade",
  "type": "consumable",
  "rarity": "uncommon",
  "damage": 18,
  "effect": "combat_damage",
  "flavor": "Explodes into dust, regret, and one final page jam."
}
```

---

### `data/enemies.json`

Defines standard enemy templates.

Enemy fields include:

* id
* name
* hp
* attack
* defense
* xp
* tags
* abilities
* flavor

---

### `data/bosses.json`

Defines boss templates.

Bosses include:

* larger HP pools
* stronger attacks
* floor theme matching tags
* boss flavor text
* special abilities

---

### `data/floor_themes.json`

Defines possible floor themes.

Themes affect:

* tone
* description
* enemy tag selection
* boss tag selection
* trap selection
* loot bias

---

### `data/rooms.json`

Defines reusable room event templates.

Room events can provide:

* flavor outcomes
* NPC text
* shop events
* random rewards
* healing events
* small loot events

---

### `data/sponsors.json`

Defines fake in-game sponsors used for broadcast-style flavor.

---

## Assets

Dungeon Showdown supports generated and custom art assets.

Current asset categories include:

```text
assets/ui/
assets/icons/
assets/icons/classes/
assets/icons/items/
assets/portraits/classes/
assets/portraits/enemies/
assets/portraits/bosses/
```

Default image fallbacks are included for:

```text
standard enemies
mini-bosses
bosses
weapons
armor
consumables
trinkets
```

Current default enemy portrait files:

```text
assets/portraits/enemies/default_enemy.png
assets/portraits/enemies/default_miniboss.png
assets/portraits/bosses/default_boss.png
```

Current default item icon files:

```text
assets/icons/items/item_weapon.png
assets/icons/items/item_armor.png
assets/icons/items/item_consumable.png
assets/icons/items/item_trinket.png
```

---

## Save System

Runs are saved locally in:

```text
saves/
```

The save system stores:

* run seed
* player data
* current floor
* floor data
* generated lore
* inventory
* equipment
* stats
* progress

Generated Ollama lore is saved to the run seed file so it does not need to be regenerated every time the run is loaded.

---

## Settings

The settings screen supports:

* UI theme selection
* difficulty preset
* Ollama enabled/disabled
* Ollama model selection
* generation timeout behavior

Current UI theme examples:

```text
Hazard Broadcast
Cold Corporate
Toxic Neon
```

Current difficulty examples:

```text
Easy
Normal
Hard
Nightmare
```

---

## Design Goals

Dungeon Showdown is built around a few core principles:

1. **Python controls all gameplay.**
   AI text should never determine combat outcomes, loot rolls, enemy stats, or player survival.

2. **Ollama is optional.**
   The game must work offline and without AI generation.

3. **Seeds should be persistent.**
   Generated floors and lore should be saved so a run remains consistent.

4. **Content should be data-driven.**
   Items, enemies, bosses, sponsors, rooms, traps, and floor themes should be easy to expand through JSON.

5. **The tone should be funny, violent, weird, and original.**
   The game should feel like a corporate death-game broadcast without relying on copyrighted story material.

---

## Roadmap

Planned or possible future upgrades:

* unique enemy portraits
* unique boss portraits
* per-item custom icons
* item category tabs
* character/status screen redesign
* boss intro screen with portrait
* floor transition animations
* better room transition effects
* sound effects
* background music
* controller support
* combat targeting for multi-enemy item use
* status effect icons
* animated damage/heal feedback
* more room event types
* more floor themes
* more sponsor events
* expanded announcer commentary
* build scripts for Windows releases

---

## Known Limitations

Current prototype limitations:

* enemy portraits are still defaults by tier
* item icons are defaults by item type
* combat item targeting currently hits the active enemy
* some UI screens are still being polished
* audio support is optional and may not include full sound assets yet
* balance is still experimental
* generated lore quality depends on the local Ollama model used

---

## Development Notes

This project is designed to be expanded in phases.

When adding new content, prefer editing JSON files first:

```text
data/items.json
data/enemies.json
data/bosses.json
data/floor_themes.json
data/rooms.json
data/sponsors.json
data/trap_templates.json
```

When adding new assets, place them in the appropriate `assets/` subfolder and then wire them through `asset_manager.py`.

---

## Credits

Dungeon Showdown is an original Python/Pygame dungeon crawler prototype.

Game systems, code structure, JSON content, and generated asset concepts were developed as an original project.

This repository does not include copyrighted lore, characters, or story content from any existing book, show, game, or franchise.

---

## License

Choose a license before publishing.

Suggested options:

* MIT License for permissive open-source use
* GPLv3 if you want derivative projects to stay open-source
* All Rights Reserved if this is a private/proprietary game project

Example placeholder:

```text
Copyright (c) 2026 YOUR NAME

License TBD.
```

---

## Quick Start

```bash
git clone https://github.com/YOUR-USERNAME/dungeon-showdown.git
cd dungeon-showdown
python -m venv .venv
.venv\Scripts\activate
pip install pygame requests
python main.py
```

For Linux/macOS:

```bash
git clone https://github.com/YOUR-USERNAME/dungeon-showdown.git
cd dungeon-showdown
python3 -m venv .venv
source .venv/bin/activate
pip install pygame requests
python main.py
```
