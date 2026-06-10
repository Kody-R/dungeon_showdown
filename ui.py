from __future__ import annotations
import textwrap
import pygame

from config import COLORS, DEFAULT_FONT_SIZE, SMALL_FONT_SIZE, BIG_FONT_SIZE


class Button:
    def __init__(self, rect: pygame.Rect, text: str, action: str):
        self.rect = rect
        self.text = text
        self.action = action

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int]) -> None:
        color = COLORS["button_hover"] if self.rect.collidepoint(mouse_pos) else COLORS["button"]
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, COLORS["accent"], self.rect, width=2, border_radius=10)
        label = font.render(self.text, True, COLORS["text"])
        surface.blit(label, label.get_rect(center=self.rect.center))


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, x: int, y: int, color=None) -> None:
    image = font.render(text, True, color or COLORS["text"])
    surface.blit(image, (x, y))


def draw_wrapped_text(surface: pygame.Surface, font: pygame.font.Font, text: str, rect: pygame.Rect, color=None, line_gap: int = 6) -> int:
    color = color or COLORS["text"]
    words_per_line = max(20, rect.width // max(8, font.size("M")[0]))
    lines = []
    for paragraph in text.splitlines() or [text]:
        lines.extend(textwrap.wrap(paragraph, width=words_per_line) or [""])
    y = rect.y
    for line in lines:
        if y + font.get_height() > rect.bottom:
            break
        surface.blit(font.render(line, True, color), (rect.x, y))
        y += font.get_height() + line_gap
    return y


class TextLog:
    def __init__(self, max_lines: int = 120):
        self.lines: list[str] = []
        self.max_lines = max_lines

    def add(self, message: str) -> None:
        self.lines.append(message)
        self.lines = self.lines[-self.max_lines:]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, COLORS["panel"], rect, border_radius=8)
        pygame.draw.rect(surface, COLORS["panel_light"], rect, width=2, border_radius=8)
        line_height = font.get_height() + 4
        visible = max(1, rect.height // line_height - 1)
        y = rect.y + 10
        for line in self.lines[-visible:]:
            clipped = line if len(line) < 120 else line[:117] + "..."
            surface.blit(font.render(clipped, True, COLORS["text"]), (rect.x + 12, y))
            y += line_height


def load_fonts() -> tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]:
    pygame.font.init()
    return (
        pygame.font.SysFont("consolas", SMALL_FONT_SIZE),
        pygame.font.SysFont("consolas", DEFAULT_FONT_SIZE),
        pygame.font.SysFont("consolas", BIG_FONT_SIZE, bold=True),
    )
