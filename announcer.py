from __future__ import annotations
import random
from typing import Any


class Announcer:
    """Local, deterministic-ish announcer flavor.

    This class never changes mechanics. It only returns text lines for the UI/log.
    Ollama-enhanced long-form recaps live in lore_manager.py and are called sparingly.
    """

    COMBAT_START = [
        "Announcer: The violence department is thrilled to see everyone on schedule.",
        "Announcer: Remember, folks: every bad decision is premium content.",
        "Announcer: Weapons out, dignity optional, liability waived.",
        "Announcer: The room has chosen conflict. How brand-forward.",
    ]

    ATTACK = [
        "Announcer: A clean hit! Well, legally clean. Physically disgusting.",
        "Announcer: That impact tested beautifully with our focus group of jackals.",
        "Announcer: The audience loves direct problem solving with blunt instruments.",
        "Announcer: A medically interesting choice from our crawler!",
    ]

    CRIT = [
        "Announcer: CRITICAL HIT! That one had a commemorative plaque attached.",
        "Announcer: CRITICAL HIT! The replay team just screamed in four departments.",
        "Announcer: CRITICAL HIT! Somewhere, a sponsor paid extra for that angle.",
        "Announcer: CRITICAL HIT! That voided three warranties and one childhood dream.",
    ]

    DEFEND = [
        "Announcer: Defensive posture! Not glamorous, but neither is dying.",
        "Announcer: The crawler briefly becomes a fortified complaint form.",
        "Announcer: Blocking: the official strategy of people with tomorrow plans.",
    ]

    FLEE_SUCCESS = [
        "Announcer: Tactical retreat! Cowardice, but with footwork.",
        "Announcer: The crawler escapes. The audience is booing, but softly entertained.",
    ]

    FLEE_FAIL = [
        "Announcer: Escape denied! The dungeon loves commitment.",
        "Announcer: Running failed. Excellent news for our advertisers.",
    ]

    TRAP_AVOIDED = [
        "Announcer: Trap avoided! Somewhere, a sad engineer deletes a spreadsheet.",
        "Announcer: The crawler spots the trap before it becomes a customer-service issue.",
        "Announcer: Nice reflexes! The floor hates that.",
    ]

    TRAP_TRIGGERED = [
        "Announcer: Trap triggered! That sound was pain with a marketing budget.",
        "Announcer: The dungeon reminds everyone that caution is not just a font choice.",
        "Announcer: Contact! The trap department earns a tiny bonus.",
    ]

    LOOT = [
        "Announcer: Loot crate! Because nothing says survival like questionable packaging.",
        "Announcer: New item reveal! Please ignore the teeth marks on the label.",
        "Announcer: The crawler receives goods. Whether they are helpful is a separate tragedy.",
    ]

    RARE_LOOT = [
        "Announcer: RARE ITEM! The accounting goblins just approved dramatic lighting.",
        "Announcer: Now that is premium loot. Please clap before it becomes cursed.",
        "Announcer: The rarity meter is making a noise usually reserved for lawsuits.",
    ]

    LEVEL_UP = [
        "Announcer: LEVEL UP! The crawler becomes slightly harder to monetize as a corpse.",
        "Announcer: Growth! Progress! A statistically smaller chance of immediate liquidation!",
        "Announcer: The numbers went up. The crowd accepts this as character development.",
    ]

    DEATH = [
        "Announcer: And that's a wrap on this crawler's vertical integration with the floor.",
        "Announcer: The crawler has died. Please enjoy this respectful ad break for meat insurance.",
        "Announcer: Fatality confirmed. The memorial montage has already chosen unflattering music.",
    ]

    VICTORY = [
        "Announcer: Victory! The boss has been downgraded from threat to floor decoration.",
        "Announcer: The crawler survives, upsetting several internal projections.",
        "Announcer: Boss defeated! The audience is cheering, screaming, and ordering snacks.",
    ]

    REST = [
        "Announcer: Rest station activated. Even televised nightmares have labor laws.",
        "Announcer: Health restored. The dungeon considers this deeply rude.",
    ]

    SPONSOR_BREAK = [
        "Announcer: Sponsor break! Morality will resume after this message.",
        "Announcer: A word from our sponsor, who has definitely read none of the incident reports.",
    ]

    ROOM_CLEAR = [
        "Announcer: Room cleared. Sanitation crews are pretending not to notice.",
        "Announcer: Another room resolved through grit, panic, and questionable inputs.",
    ]

    def __init__(self, seed: int | str = "broadcast") -> None:
        self.rng = random.Random(f"announcer:{seed}")

    def line(self, category: str) -> str:
        bank = getattr(self, category, None)
        if isinstance(bank, list) and bank:
            return self.rng.choice(bank)
        return "Announcer: The booth crackles ominously, then pretends that was intentional."

    def combat_start(self, is_boss: bool = False) -> str:
        if is_boss:
            return "Announcer: BOSS FIGHT! Viewers with weak stomachs should upgrade to premium nausea filtering."
        return self.line("COMBAT_START")

    def after_combat_messages(self, messages: list[str]) -> list[str]:
        joined = "\n".join(messages).lower()
        lines: list[str] = []
        if "critical" in joined or "crit" in joined:
            lines.append(self.line("CRIT"))
        elif any("you hit" in m.lower() for m in messages):
            if self.rng.random() < 0.35:
                lines.append(self.line("ATTACK"))
        if any("defend" in m.lower() or "brace" in m.lower() for m in messages):
            if self.rng.random() < 0.45:
                lines.append(self.line("DEFEND"))
        if "flee successfully" in joined:
            lines.append(self.line("FLEE_SUCCESS"))
        elif "fail to flee" in joined or "escape denied" in joined:
            lines.append(self.line("FLEE_FAIL"))
        if "level up" in joined:
            lines.append(self.line("LEVEL_UP"))
        return lines

    def loot_reveal(self, item: dict[str, Any]) -> str:
        rarity = str(item.get("rarity", "common")).lower()
        if rarity in {"rare", "epic", "legendary", "absurd"}:
            return self.line("RARE_LOOT")
        return self.line("LOOT")
