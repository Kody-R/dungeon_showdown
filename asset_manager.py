from __future__ import annotations
from pathlib import Path
import pygame

from config import COLORS


class AssetManager:
    """UI/icon/portrait loader with safe fallbacks.

    Asset layout used by the upgraded Phase 8 asset build:
        assets/ui/*.png
        assets/icons/*.png
        assets/icons/classes/*.png
        assets/portraits/classes/*.png
        assets/sprites/*.png
        assets/sprites/icons/*.png  # legacy fallback path
    """

    ROOM_ICON_FILES = {
        "Entrance": "icon_room_entrance.png",
        "Combat": "icon_room_combat.png",
        "Trap": "icon_room_trap.png",
        "Loot": "icon_room_loot.png",
        "Sponsor Crate": "icon_room_sponsor.png",
        "Shop": "icon_room_shop.png",
        "Rest": "icon_room_rest.png",
        "NPC Event": "icon_room_npc.png",
        "Mini-Boss": "icon_room_miniboss.png",
        "Boss Gate": "icon_room_boss_gate.png",
        "Boss Room": "icon_room_boss.png",
        "Exit": "icon_room_exit.png",
    }

    GENERIC_ICON_FILES = {
        "credits": "icon_currency_credits.png",
    }

    CLASS_ICON_FILES = {
        "scrapper": "class_scrapper_icon.png",
        "former_mall_cop": "class_former_mall_cop_icon.png",
        "failed_magician": "class_failed_magician_icon.png",
        "lunch_lady_avenger": "class_lunch_lady_avenger_icon.png",
        "it_department_survivor": "class_it_department_survivor_icon.png",
        "mascot_handler": "class_mascot_handler_icon.png",
    }

    CLASS_PORTRAIT_FILES = {
        "scrapper": "class_scrapper_portrait.png",
        "former_mall_cop": "class_former_mall_cop_portrait.png",
        "failed_magician": "class_failed_magician_portrait.png",
        "lunch_lady_avenger": "class_lunch_lady_avenger_portrait.png",
        "it_department_survivor": "class_it_department_survivor_portrait.png",
        "mascot_handler": "class_mascot_handler_portrait.png",
    }

    UI_FILES = {
        "logo": "logo_dungeon_showdown.png",
        "title_bg": "bg_title_screen.png",
        "gameplay_bg": "bg_gameplay_frame.png",
        "top_bar": "ui_top_bar.png",
        "right_stats_panel": "ui_right_stats_panel.png",
        "bottom_log_panel": "ui_bottom_log_panel.png",
        "loot_popup": "ui_popup_loot.png",
        "boss_popup": "ui_popup_boss.png",
    }

    def __init__(self, asset_dir: Path) -> None:
        self.asset_dir = asset_dir
        self.ui_dir = self.asset_dir / "ui"
        self.icon_dir = self.asset_dir / "icons"
        self.class_icon_dir = self.icon_dir / "classes"
        self.class_portrait_dir = self.asset_dir / "portraits" / "classes"
        self.sprite_dir = self.asset_dir / "sprites"
        self.legacy_icon_dir = self.sprite_dir / "icons"

        self.icons: dict[str, pygame.Surface] = {}
        self.generic_icons: dict[str, pygame.Surface] = {}
        self.class_icons: dict[str, pygame.Surface] = {}
        self.class_portraits: dict[str, pygame.Surface] = {}
        self.ui_images: dict[str, pygame.Surface] = {}
        self._scaled_cache: dict[tuple[str, int, int], pygame.Surface] = {}
        self._build_fallback_icons()
        self._load_optional_ui()
        self._load_optional_icons()
        self._load_optional_generic_icons()
        self._load_optional_class_assets()

    def _safe_load_image(self, path: Path) -> pygame.Surface | None:
        if not path.exists():
            return None
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            return self._strip_light_checkerboard_background(image)
        except pygame.error:
            return None

    def _strip_light_checkerboard_background(self, image: pygame.Surface) -> pygame.Surface:
        """Remove fake white/gray checkerboard backgrounds from generated assets.

        Several generated PNGs visually contain a checkerboard instead of real alpha.
        This flood-fills only near-white/near-gray pixels connected to the image edges,
        so interior bright artwork is preserved.
        """
        width, height = image.get_size()
        if width <= 0 or height <= 0:
            return image

        def is_edge_checker_pixel(x: int, y: int) -> bool:
            r, g, b, a = image.get_at((x, y))
            if a == 0:
                return True
            return min(r, g, b) >= 215 and (max(r, g, b) - min(r, g, b)) <= 24

        visited = set()
        stack = []
        for x in range(width):
            stack.append((x, 0))
            stack.append((x, height - 1))
        for y in range(height):
            stack.append((0, y))
            stack.append((width - 1, y))

        while stack:
            x, y = stack.pop()
            if (x, y) in visited or x < 0 or y < 0 or x >= width or y >= height:
                continue
            visited.add((x, y))
            if not is_edge_checker_pixel(x, y):
                continue
            image.set_at((x, y), (0, 0, 0, 0))
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))
        return image

    def _build_fallback_icons(self) -> None:
        specs = {
            "Combat": COLORS["danger"],
            "Mini-Boss": COLORS["danger"],
            "Boss Room": COLORS["danger"],
            "Loot": COLORS["accent"],
            "Sponsor Crate": COLORS["accent"],
            "Trap": (230, 120, 50),
            "Rest": COLORS["good"],
            "Shop": (120, 180, 255),
            "NPC Event": (190, 130, 255),
            "Exit": COLORS["good"],
            "Entrance": COLORS["muted"],
            "Boss Gate": COLORS["muted"],
        }
        for name, color in specs.items():
            surf = pygame.Surface((22, 22), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (11, 11), 9)
            pygame.draw.circle(surf, COLORS["bg"], (11, 11), 9, 2)
            self.icons[name] = surf

        credit = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(credit, COLORS["gold"], (12, 12), 10)
        pygame.draw.circle(credit, COLORS["bg"], (12, 12), 10, 2)
        pygame.draw.circle(credit, COLORS["bg"], (12, 12), 5, 1)
        self.generic_icons["credits"] = credit

    def _load_optional_ui(self) -> None:
        for key, filename in self.UI_FILES.items():
            image = self._safe_load_image(self.ui_dir / filename)
            if image:
                self.ui_images[key] = image

    def _load_optional_icons(self) -> None:
        for room_type, filename in self.ROOM_ICON_FILES.items():
            image = self._safe_load_image(self.icon_dir / filename)
            if image:
                self.icons[room_type] = pygame.transform.smoothscale(image, (28, 28))

        if self.legacy_icon_dir.exists():
            for path in self.legacy_icon_dir.glob("*.png"):
                key = path.stem.replace("_", " ").title()
                image = self._safe_load_image(path)
                if image:
                    self.icons[key] = pygame.transform.smoothscale(image, (28, 28))

    def _load_optional_generic_icons(self) -> None:
        for key, filename in self.GENERIC_ICON_FILES.items():
            image = self._safe_load_image(self.icon_dir / filename)
            if image:
                self.generic_icons[key] = pygame.transform.smoothscale(image, (24, 24))

    def _load_optional_class_assets(self) -> None:
        for key, filename in self.CLASS_ICON_FILES.items():
            image = self._safe_load_image(self.class_icon_dir / filename)
            if image:
                self.class_icons[key] = pygame.transform.smoothscale(image, (52, 52))

        for key, filename in self.CLASS_PORTRAIT_FILES.items():
            image = self._safe_load_image(self.class_portrait_dir / filename)
            if image:
                self.class_portraits[key] = pygame.transform.smoothscale(image, (290, 290))

    def icon(self, room_type: str) -> pygame.Surface | None:
        return self.icons.get(room_type)

    def generic_icon(self, key: str) -> pygame.Surface | None:
        return self.generic_icons.get(key)

    def class_icon(self, key: str) -> pygame.Surface | None:
        return self.class_icons.get(key)

    def class_portrait(self, key: str) -> pygame.Surface | None:
        return self.class_portraits.get(key)

    def ui(self, key: str) -> pygame.Surface | None:
        return self.ui_images.get(key)

    def scaled_ui(self, key: str, size: tuple[int, int]) -> pygame.Surface | None:
        image = self.ui(key)
        if image is None:
            return None
        cache_key = (key, int(size[0]), int(size[1]))
        if cache_key not in self._scaled_cache:
            self._scaled_cache[cache_key] = pygame.transform.smoothscale(image, size)
        return self._scaled_cache[cache_key]

    def blit_scaled_ui(self, screen: pygame.Surface, key: str, rect: pygame.Rect) -> bool:
        image = self.scaled_ui(key, (rect.width, rect.height))
        if image is None:
            return False
        screen.blit(image, rect)
        return True
