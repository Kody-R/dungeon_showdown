from __future__ import annotations
import json
import random
import re

from ollama_client import OllamaClient


FALLBACK_FLOOR_INTRO = {
    "title": "Emergency Dungeon Broadcast",
    "intro": "The dungeon's narration system coughs, sparks, and begins reading from a laminated card.",
    "description": "This floor smells like danger, mildew, and unpaid overtime.",
    "warning": "Try not to die. It creates scheduling issues.",
}

FALLBACK_BOSS_INTRO = "The boss arrives with an expression that suggests upper management personally approved your suffering."
FALLBACK_SPONSOR = "Tonight's sponsor apologizes for nothing and reminds you that danger is just engagement with sharper edges."
FALLBACK_DEATH_RECAP = "The broadcast cuts to a memorial reel assembled from panic, poor decisions, and one extremely judgmental camera angle."
FALLBACK_VICTORY_RECAP = "The boss falls, the audience roars, and the dungeon pretends this was all part of its quarterly plan."
FALLBACK_RARE_LOOT = "The crate opens with dramatic lighting. Something inside is either valuable, cursed, or both."


class LoreManager:
    def __init__(self, ollama_client: OllamaClient):
        self.client = ollama_client

    def generate_floor_lore(self, floor, progress=None) -> dict:
        existing = floor.lore or {}
        if existing.get("ollama_floor_intro") or existing.get("generated_once"):
            return existing

        if progress:
            progress("Contacting local announcer AI...")
        enemy_names = sorted({enemy.get("name", "Enemy") for room in floor.rooms.values() for enemy in room.enemies})
        prompt = self._floor_prompt(floor.floor_number, floor.theme, floor.boss, enemy_names)
        fallback_json = json.dumps(FALLBACK_FLOOR_INTRO)
        text = self.client.generate(prompt, temperature=0.82, max_tokens=500, fallback=fallback_json)
        parsed = self._parse_lore_json(text)

        lore = dict(existing)
        lore.update(parsed)
        lore["ollama_floor_intro"] = bool(not self.client.last_error and text.strip() != fallback_json)
        lore["generated_once"] = True
        if self.client.last_error:
            lore["generation_error"] = self.client.last_error
        floor.lore = lore
        floor.generated_by_ollama = bool(lore.get("ollama_floor_intro"))
        return lore

    def generate_boss_intro(self, floor, progress=None) -> str:
        floor.lore.setdefault("boss_intro", "")
        if floor.lore.get("boss_intro"):
            return floor.lore["boss_intro"]
        if progress:
            progress("Writing boss intro...")
        prompt = self._boss_prompt(floor.boss, floor.theme)
        text = self.client.generate(prompt, temperature=0.86, max_tokens=220, fallback=FALLBACK_BOSS_INTRO)
        floor.lore["boss_intro"] = text.strip() or FALLBACK_BOSS_INTRO
        if self.client.last_error:
            floor.lore["boss_intro_error"] = self.client.last_error
        return floor.lore["boss_intro"]

    def generate_sponsor_message(self, floor, sponsors: list[dict], progress=None) -> str:
        floor.lore.setdefault("sponsor_message", "")
        if floor.lore.get("sponsor_message"):
            return floor.lore["sponsor_message"]
        if progress:
            progress("Creating morally questionable sponsor ad...")
        sponsor = self._pick_sponsor(floor.floor_number, floor.theme, sponsors)
        prompt = self._sponsor_prompt(sponsor)
        text = self.client.generate(prompt, temperature=0.9, max_tokens=140, fallback=FALLBACK_SPONSOR)
        floor.lore["sponsor"] = sponsor
        floor.lore["sponsor_message"] = text.strip() or FALLBACK_SPONSOR
        if self.client.last_error:
            floor.lore["sponsor_error"] = self.client.last_error
        return floor.lore["sponsor_message"]

    def generate_floor_package(self, floor, sponsors: list[dict], progress=None) -> dict:
        if progress:
            progress(f"Generating Floor {floor.floor_number} broadcast package...")
        self.generate_floor_lore(floor, progress)
        self.generate_boss_intro(floor, progress)
        self.generate_sponsor_message(floor, sponsors, progress)
        if progress:
            progress("Saving floor data...")
        return floor.lore


    def generate_death_recap(self, floor, player, cause: str = "defeat", progress=None) -> str:
        floor.lore.setdefault("death_recaps", [])
        if progress:
            progress("Writing death recap...")
        prompt = f"""Write a short original death recap for a dark comedy televised dungeon crawler.

Player name: {getattr(player, 'name', 'Crawler')}
Player class: {getattr(player, 'player_class', 'Unknown')}
Floor: {getattr(floor, 'floor_number', '?')} - {floor.theme.get('name', 'Unknown Floor')}
Cause of death: {cause}

Tone: sarcastic, theatrical, funny, not copyrighted.
Rules: Do not change mechanics or invent stats. Keep under 120 words."""
        text = self.client.generate(prompt, temperature=0.88, max_tokens=180, fallback=FALLBACK_DEATH_RECAP)
        recap = text.strip() or FALLBACK_DEATH_RECAP
        floor.lore["death_recaps"].append(recap)
        return recap

    def generate_victory_recap(self, floor, player, progress=None) -> str:
        if floor.lore.get("victory_recap"):
            return floor.lore["victory_recap"]
        if progress:
            progress("Writing victory recap...")
        prompt = f"""Write a short original floor victory recap for a dark comedy televised dungeon crawler.

Player name: {getattr(player, 'name', 'Crawler')}
Player class: {getattr(player, 'player_class', 'Unknown')}
Floor: {getattr(floor, 'floor_number', '?')} - {floor.theme.get('name', 'Unknown Floor')}
Defeated boss: {floor.boss.get('name', 'Unknown Boss')}

Tone: sarcastic, triumphant, absurd, not copyrighted.
Rules: Do not change mechanics or invent stats. Keep under 140 words."""
        text = self.client.generate(prompt, temperature=0.86, max_tokens=200, fallback=FALLBACK_VICTORY_RECAP)
        floor.lore["victory_recap"] = text.strip() or FALLBACK_VICTORY_RECAP
        return floor.lore["victory_recap"]

    def generate_rare_loot_narration(self, floor, item: dict, progress=None) -> str:
        key = "rare_loot_narration"
        floor.lore.setdefault(key, {})
        item_id = str(item.get("id", item.get("name", "unknown_item")))
        if item_id in floor.lore[key]:
            return floor.lore[key][item_id]
        if progress:
            progress("Writing rare loot reveal...")
        prompt = f"""Write a short rare loot reveal for a dark comedy dungeon crawler game show.

Item: {item.get('name', 'Unknown Item')}
Rarity: {item.get('rarity', 'rare')}
Flavor: {item.get('flavor', '')}

Rules: Do not create stats. Do not change mechanics. Keep under 70 words."""
        text = self.client.generate(prompt, temperature=0.9, max_tokens=110, fallback=FALLBACK_RARE_LOOT)
        narration = text.strip() or FALLBACK_RARE_LOOT
        floor.lore[key][item_id] = narration
        return narration

    def _floor_prompt(self, floor_number: int, theme: dict, boss: dict, enemy_names: list[str]) -> str:
        return f"""You are the announcer and lore writer for an original dark comedy dungeon crawler game.

Write a dramatic, sarcastic intro for Floor {floor_number}.

Game context:
- The player is trapped in a deadly televised underground dungeon.
- The show is watched by unseen audiences.
- The tone is absurd, dangerous, violent, and funny.
- Do not use copyrighted names, characters, factions, authors, books, or franchises.
- Do not alter gameplay mechanics.
- Do not include stat blocks.

Floor theme:
{theme.get('name', 'Unbranded Danger Zone')} — {theme.get('tone', 'dangerous comedy')}
{theme.get('description', '')}

Floor boss:
{boss.get('name', 'Unknown Boss')}

Known enemies:
{', '.join(enemy_names) if enemy_names else 'Unknown contractual hostiles'}

Return ONLY valid JSON with these keys:
{{
  "intro": "2-4 sentence broadcast intro",
  "title": "short floor title",
  "description": "one paragraph environmental description",
  "warning": "one announcer warning"
}}
Keep the total under 300 words."""

    def _boss_prompt(self, boss: dict, theme: dict) -> str:
        return f"""Write an original boss introduction for a dark comedy dungeon crawler.

Boss name:
{boss.get('name', 'Unknown Boss')}

Boss type:
{boss.get('type', boss.get('id', 'boss'))}

Floor theme:
{theme.get('name', 'Unbranded Danger Zone')}

Tone:
Sarcastic, theatrical, threatening, absurd.

Rules:
- Do not create stats.
- Do not describe copyrighted characters.
- Do not mention real books, authors, or franchises.
- Keep it under 180 words."""

    def _sponsor_prompt(self, sponsor: dict) -> str:
        return f"""Write a fake sponsor message for a deadly dungeon game show.

Sponsor name:
{sponsor.get('name', 'Liability Snacks Unlimited')}

Product:
{sponsor.get('product', 'Emergency Regret Wafer')}

Tone:
Corporate, cheerful, morally awful, funny.

Rules:
- Keep it under 90 words.
- Do not include real brands.
- Do not affect gameplay."""

    def _parse_lore_json(self, text: str) -> dict:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    parsed = dict(FALLBACK_FLOOR_INTRO)
            else:
                parsed = dict(FALLBACK_FLOOR_INTRO)
        return {
            "title": str(parsed.get("title") or FALLBACK_FLOOR_INTRO["title"]).strip(),
            "intro": str(parsed.get("intro") or FALLBACK_FLOOR_INTRO["intro"]).strip(),
            "description": str(parsed.get("description") or FALLBACK_FLOOR_INTRO["description"]).strip(),
            "warning": str(parsed.get("warning") or FALLBACK_FLOOR_INTRO["warning"]).strip(),
        }

    def _pick_sponsor(self, floor_number: int, theme: dict, sponsors: list[dict]) -> dict:
        if not sponsors:
            return {"name": "Liability Snacks Unlimited", "product": "Emergency Regret Wafer"}
        rng = random.Random(f"{floor_number}:{theme.get('id', theme.get('name', 'theme'))}:sponsor")
        return dict(rng.choice(sponsors))
